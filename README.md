# AgentTrace

A local-first observability and replay tool for LLM agent pipelines.

Instrument any multi-step AI agent with a lightweight Python SDK,
capture every execution step (prompts, tool calls, latencies, token
costs, errors) into a local SQLite database, visualize each run as an
interactive timeline, and replay individual steps with modified inputs
to debug failures — all self-hosted via Docker Compose with zero cloud
dependency.

> **Status:** scaffolding in progress. This README will be filled in
> with real setup instructions, a screenshot, and an architecture
> writeup once the vertical slice (SDK → SQLite → API → dashboard) is
> working end to end (Phase 7 of the build).

## Planned architecture

```
Demo agent (or your own agent)
        │  instrumented with agenttrace-sdk
        ▼
   agenttrace.db (SQLite)  <── shared volume ──┐
        ▲                                       │
        │ reads                                 │ writes
   FastAPI backend  ────────────────────────────┘
        │  REST API (runs, run detail, replay)
        ▼
   Next.js dashboard (localhost:3000)
```

- **SDK** (`sdk/`): `Tracer`, `@trace_step`, `record_usage` — instrument
  any Python agent function to record steps immediately to SQLite, so
  a crash still leaves a usable partial trace.
- **Backend** (`backend/`): FastAPI, reads the same SQLite file the SDK
  writes to. Serves run/step data and handles single-step LLM replay.
- **Frontend** (`frontend/`): Next.js + React + TypeScript + Tailwind.
  Runs list → run detail timeline → step detail panel → replay diff UI.
- **Demo agent** (`demo-agent/`): a 3-step sample agent (search →
  summarize → write file) instrumented with the SDK, used to generate
  real trace data to view in the dashboard.

## Repo structure

```
agenttrace/
  sdk/                  # agenttrace-sdk Python package
  backend/              # FastAPI app
  frontend/             # Next.js app
  demo-agent/           # sample instrumented agent
  docker-compose.yml
  .env.example
```

## Setup

_TODO(Phase 7): fill in once Docker Compose is wired up end to end._

```bash
cp .env.example .env
# fill in OPENAI_API_KEY or ANTHROPIC_API_KEY in .env

docker compose up          # backend on :8000, dashboard on :3000
docker compose run demo-agent   # generates a real trace to view
```

## Screenshot

_TODO(Phase 7): add a screenshot of the run timeline / replay UI here._

## License

MIT
