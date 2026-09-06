"""
Core instrumentation primitives: Tracer, trace_step, record_usage.

Usage
-----

    from agenttrace import Tracer, trace_step, record_usage

    tracer = Tracer(db_path="agenttrace.db")

    with tracer.start_run(name="my-agent-run"):

        @trace_step(name="search", step_type="tool_call")
        def search(topic: str) -> list[str]:
            ...

        @trace_step(name="summarize", step_type="llm_call")
        def summarize(results: list[str]) -> str:
            response = openai_client.chat.completions.create(...)
            return response.choices[0].message.content

        results = search("agent observability")
        summary = summarize(results)

`trace_step` also works as a context manager, for call sites that
aren't a clean single function (or where you want to record a custom
input/output shape):

    with trace_step("summarize", step_type="llm_call", input={"prompt": prompt}) as step:
        response = call_llm(prompt)
        step.set_output(response.text)
        step.record_usage(prompt_tokens=..., completion_tokens=...)

Nesting is automatic: a `trace_step` used while another one is already
open (in the same run, either as nested decorated calls or nested
`with` blocks) is recorded as a child of the outer step, using
`contextvars` so it works correctly across nested function calls
without threading a "parent" argument through every call site.

Every step is written to SQLite the moment it starts (so partial
traces survive a crash) and updated the moment it ends.
"""

import functools
import inspect
import time
import traceback
from contextvars import ContextVar
from datetime import datetime, timezone
from typing import Optional, Tuple
import uuid

from .storage import Storage, truncate

# ---------------------------------------------------------------------------
# Context tracking (contextvars so this is safe across nested calls and,
# unlike thread-locals, propagates correctly into async tasks too).
# ---------------------------------------------------------------------------

_current_tracer: ContextVar[Optional["Tracer"]] = ContextVar(
    "agenttrace_current_tracer", default=None
)
_current_run_id: ContextVar[Optional[str]] = ContextVar(
    "agenttrace_current_run_id", default=None
)
_current_step_stack: ContextVar[Tuple[str, ...]] = ContextVar(
    "agenttrace_current_step_stack", default=()
)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


# ---------------------------------------------------------------------------
# LLM usage auto-detection
# ---------------------------------------------------------------------------

# Rough per-million-token USD prices, keyed by a model-name prefix match.
# These are illustrative estimates for a local debugging tool, not
# billing-accurate figures — real prices change over time and vary by
# provider tier. Unrecognized models fall back to `None` (no cost
# estimate), which the dashboard should render as "—" rather than $0.
_PRICING_PER_MILLION_TOKENS = {
    # (prefix, (prompt_price, completion_price))
    "gpt-4o-mini": (0.15, 0.60),
    "gpt-4o": (2.50, 10.00),
    "gpt-4-turbo": (10.00, 30.00),
    "gpt-3.5-turbo": (0.50, 1.50),
    "claude-3-5-sonnet": (3.00, 15.00),
    "claude-3-5-haiku": (0.80, 4.00),
    "claude-3-opus": (15.00, 75.00),
    "claude-3-haiku": (0.25, 1.25),
}


def _estimate_cost(model: Optional[str], prompt_tokens: int, completion_tokens: int) -> Optional[float]:
    if not model:
        return None
    for prefix, (prompt_price, completion_price) in _PRICING_PER_MILLION_TOKENS.items():
        if model.startswith(prefix):
            return round(
                (prompt_tokens / 1_000_000) * prompt_price
                + (completion_tokens / 1_000_000) * completion_price,
                6,
            )
    return None


def _extract_text(result) -> Optional[str]:
    """Best-effort extraction of the human-readable text from an OpenAI
    or Anthropic SDK response object (used only for the *stored* trace
    output — the caller's actual return value is never touched)."""
    # OpenAI chat/completions: result.choices[0].message.content
    choices = getattr(result, "choices", None)
    if choices:
        message = getattr(choices[0], "message", None)
        content = getattr(message, "content", None) if message else None
        if content is not None:
            return content

    # Anthropic messages: result.content is a list of blocks with .text
    content_blocks = getattr(result, "content", None)
    if isinstance(content_blocks, list):
        texts = [getattr(block, "text", None) for block in content_blocks]
        texts = [t for t in texts if t]
        if texts:
            return "".join(texts)

    return None


