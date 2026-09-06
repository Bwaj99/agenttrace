"""
SQLAlchemy models for the AgentTrace schema.

This is the single source of truth for the `runs`, `steps`, and
`step_replays` tables. The FastAPI backend imports these same classes
(rather than redefining them) so the SDK (writer) and the backend
(reader) can never drift apart — they share one SQLite file via a
Docker volume.

All timestamp columns are naive UTC datetimes (we always construct
them with `datetime.now(timezone.utc)` and store the value as-is;
SQLite has no native timezone-aware type, so keeping everything UTC
by convention avoids ambiguity).

JSON-ish fields (`metadata_json`, `input_json`, `output_json`,
`token_usage_json`, `modified_input_json`) are stored as TEXT
containing a JSON string, already truncated/serialized by
`storage.truncate()` before being written. Callers reading them back
just `json.loads()` the column.
"""

import uuid

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


def _new_id() -> str:
    """Generate a URL-safe unique id for a run/step/replay row."""
    return uuid.uuid4().hex


class Run(Base):
    """One full agent execution, started by `Tracer.start_run(...)`."""

    __tablename__ = "runs"

    id = Column(String, primary_key=True, default=_new_id)
    name = Column(String, nullable=False)
    started_at = Column(DateTime, nullable=False)
    ended_at = Column(DateTime, nullable=True)
    # "running" while in progress, then "completed" or "failed" on exit.
    status = Column(String, nullable=False, default="running")
    # Arbitrary caller-supplied metadata (e.g. {"agent_version": "..."}),
    # JSON-serialized. Defaults to an empty object, never NULL.
    metadata_json = Column(Text, nullable=False, default="{}")

    steps = relationship(
        "Step", back_populates="run", cascade="all, delete-orphan"
    )


class Step(Base):
    """
    A single traced unit of work (an LLM call, a tool call, or any
    custom function) within a run. `parent_step_id` is nullable and
    self-referential, which is what lets the dashboard render a tree
    instead of a flat list.
    """

    __tablename__ = "steps"

    id = Column(String, primary_key=True, default=_new_id)
    run_id = Column(String, ForeignKey("runs.id"), nullable=False, index=True)
    parent_step_id = Column(
        String, ForeignKey("steps.id"), nullable=True, index=True
    )
    name = Column(String, nullable=False)
    # "llm_call" | "tool_call" | "custom" — the backend/frontend key off
    # this to decide, e.g., whether the "Replay" button applies.
    step_type = Column(String, nullable=False, default="custom")
    started_at = Column(DateTime, nullable=False)
    ended_at = Column(DateTime, nullable=True)
    duration_ms = Column(Integer, nullable=True)
    input_json = Column(Text, nullable=True)
    output_json = Column(Text, nullable=True)
    # Full traceback text if the step raised; NULL on success.
    error = Column(Text, nullable=True)
    # {"prompt_tokens": int, "completion_tokens": int, "estimated_cost": float}
    # JSON-serialized; NULL for non-LLM steps or when usage couldn't be
    # determined.
    token_usage_json = Column(Text, nullable=True)

    run = relationship("Run", back_populates="steps")
    replays = relationship(
        "StepReplay", back_populates="original_step", cascade="all, delete-orphan"
    )


class StepReplay(Base):
    """
    A single replay attempt against an existing `Step` (v1 only
    supports replaying step_type == "llm_call"). Replays are additive
    — each attempt gets its own row here, never overwriting the
    original step, so history is preserved for diffing.
    """

    __tablename__ = "step_replays"

    id = Column(String, primary_key=True, default=_new_id)
    original_step_id = Column(
        String, ForeignKey("steps.id"), nullable=False, index=True
    )
    requested_at = Column(DateTime, nullable=False)
    modified_input_json = Column(Text, nullable=False)
    output_json = Column(Text, nullable=True)
    error = Column(Text, nullable=True)
    token_usage_json = Column(Text, nullable=True)

    original_step = relationship("Step", back_populates="replays")
