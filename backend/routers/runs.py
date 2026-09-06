"""
Run listing + detail endpoints.

Planned (Phase 3):

    GET /runs
        List all runs with summary stats: duration, step count,
        total cost, status. One row per run, no nested steps (keep
        this endpoint cheap for a table view).

    GET /runs/{run_id}
        Full run detail: the run row plus its complete step tree
        (steps nested by parent_step_id, ordered by started_at).
"""

# TODO(Phase 3): implement router = APIRouter(), the two endpoints
# above, and the run-summary aggregation (cost/duration/step count).
