"""
Run listing + detail endpoints.

    GET /runs               -> list of RunSummary (cheap, no step tree)
    GET /runs/{run_id}      -> RunDetail (summary + nested step tree)
"""

import json
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models import Run, Step
from schemas import RunDetail, RunSummary, StepNode, TokenUsage

router = APIRouter(tags=["runs"])


def _parse_json(text: Optional[str]):
    """Decode a JSON text column, tolerating NULL and (defensively)
    malformed content rather than 500ing the whole request."""
    if not text:
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {"_agenttrace_parse_error": True, "raw": text}


def _duration_ms(started_at, ended_at) -> Optional[int]:
    if started_at is None or ended_at is None:
        return None
    return int((ended_at - started_at).total_seconds() * 1000)


def _summarize(run: Run, steps: List[Step]) -> dict:
    """Shared aggregation for both endpoints: step count + rolled-up
    token/cost totals across every step in the run (nested or not)."""
    total_prompt_tokens = 0
    total_completion_tokens = 0
    total_cost = 0.0

    for step in steps:
        usage = _parse_json(step.token_usage_json)
        if not usage:
            continue
        total_prompt_tokens += usage.get("prompt_tokens") or 0
        total_completion_tokens += usage.get("completion_tokens") or 0
        total_cost += usage.get("estimated_cost") or 0.0

    return {
        "id": run.id,
        "name": run.name,
        "started_at": run.started_at,
        "ended_at": run.ended_at,
        "status": run.status,
        "metadata": _parse_json(run.metadata_json) or {},
        "step_count": len(steps),
        "total_prompt_tokens": total_prompt_tokens,
        "total_completion_tokens": total_completion_tokens,
        "total_cost": round(total_cost, 6),
        "duration_ms": _duration_ms(run.started_at, run.ended_at),
    }


@router.get("/runs", response_model=List[RunSummary])
def list_runs(db: Session = Depends(get_db)):
    """List every run, newest first, with rolled-up summary stats.
    Deliberately doesn't build the step tree — this powers the runs
    table, which only needs the totals."""
    runs = db.query(Run).order_by(Run.started_at.desc()).all()
    summaries = []
    for run in runs:
        # One query per run for its steps; runs/step counts stay small
        # for a local debugging tool, so this favors simplicity over a
        # single big join.
        steps = db.query(Step).filter(Step.run_id == run.id).all()
        summaries.append(_summarize(run, steps))
    return summaries


@router.get("/runs/{run_id}", response_model=RunDetail)
def get_run(run_id: str, db: Session = Depends(get_db)):
    """Full run detail: summary stats plus the complete step tree,
    nested by parent_step_id, each subtree ordered by start time."""
    run = db.get(Run, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail=f"run '{run_id}' not found")

    steps = (
        db.query(Step)
        .filter(Step.run_id == run_id)
        .order_by(Step.started_at.asc())
        .all()
    )

    nodes: dict[str, StepNode] = {}
    for step in steps:
        usage_dict = _parse_json(step.token_usage_json)
        nodes[step.id] = StepNode(
            id=step.id,
            parent_step_id=step.parent_step_id,
            name=step.name,
            step_type=step.step_type,
            started_at=step.started_at,
            ended_at=step.ended_at,
            duration_ms=step.duration_ms,
            input=_parse_json(step.input_json),
            output=_parse_json(step.output_json),
            error=step.error,
            token_usage=TokenUsage(**usage_dict) if usage_dict else None,
            children=[],
        )

    roots: List[StepNode] = []
    for step in steps:
        node = nodes[step.id]
        parent = nodes.get(step.parent_step_id) if step.parent_step_id else None
        if parent is not None:
            parent.children.append(node)
        else:
            roots.append(node)

    slowest = max(
        (s for s in steps if s.duration_ms is not None),
        key=lambda s: s.duration_ms,
        default=None,
    )

    summary = _summarize(run, steps)
    return RunDetail(**summary, steps=roots, slowest_step_id=slowest.id if slowest else None)
