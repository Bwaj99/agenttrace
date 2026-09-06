"""
SQLAlchemy models for the AgentTrace schema.

This is the single source of truth for the `runs` and `steps` tables.
The FastAPI backend (backend/models.py) will import or mirror these
same models so both the SDK (writer) and the backend (reader) agree on
schema — they share one SQLite file via a Docker volume.

Planned schema (Phase 2):

    class Run(Base):
        __tablename__ = "runs"
        id: str (uuid, primary key)
        name: str
        started_at: datetime
        ended_at: datetime | None
        status: str            # "running" | "completed" | "failed"
        metadata_json: str     # JSON-serialized dict

    class Step(Base):
        __tablename__ = "steps"
        id: str (uuid, primary key)
        run_id: str (FK -> runs.id)
        parent_step_id: str | None (FK -> steps.id)   # enables nesting
        name: str
        step_type: str          # "llm_call" | "tool_call" | "custom"
        started_at: datetime
        ended_at: datetime | None
        duration_ms: int | None
        input_json: str         # truncated, serialized
        output_json: str        # truncated, serialized
        error: str | None
        token_usage_json: str | None  # {prompt_tokens, completion_tokens, estimated_cost}

    class StepReplay(Base):
        __tablename__ = "step_replays"
        id: str (uuid, primary key)
        original_step_id: str (FK -> steps.id)
        requested_at: datetime
        modified_input_json: str
        output_json: str
        error: str | None
        token_usage_json: str | None

Replays are stored as their own rows linked to the original step
(never overwriting history), per the product spec.
"""

# TODO(Phase 2): define Base, Run, Step, StepReplay with SQLAlchemy.
