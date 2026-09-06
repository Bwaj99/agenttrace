"""
SQLite storage layer used by the SDK to write runs/steps immediately
(not batched), so a crashed agent still leaves a usable partial trace.

Every public method opens a short-lived session, does one write, and
commits immediately — favoring crash-safety and simplicity over
throughput, which is the right tradeoff for a local debugging tool
that's tracing a handful of steps per run, not a high-volume pipeline.
"""

import json
from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from .models import Base, Run, Step, StepReplay

# Cap on the size of any single JSON-serialized field (input, output,
# etc.) before it's written to SQLite. Keeps the DB fast and the
# dashboard responsive even when a step's payload is huge (e.g. a
# large retrieved document).
MAX_FIELD_BYTES = 10_000


def truncate(value) -> str:
    """
    Serialize an arbitrary Python value to a JSON string, capped at
    MAX_FIELD_BYTES. Used for every input/output/metadata field before
    it's stored.

    - Falls back to `str(value)` for anything JSON can't serialize
      natively (e.g. custom SDK response objects from an LLM client).
    - If the serialized form exceeds the cap, it's replaced with a
      small wrapper object carrying a truncated preview, so the field
      always remains valid, parseable JSON.
    """
    try:
        serialized = json.dumps(value, default=str)
    except (TypeError, ValueError):
        serialized = json.dumps(str(value))

    encoded = serialized.encode("utf-8")
    if len(encoded) <= MAX_FIELD_BYTES:
        return serialized

    # Decode a safely-truncated byte slice back to text (ignoring any
    # partial multi-byte character cut off at the boundary), and wrap
    # it so consumers can still tell it was truncated.
    preview = encoded[:MAX_FIELD_BYTES].decode("utf-8", errors="ignore")
    return json.dumps(
        {
            "_agenttrace_truncated": True,
            "original_bytes": len(encoded),
            "preview": preview,
        }
    )


class Storage:
    """
    Thin wrapper around a SQLAlchemy engine/session pointed at a local
    SQLite file. Creates the schema on first use (`create_all` — good
    enough for v1; Alembic can be layered on later if the schema needs
    real migrations).
    """

    def __init__(self, db_path: str):
        self.db_path = db_path
        # check_same_thread=False: the demo agent / backend may touch
        # this from more than one thread (e.g. FastAPI's threadpool),
        # and each call already uses its own short-lived session.
        self.engine = create_engine(
            f"sqlite:///{db_path}", connect_args={"check_same_thread": False}
        )
        Base.metadata.create_all(self.engine)
        self._Session = sessionmaker(bind=self.engine, expire_on_commit=False)

    @contextmanager
    def _session(self):
        session = self._Session()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    # -- runs -----------------------------------------------------------

    def insert_run(self, id, name, started_at, status, metadata=None):
        with self._session() as session:
            session.add(
                Run(
                    id=id,
                    name=name,
                    started_at=started_at,
                    status=status,
                    metadata_json=truncate(metadata or {}),
                )
            )

    def update_run(self, id, **fields):
        with self._session() as session:
            run = session.get(Run, id)
            if run is None:
                return
            for key, value in fields.items():
                setattr(run, key, value)

    # -- steps ------------------------------------------------------------

    def insert_step(
        self,
        id,
        run_id,
        parent_step_id,
        name,
        step_type,
        started_at,
        input_json=None,
    ):
        with self._session() as session:
            session.add(
                Step(
                    id=id,
                    run_id=run_id,
                    parent_step_id=parent_step_id,
                    name=name,
                    step_type=step_type,
                    started_at=started_at,
                    input_json=input_json,
                )
            )

    def update_step(self, id, **fields):
        with self._session() as session:
            step = session.get(Step, id)
            if step is None:
                return
            for key, value in fields.items():
                setattr(step, key, value)

    # -- replays ----------------------------------------------------------

    def insert_step_replay(
        self,
        id,
        original_step_id,
        requested_at,
        modified_input_json,
        output_json=None,
        error=None,
        token_usage_json=None,
    ):
        with self._session() as session:
            session.add(
                StepReplay(
                    id=id,
                    original_step_id=original_step_id,
                    requested_at=requested_at,
                    modified_input_json=modified_input_json,
                    output_json=output_json,
                    error=error,
                    token_usage_json=token_usage_json,
                )
            )
