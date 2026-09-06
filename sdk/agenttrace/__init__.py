"""
agenttrace-sdk
===============

Lightweight instrumentation library for tracing multi-step LLM agent
pipelines into a local SQLite database.

Public API (implemented in Phase 2):

    from agenttrace import Tracer, trace_step, record_usage

    tracer = Tracer(db_path="agenttrace.db")
    with tracer.start_run(name="my-agent-run"):
        with trace_step("search"):
            ...
        with trace_step("summarize"):
            ...

- Tracer: owns a run's lifecycle (start/end) and the storage connection.
- trace_step: decorator / context manager that records a single step
  (name, timing, input, output, errors, token usage) and supports
  nesting so child steps roll up under their parent.
- record_usage: manual override for attaching token usage / cost to
  the currently-active step when it can't be auto-detected from the
  wrapped LLM client's response shape.
"""

# TODO(Phase 2): implement Tracer, trace_step, record_usage in
# tracer.py and re-export them here.
#
# from .tracer import Tracer, trace_step, record_usage
#
# __all__ = ["Tracer", "trace_step", "record_usage"]

__version__ = "0.1.0"
