"""
Single-step replay endpoint.

    POST /runs/{run_id}/steps/{step_id}/replay
        Body: { "modified_input": <json> }

v1 scope (per product spec): only `step_type == "llm_call"` steps can
be replayed. We take the modified prompt, call the same provider/model
recorded on the original step, and return the new output alongside the
original for diffing. Each attempt is stored as its own `StepReplay`
row linked to the original step — the original step's history is never
overwritten.
"""

import json
import os
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from agenttrace.storage import truncate
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models import Step, StepReplay
from schemas import ReplayRequest, ReplayResult, TokenUsage

router = APIRouter(tags=["replay"])

# Fallback models used when the original step's recorded output didn't
# carry a `model` field (e.g. it was written by `record_usage()` alone
# rather than SDK auto-detection). Whichever provider's API key is
# configured wins; matches the demo agent's single-provider approach.
_DEFAULT_OPENAI_MODEL = "gpt-4o-mini"
_DEFAULT_ANTHROPIC_MODEL = "claude-3-5-sonnet-20241022"


def _extract_prompt(modified_input: Any) -> str:
    """
    The SDK stores an llm_call step's input as whatever shape the
    caller gave `trace_step(..., input=...)` — most commonly
    {"prompt": "..."}. Accept a few common shapes so the replay
    textarea (which round-trips the original input) works whether the
    caller used "prompt", "text", or a bare string.
    """
    if isinstance(modified_input, str):
        return modified_input
    if isinstance(modified_input, dict):
        for key in ("prompt", "text", "input", "query"):
            value = modified_input.get(key)
            if isinstance(value, str):
                return value
    # Last resort: something structured we don't recognize — stringify
    # it so the call doesn't crash, even if the result is odd.
    return json.dumps(modified_input)


def _model_for_step(step: Step) -> Optional[str]:
    """Best-effort: pull the model the original call used out of the
    step's stored output (SDK auto-detection stores {"model", "text"}
    for recognized LLM responses)."""
    if not step.output_json:
        return None
    try:
        output = json.loads(step.output_json)
    except json.JSONDecodeError:
        return None
    if isinstance(output, dict):
        return output.get("model")
    return None


def _call_openai(model: str, prompt: str) -> dict:
    from openai import OpenAI

    client = OpenAI()
    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
    )
    return {
        "text": response.choices[0].message.content,
        "prompt_tokens": response.usage.prompt_tokens,
        "completion_tokens": response.usage.completion_tokens,
    }


def _call_anthropic(model: str, prompt: str) -> dict:
    import anthropic

    client = anthropic.Anthropic()
    response = client.messages.create(
        model=model,
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}],
    )
    text = "".join(getattr(block, "text", "") for block in response.content)
    return {
        "text": text,
        "prompt_tokens": response.usage.input_tokens,
        "completion_tokens": response.usage.output_tokens,
    }


@router.post("/runs/{run_id}/steps/{step_id}/replay", response_model=ReplayResult)
def replay_step(
    run_id: str,
    step_id: str,
    body: ReplayRequest,
    db: Session = Depends(get_db),
):
    step = db.get(Step, step_id)
    if step is None or step.run_id != run_id:
        raise HTTPException(
            status_code=404, detail=f"step '{step_id}' not found on run '{run_id}'"
        )
    if step.step_type != "llm_call":
        raise HTTPException(
            status_code=400,
            detail=(
                f"step_type '{step.step_type}' cannot be replayed — "
                "v1 only supports replaying llm_call steps"
            ),
        )

    prompt = _extract_prompt(body.modified_input)
    model = _model_for_step(step)

    replay_id = uuid.uuid4().hex
    requested_at = datetime.now(timezone.utc)

    error_text: Optional[str] = None
    output_text: Optional[str] = None
    token_usage: Optional[dict] = None

    try:
        if os.environ.get("OPENAI_API_KEY"):
            result = _call_openai(model or _DEFAULT_OPENAI_MODEL, prompt)
        elif os.environ.get("ANTHROPIC_API_KEY"):
            result = _call_anthropic(model or _DEFAULT_ANTHROPIC_MODEL, prompt)
        else:
            raise RuntimeError(
                "no OPENAI_API_KEY or ANTHROPIC_API_KEY configured on the backend"
            )
        output_text = result["text"]
        token_usage = {
            "prompt_tokens": result["prompt_tokens"],
            "completion_tokens": result["completion_tokens"],
            "estimated_cost": None,  # illustrative pricing lives in the SDK; kept simple here
        }
    except Exception as exc:  # noqa: BLE001 - surface any provider/config error to the caller
        error_text = str(exc)

    # Store the attempt regardless of success/failure — replays are
    # additive history, never overwriting the original step.
    replay_row = StepReplay(
        id=replay_id,
        original_step_id=step_id,
        requested_at=requested_at,
        modified_input_json=truncate(body.modified_input),
        output_json=truncate(output_text) if output_text is not None else None,
        error=error_text,
        token_usage_json=truncate(token_usage) if token_usage is not None else None,
    )
    db.add(replay_row)
    db.commit()

    if error_text is not None:
        raise HTTPException(status_code=502, detail=f"replay call failed: {error_text}")

    original_output = json.loads(step.output_json) if step.output_json else None

    return ReplayResult(
        replay_id=replay_id,
        step_id=step_id,
        requested_at=requested_at,
        modified_input=body.modified_input,
        original_output=original_output,
        replayed_output=output_text,
        token_usage=TokenUsage(**token_usage) if token_usage else None,
        error=None,
    )
