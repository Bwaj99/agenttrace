"""
SQLite storage layer used by the SDK to write runs/steps immediately
(not batched), so a crashed agent still leaves a usable partial trace.

Planned responsibilities (Phase 2):

- Storage(db_path): opens/creates the SQLite file, runs
  `Base.metadata.create_all()` on first use (simple migration story
  for v1 — Alembic can be layered on later if needed).
- insert_run(...) / update_run(...): write-through, single-row
  commits (no batching) so partial progress is durable.
- insert_step(...) / update_step(...): same immediacy guarantee.
- truncate(value, max_bytes=10_000): shared helper that serializes an
  arbitrary Python value to JSON and truncates it to a size cap
  (~10KB per field, per the product spec) before it's stored, so large
  prompts/outputs don't blow up SQLite or the UI.
- A short-lived SQLAlchemy Session per write (or a scoped session) —
  favor simplicity and crash-safety over throughput for v1.
"""

# TODO(Phase 2): implement Storage class + truncate() helper.
