"""
AgentTrace backend — FastAPI app.

Serves trace data (runs + nested steps) from the same SQLite file the
agenttrace-sdk writes to (a shared Docker volume in production; a
local path during development).

Planned structure (Phase 3):

    app = FastAPI(title="AgentTrace API")
    app.add_middleware(CORSMiddleware, allow_origins=[...], ...)
    app.include_router(runs.router)
    app.include_router(replay.router)

Endpoints (see routers/):
    GET  /runs                                    -> routers/runs.py
    GET  /runs/{run_id}                            -> routers/runs.py
    POST /runs/{run_id}/steps/{step_id}/replay     -> routers/replay.py
"""

# TODO(Phase 3): construct the FastAPI app, configure CORS for
# localhost:3000, and include the routers below.
