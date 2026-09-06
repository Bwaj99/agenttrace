"""
Core instrumentation primitives: Tracer, trace_step, record_usage.

This module is the heart of the SDK. It will be implemented in Phase 2
of the build. Sketch of the design for reference while building:

- Tracer(db_path):
    * Owns a Storage instance (see storage.py) pointed at a local
      SQLite file.
    * start_run(name, metadata=None) -> context manager that inserts a
      `runs` row immediately (status="running"), yields a run context,
      and on exit updates status to "completed" or "failed" + ended_at.
    * Tracks the "current step stack" (thread-local / contextvar) so
      nested trace_step calls can find their parent_step_id.

- trace_step(name, step_type="custom"):
    * Usable as both a decorator and a context manager.
    * On enter: inserts a `steps` row immediately (started_at set,
      ended_at null) so partial/crashed runs still leave usable data.
    * Captures input arguments (serialized + truncated, see
      storage.py's truncation helper).
    * On exit: records output or error, ended_at, duration_ms.
    * If the wrapped call's return value looks like an OpenAI or
      Anthropic response object, auto-extract token usage
      (prompt/completion tokens) and estimate cost from a small
      per-model price table.

- record_usage(prompt_tokens, completion_tokens, cost=None):
    * Manual override — attaches usage data to whichever step is
      currently active on the context-var stack, for cases where
      auto-detection can't parse the LLM client's response shape.

Uses Python's `contextvars` to track nesting safely across async code
and threads.
"""

# TODO(Phase 2): implement Tracer, trace_step, record_usage.
