# AgentTrace

A local-first observability and replay tool for LLM agent pipelines.

Instrument any multi-step AI agent with a lightweight Python SDK,
capture every execution step (prompts, tool calls, latencies, token
costs, errors) into a local SQLite database, visualize each run as an
interactive timeline, and replay individual LLM-call steps with
modified inputs to debug failures — all self-hosted via Docker Compose
with zero cloud dependency.

![AgentTrace run detail screenshot placeholder](docs/screenshot-run-detail.png)
*(screenshot: a run's timeline, step detail panel, and replay diff — see [Screenshot](#screenshot) below)*

## Quickstart

```bash
cp .env.example .env
# optionally set OPENAI_API_KEY or ANTHROPIC_API_KEY in .env —
# the demo agent and the replay endpoint work without one, using a
# clearly-labeled mock response, so you can try the whole pipeline
# with zero setup.

docker compose up -d          # backend on :8000, dashboard on :3000
docker compose run demo-agent "your topic here"
```

Open [http://localhost:3000](http://localhost:3000) — the run you just
generated is there, with its full step timeline.

Run the demo agent again (with a different topic, or the same one) any
time to add more traces. Nothing here talks to the network except the
demo agent's own LLM call (or the replay endpoint's, if you use it) —
everything else stays on your machine.

### Running without Docker

Each piece can also run directly, which is faster to iterate on during
development:

```bash
# 1. SDK (editable install, shared by the backend and the demo agent)
pip install -e ./sdk

# 2. Backend
cd backend
pip install -r requirements.txt
AGENTTRACE_DB_PATH=../agenttrace.db uvicorn main:app --reload --port 8000

# 3. Frontend (separate terminal)
cd frontend
npm install
NEXT_PUBLIC_API_URL=http://localhost:8000 npm run dev

# 4. Demo agent (separate terminal, run any time to add a trace)
cd demo-agent
pip install -r requirements.txt
AGENTTRACE_DB_PATH=../agenttrace.db python agent.py "your topic here"
```

All three pieces just need to agree on `AGENTTRACE_DB_PATH` — point
them at the same SQLite file and everything shares state.

## Architecture

```
Your agent (or the bundled demo agent)
        │  instrumented with agenttrace-sdk:
        │  @trace_step / Tracer.start_run()
        ▼
   agenttrace.db (SQLite)  <──── shared Docker volume ────┐
        ▲                                                  │
        │ writes immediately,                              │ reads
        │ not batched                                       │
        │                                          FastAPI backend
        │                                          (routers/runs.py,
        │                                           routers/replay.py)
        │                                                  │
        │                                    REST: GET /runs,
        │                                    GET /runs/{id},
        │                                    POST .../replay
        │                                                  ▼
        │                                       Next.js dashboard
        │                                       (localhost:3000)
        └──────────────────── replay calls the same provider/model
                               recorded on the original step, and
                               writes a new StepReplay row — never
                               touching the original step's history.
```

**Why SQLite, written immediately.** Every `runs`/`steps` row is
inserted the moment it starts and updated the moment it ends — nothing
is batched in memory. If your agent crashes mid-run, the partial trace
up to the crash is still in the database and viewable in the
dashboard, with the failed step's full traceback attached. The backend
reads from the exact same file the SDK writes to (shared via a Docker
volume), so there's no sync step and no second copy of the schema —
`backend/models.py` imports the SDK's SQLAlchemy models directly.

**SDK** ([sdk/](sdk/)) — `agenttrace-sdk`, a small Python package:
- `Tracer.start_run(name=...)`: a context manager marking one full
  agent execution; flips the run's status to `completed` or `failed`
  on exit (re-raising the original exception either way).
- `@trace_step(name=..., step_type=...)`: usable as a decorator or a
  context manager. Records timing, input/output (JSON-serialized,
  truncated at ~10KB/field), and errors. Nesting is automatic —
  `contextvars` track which step is currently "open," so a step called
  from inside another step is recorded as its child, giving the
  dashboard a tree instead of a flat list.
- Token usage: when a decorated LLM-call function returns a raw
  OpenAI or Anthropic SDK response object, usage and an illustrative
  cost estimate are extracted automatically. `record_usage(...)` is
  available as a manual override for shapes the SDK doesn't recognize
  (e.g. a streamed response).

**Backend** ([backend/](backend/)) — FastAPI:
- `GET /runs` — every run with rolled-up stats (duration, step count,
  total cost/tokens, status), no step tree (kept cheap for the table).
- `GET /runs/{run_id}` — one run's full nested step tree, plus which
  step was slowest.
- `POST /runs/{run_id}/steps/{step_id}/replay` — v1 only supports
  replaying `llm_call` steps: takes a modified prompt, calls the same
  provider/model recorded on the original step, and stores the attempt
  as its own `StepReplay` row (even on failure) — the original step is
  never overwritten, so replay history accumulates rather than clobbers.

**Frontend** ([frontend/](frontend/)) — Next.js (App Router) + React +
TypeScript + Tailwind, no heavier UI framework:
- `/` — runs table.
- `/runs/[runId]` — summary bar (total tokens/cost/duration, slowest
  step), the step timeline (indented tree, color-coded by status), and
  a detail panel for whichever step is selected, with collapsible
  input/output JSON and (for `llm_call` steps) the replay UI: an
  editable textarea pre-filled with the original prompt, and a
  side-by-side original-vs-replayed diff once you run it.

**Demo agent** ([demo-agent/](demo-agent/)) — a 3-step agent (search →
summarize → write file), fully instrumented, used to generate real
trace data. The search step is a hardcoded stub (no search API key
needed). The summarize step calls whichever of `OPENAI_API_KEY` /
`ANTHROPIC_API_KEY` is set — or falls back to a clearly-labeled mock
response if neither is, so the whole SDK → SQLite → API → dashboard
pipeline is verifiable with zero external setup.

## Project layout

```
agenttrace/
  sdk/                  # agenttrace-sdk Python package (pip install -e .)
    agenttrace/
      tracer.py          # Tracer, trace_step, record_usage
      models.py          # SQLAlchemy schema (Run, Step, StepReplay)
      storage.py          # SQLite write layer + truncation helper
    test_sdk_smoke.py     # standalone verification script, no pytest needed
  backend/               # FastAPI app
    routers/{runs,replay}.py
    database.py, models.py, schemas.py
  frontend/              # Next.js app
    app/                  # pages (runs list, run detail)
    components/           # StepTree, StepDetailPanel, ReplayPanel, SummaryBar, ...
    lib/                   # API client + shared types/formatting
  demo-agent/
    agent.py
  docker-compose.yml
  .env.example
```

## Scope notes (v1)

- **Replay is single-step LLM-call only.** There's no attempt at
  deterministic full-agent replay — tool calls and non-LLM steps
  aren't replayable in v1, by design.
- **Fields are truncated at ~10KB.** A step's input/output is capped
  before it's written to SQLite, so a huge retrieved document or
  response won't blow up the database or the dashboard. Truncated
  fields are marked as such rather than silently cut.
- **Cost estimates are illustrative**, from a small hardcoded
  per-model price table in the SDK — not billing-accurate, and
  unrecognized models simply show no cost rather than `$0`.
- **No auth / multi-user support.** This is a local, single-user
  debugging tool by design; everything (backend, SQLite file, replay
  endpoint) is meant to run on your machine, not be exposed publicly.

## Screenshot

_A screenshot of the run detail page (timeline + step panel + replay
diff) goes at `docs/screenshot-run-detail.png` — generate one by
running through the Quickstart above and capturing `/runs/<id>`._

## License

MIT
