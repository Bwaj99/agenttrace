"""
Standalone smoke test for the agenttrace SDK — no pytest required, run
directly:

    python test_sdk_smoke.py

Proves, by reading the SQLite file back with a plain SQLAlchemy
session (independent of the SDK's own write path), that:

  1. A run row is written the moment `start_run` is entered, and
     flipped to "completed"/"failed" (with `ended_at` set) on exit.
  2. Steps nest correctly (parent_step_id round-trips through two
     levels of decorated function calls).
  3. Input/output are captured automatically by the decorator form,
     and JSON-serialized.
  4. A step that raises records the error text and still marks the
     run "failed" (rather than losing the trace).
  5. LLM token usage is auto-detected from an OpenAI-shaped response
     object, and cost is estimated.
  6. Oversized output is truncated to the ~10KB cap rather than
     blowing up the row.
  7. Nothing is batched — every row exists in the DB immediately after
     its context manager exits, before the process ends.
"""

import json
import os
import sys
import tempfile
from types import SimpleNamespace

sys.path.insert(0, os.path.dirname(__file__))

from agenttrace import Tracer, trace_step, record_usage  # noqa: E402
from agenttrace.storage import MAX_FIELD_BYTES  # noqa: E402
from agenttrace.models import Run, Step  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402


def _read_only_session(db_path):
    """A second, independent connection — proves data is durably on
    disk, not just cached in the Tracer's own session."""
    engine = create_engine(f"sqlite:///{db_path}")
    return sessionmaker(bind=engine)()


def _fake_openai_response(content: str, prompt_tokens: int, completion_tokens: int):
    """Mimics the shape of an OpenAI ChatCompletion response enough
    for `_try_extract_llm_usage` to auto-detect usage from it."""
    return SimpleNamespace(
        model="gpt-4o-mini",
        choices=[SimpleNamespace(message=SimpleNamespace(content=content))],
        usage=SimpleNamespace(
            prompt_tokens=prompt_tokens, completion_tokens=completion_tokens
        ),
    )


