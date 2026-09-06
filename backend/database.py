"""
Database engine/session setup for the backend.

Points at the exact same SQLite file the agenttrace-sdk writes to
(shared via a Docker volume in production; a local relative path
during development). Reuses the SDK's own SQLAlchemy models
(backend/models.py just re-exports them) so there is exactly one
schema definition in the whole project.
"""

import os

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from models import Base

# Default matches .env.example / docker-compose.yml. Override with
# AGENTTRACE_DB_PATH for local (non-Docker) development against a
# trace file produced elsewhere (e.g. by running demo-agent locally).
DB_PATH = os.environ.get("AGENTTRACE_DB_PATH", "../agenttrace.db")

engine = create_engine(
    f"sqlite:///{DB_PATH}", connect_args={"check_same_thread": False}
)

# Safe to call even if the SDK hasn't written anything yet — this is
# what lets `docker compose up` show an empty (but functioning) runs
# list before the demo agent has ever been run.
Base.metadata.create_all(engine)

SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)


def get_db():
    """FastAPI dependency: yields a session, closes it after the request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
