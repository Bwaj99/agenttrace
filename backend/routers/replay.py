"""
Single-step replay endpoint.

Planned (Phase 3):

    POST /runs/{run_id}/steps/{step_id}/replay
        Body: { "modified_input": <json> }

        - Loads the original step; v1 only supports replaying steps
          with step_type == "llm_call".
        - Extracts the provider/model recorded on the original step's
          input/metadata.
        - Calls that same provider/model with the modified input.
        - Inserts a new `step_replays` row (original_step_id,
          modified_input, new output, token usage) — never overwrites
          the original step's history.
        - Returns { original_output, replayed_output, token_usage }
          so the frontend can diff them side by side.
"""

# TODO(Phase 3): implement router = APIRouter() and the replay
# endpoint above, including the OpenAI/Anthropic call-out and error
# handling for non-llm_call step types.