def _try_extract_llm_response(result) -> Optional[dict]:
    """
    Best-effort detection of an OpenAI or Anthropic SDK response object,
    so `@trace_step` on an LLM call "just works" without the caller
    doing anything extra: token usage is extracted for the cost/latency
    summary, and a clean {"text", "model"} dict replaces the raw SDK
    object as the *stored* step output (the raw object is still what's
    returned to the caller — only what gets written to SQLite changes),
    since the raw object usually isn't cleanly JSON-serializable and a
    plain str() dump isn't useful in the dashboard or for replay.

    Returns None if `result` doesn't look like a recognized LLM
    response shape — the caller can still attach usage manually via
    `record_usage(...)`, and the raw return value is stored as-is.
    """
    usage = getattr(result, "usage", None)
    if usage is None:
        return None

    model = getattr(result, "model", None)
    text = _extract_text(result)

    # OpenAI chat/completions response: usage.prompt_tokens / completion_tokens
    if hasattr(usage, "prompt_tokens") and hasattr(usage, "completion_tokens"):
        prompt_tokens = usage.prompt_tokens or 0
        completion_tokens = usage.completion_tokens or 0
        return {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "estimated_cost": _estimate_cost(model, prompt_tokens, completion_tokens),
            "model": model,
            "text": text,
        }

    # Anthropic messages response: usage.input_tokens / output_tokens
    if hasattr(usage, "input_tokens") and hasattr(usage, "output_tokens"):
        prompt_tokens = usage.input_tokens or 0
        completion_tokens = usage.output_tokens or 0
        return {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "estimated_cost": _estimate_cost(model, prompt_tokens, completion_tokens),
            "model": model,
            "text": text,
        }

    return None


def _capture_call_input(func, args, kwargs) -> dict:
    """
    Best-effort capture of a decorated function's call arguments as a
    single JSON-able dict, binding them to their parameter names when
    possible (falling back to positional if binding fails, e.g. for
    builtins/partials with no introspectable signature).
    """
    try:
        signature = inspect.signature(func)
        bound = signature.bind_partial(*args, **kwargs)
        bound.apply_defaults()
        return dict(bound.arguments)
    except (TypeError, ValueError):
        return {"args": list(args), "kwargs": kwargs}


# ---------------------------------------------------------------------------
# Tracer
# ---------------------------------------------------------------------------


class Tracer:
    """
    Owns a run's lifecycle and the SQLite storage connection. Create
    one per process (or per agent instance) and reuse it across runs.
    """

    def __init__(self, db_path: str = "agenttrace.db"):
        self.storage = Storage(db_path)

    def start_run(self, name: str, metadata: Optional[dict] = None):
        """
        Context manager: inserts a `runs` row immediately
        (status="running"), makes this tracer/run the "current" one for
        any `trace_step` used inside the `with` block, and marks the
        run "completed" or "failed" (re-raising) on exit.

            with tracer.start_run(name="demo-agent:some topic") as run_id:
                ...
        """
        return _RunContext(self, name, metadata)

    def record_usage(self, prompt_tokens=None, completion_tokens=None, cost=None):
        """Instance-method convenience alias for the module-level `record_usage`."""
        record_usage(prompt_tokens=prompt_tokens, completion_tokens=completion_tokens, cost=cost)


class _RunContext:
    """Implements the context-manager protocol for `Tracer.start_run(...)`."""

    def __init__(self, tracer: Tracer, name: str, metadata: Optional[dict]):
        self._tracer = tracer
        self._name = name
        self._metadata = metadata
        self._run_id = None
        self._tracer_token = None
        self._run_id_token = None
        self._stack_token = None

    def __enter__(self) -> str:
        self._run_id = uuid.uuid4().hex
        self._tracer.storage.insert_run(
            id=self._run_id,
            name=self._name,
            started_at=_utcnow(),
            status="running",
            metadata=self._metadata,
        )
        self._tracer_token = _current_tracer.set(self._tracer)
        self._run_id_token = _current_run_id.set(self._run_id)
        # Fresh step stack for this run, in case a run is somehow
        # started while another is already active on this context.
        self._stack_token = _current_step_stack.set(())
        return self._run_id

    def __exit__(self, exc_type, exc, tb):
        status = "failed" if exc_type is not None else "completed"
        self._tracer.storage.update_run(self._run_id, ended_at=_utcnow(), status=status)
        _current_tracer.reset(self._tracer_token)
        _current_run_id.reset(self._run_id_token)
        _current_step_stack.reset(self._stack_token)
        return False  # never suppress the caller's exception


# ---------------------------------------------------------------------------
# trace_step
# ---------------------------------------------------------------------------


class StepHandle:
    """
    Yielded by the `trace_step` context manager. Lets the caller
    attach an output value and/or token usage before the block exits.
    Not needed in decorator form — output and usage are captured
    automatically from the wrapped function's return value.
    """

    def __init__(self, step_id: str):
        self.step_id = step_id
        self._output = None
        self._has_output = False
        self._token_usage: Optional[dict] = None

    def set_output(self, value) -> None:
        self._output = value
        self._has_output = True

    def record_usage(self, prompt_tokens=None, completion_tokens=None, cost=None) -> None:
        self._token_usage = {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "estimated_cost": cost,
        }


