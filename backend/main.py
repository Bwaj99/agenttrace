"""
AgentTrace backend — FastAPI app.

Serves trace data (runs + nested steps) from the same SQLite file the
agenttrace-sdk writes to (a shared Docker volume in production; a
local path during development — see database.py).

Run locally with:

    uvicorn main:app --reload --port 8000
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routers import replay, runs

app = FastAPI(
    title="AgentTrace API",
    description="Local-first observability API for LLM agent traces.",
    version="0.1.0",
)

# The dashboard runs on localhost:3000 in both local dev and Docker
# Compose; this is a local-only tool so a permissive-but-scoped
# localhost allowlist is fine (no wildcard "*").
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(runs.router)
app.include_router(replay.router)


@app.get("/health")
def health():
    """Simple liveness check — also handy for confirming the DB file
    was found/created without errors on startup."""
    return {"status": "ok"}