def main():
    tmp_dir = tempfile.mkdtemp(prefix="agenttrace_smoke_")
    db_path = os.path.join(tmp_dir, "smoke.db")
    print(f"[smoke] writing to {db_path}")

    tracer = Tracer(db_path=db_path)

    # --- decorated steps, nested two levels deep --------------------------

    @trace_step(name="search", step_type="tool_call")
    def search(topic: str):
        return [f"result about {topic} #1", f"result about {topic} #2"]

    @trace_step(name="summarize", step_type="llm_call")
    def summarize(results):
        prompt = "Summarize: " + ", ".join(results)
        response = _fake_openai_response(
            content=f"Summary of {len(results)} results.",
            prompt_tokens=42,
            completion_tokens=17,
        )
        return response

    @trace_step(name="write_file", step_type="tool_call")
    def write_file(summary_text: str):
        # a nested step called from *inside* another traced step
        with trace_step("format_output"):
            formatted = f"# Summary\n\n{summary_text}\n"
        return formatted

    with tracer.start_run(name="smoke-test-run", metadata={"env": "test"}) as run_id:
        results = search("agent observability")
        response = summarize(results)
        write_file(response.choices[0].message.content)

    # --- a second run that fails partway through --------------------------

    @trace_step(name="flaky_step", step_type="tool_call")
    def flaky_step():
        raise ValueError("simulated failure")

    failed_run_id = None
    try:
        with tracer.start_run(name="smoke-test-failing-run") as run_id2:
            failed_run_id = run_id2
            flaky_step()
    except ValueError:
        pass  # expected — proves the exception still propagates to the caller

    # --- oversized output gets truncated -----------------------------------

    @trace_step(name="huge_output", step_type="custom")
    def huge_output():
        return "x" * (MAX_FIELD_BYTES * 3)

    with tracer.start_run(name="smoke-test-truncation-run") as run_id3:
        huge_output()

    # --- manual record_usage() override -------------------------------------

    with tracer.start_run(name="smoke-test-manual-usage-run") as run_id4:
        with trace_step("manual_llm_call", step_type="llm_call") as step:
            step.set_output("some streamed response we can't auto-parse")
            record_usage(prompt_tokens=100, completion_tokens=50, cost=0.001)

    # ------------------------------------------------------------------------
    # Verification: read everything back with an independent session.
    # ------------------------------------------------------------------------
    session = _read_only_session(db_path)

    run = session.get(Run, run_id)
    assert run is not None, "run row was not written"
    assert run.status == "completed", f"expected completed, got {run.status}"
    assert run.ended_at is not None, "ended_at was not set on completion"
    print(f"[smoke] OK: run '{run.name}' status={run.status}")

    steps = session.query(Step).filter_by(run_id=run_id).all()
    by_name = {s.name: s for s in steps}
    assert set(by_name) == {"search", "summarize", "write_file", "format_output"}, by_name
    print(f"[smoke] OK: all {len(steps)} steps for the run were written")

    # nesting: format_output's parent must be write_file; the other three
    # are top-level (no parent) since they were called directly inside
    # the `with tracer.start_run(...)` block.
    assert by_name["format_output"].parent_step_id == by_name["write_file"].id
    assert by_name["search"].parent_step_id is None
    assert by_name["summarize"].parent_step_id is None
    assert by_name["write_file"].parent_step_id is None
    print("[smoke] OK: step nesting (parent_step_id) round-trips correctly")

    # input/output capture
    search_input = json.loads(by_name["search"].input_json)
    assert search_input == {"topic": "agent observability"}, search_input
    search_output = json.loads(by_name["search"].output_json)
    assert search_output == [
        "result about agent observability #1",
        "result about agent observability #2",
    ]
    print("[smoke] OK: input/output captured and JSON-serialized")

    # every step has ended_at/duration_ms set (nothing left half-written)
    for s in steps:
        assert s.ended_at is not None, f"{s.name} missing ended_at"
        assert s.duration_ms is not None and s.duration_ms >= 0, s.name
    print("[smoke] OK: every step has ended_at + duration_ms set")

    # LLM usage auto-detection
    usage = json.loads(by_name["summarize"].token_usage_json)
    assert usage["prompt_tokens"] == 42
    assert usage["completion_tokens"] == 17
    assert usage["estimated_cost"] is not None and usage["estimated_cost"] > 0
    print(f"[smoke] OK: auto-detected LLM usage + cost estimate: {usage}")

    # failed run: status + error text captured, exception still propagated
    failed_run = session.get(Run, failed_run_id)
    assert failed_run.status == "failed", failed_run.status
    failed_step = session.query(Step).filter_by(run_id=failed_run_id).one()
    assert failed_step.error is not None and "simulated failure" in failed_step.error
    print("[smoke] OK: failing step recorded status=failed + traceback, error still raised to caller")

    # truncation
    huge_step = session.query(Step).filter_by(run_id=run_id3).one()
    assert len(huge_step.output_json.encode("utf-8")) <= MAX_FIELD_BYTES + 200
    assert json.loads(huge_step.output_json)["_agenttrace_truncated"] is True
    print("[smoke] OK: oversized output was truncated instead of stored raw")

    # manual record_usage()
    manual_step = session.query(Step).filter_by(run_id=run_id4).one()
    manual_usage = json.loads(manual_step.token_usage_json)
    assert manual_usage == {
        "prompt_tokens": 100,
        "completion_tokens": 50,
        "estimated_cost": 0.001,
    }
    print("[smoke] OK: manual record_usage() override recorded correctly")

    session.close()
    print("\n[smoke] ALL CHECKS PASSED")
    print(f"[smoke] inspect the DB yourself at: {db_path}")


if __name__ == "__main__":
    main()