class trace_step:
    """
    Decorator and context manager that records one step: name, timing,
    input, output, errors, and (for LLM calls) token usage.

    As a decorator:

        @trace_step(name="summarize", step_type="llm_call")
        def summarize(prompt: str) -> str:
            ...

    As a context manager:

        with trace_step("summarize", step_type="llm_call", input={"prompt": prompt}) as step:
            result = call_llm(prompt)
            step.set_output(result)

    Must be used while a `Tracer.start_run(...)` context is active
    (nested calls automatically become child steps of whichever step
    is currently open, or top-level steps of the run if none is).
    """

    def __init__(self, name: str, step_type: str = "custom", input=None):
        self.name = name
        self.step_type = step_type
        self._explicit_input = input
        # Per-invocation state, set on __enter__.
        self._step_id = None
        self._tracer = None
        self._start_perf = None
        self._stack_token = None
        self._handle: Optional[StepHandle] = None

    def __enter__(self) -> StepHandle:
        tracer = _current_tracer.get()
        if tracer is None:
            raise RuntimeError(
                "trace_step() was used outside of an active "
                "Tracer.start_run(...) context. Wrap your agent's "
                "entry point in `with tracer.start_run(name=...):` first."
            )
        run_id = _current_run_id.get()
        stack = _current_step_stack.get()
        parent_step_id = stack[-1] if stack else None

        self._tracer = tracer
        self._step_id = uuid.uuid4().hex
        self._start_perf = time.perf_counter()

        input_json = truncate(self._explicit_input) if self._explicit_input is not None else None
        tracer.storage.insert_step(
            id=self._step_id,
            run_id=run_id,
            parent_step_id=parent_step_id,
            name=self.name,
            step_type=self.step_type,
            started_at=_utcnow(),
            input_json=input_json,
        )

        self._stack_token = _current_step_stack.set(stack + (self._step_id,))
        self._handle = StepHandle(self._step_id)
        return self._handle

    def __exit__(self, exc_type, exc, tb) -> bool:
        duration_ms = int((time.perf_counter() - self._start_perf) * 1000)

        error_text = None
        if exc is not None:
            error_text = "".join(traceback.format_exception(exc_type, exc, tb))

        output_json = None
        if self._handle is not None and self._handle._has_output:
            output_json = truncate(self._handle._output)

        fields = dict(
            ended_at=_utcnow(),
            duration_ms=duration_ms,
            output_json=output_json,
            error=error_text,
        )
        # Only touch token_usage_json here if the handle itself recorded
        # usage (decorator auto-detection, or `step.record_usage(...)`).
        # A plain module-level `record_usage(...)` call already wrote
        # straight to storage mid-step — leave that value alone instead
        # of clobbering it back to NULL on exit.
        if self._handle is not None and self._handle._token_usage is not None:
            fields["token_usage_json"] = truncate(self._handle._token_usage)

        self._tracer.storage.update_step(self._step_id, **fields)
        _current_step_stack.reset(self._stack_token)
        return False  # never suppress the wrapped code's exception

    def __call__(self, func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            call_input = _capture_call_input(func, args, kwargs)
            # A fresh `trace_step` per invocation — self (the decorator
            # instance) is shared across every call to the wrapped
            # function, so per-call state must not live on it.
            with trace_step(self.name, self.step_type, input=call_input) as step:
                result = func(*args, **kwargs)
                llm_info = _try_extract_llm_response(result)
                if llm_info is not None:
                    step.record_usage(
                        prompt_tokens=llm_info["prompt_tokens"],
                        completion_tokens=llm_info["completion_tokens"],
                        cost=llm_info["estimated_cost"],
                    )
                    # Store the clean {model, text} shape rather than the
                    # raw SDK object — `result` itself (returned below)
                    # is untouched, so callers see the real response.
                    step.set_output({"model": llm_info["model"], "text": llm_info["text"]})
                else:
                    step.set_output(result)
                return result

        return wrapper


def record_usage(prompt_tokens=None, completion_tokens=None, cost=None) -> None:
    """
    Manually attach token usage to the currently-active step (the
    innermost open `trace_step`), for cases where auto-detection can't
    parse the wrapped call's return value (e.g. a streaming response,
    or a provider/shape `_try_extract_llm_usage` doesn't recognize).

    No-op (rather than raising) if called outside any active step, so
    it's safe to sprinkle into shared helper code that isn't always
    called from within a trace.
    """
    tracer = _current_tracer.get()
    stack = _current_step_stack.get()
    if tracer is None or not stack:
        return

    step_id = stack[-1]
    usage = {
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "estimated_cost": cost,
    }
    tracer.storage.update_step(step_id, token_usage_json=truncate(usage))
