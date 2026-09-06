/**
 * Run detail page (route: "/runs/[runId]").
 *
 * Planned (Phase 5):
 * - Fetch GET /runs/{run_id} from the backend.
 * - Cost/latency summary bar at the top: total tokens, total cost,
 *   total duration, slowest step highlighted.
 * - Vertical timeline/tree view of steps (nested steps indented),
 *   each showing name, duration, color-coded status.
 * - Clicking a step opens the StepDetailPanel (components/) showing
 *   full input/output JSON, token usage, and duration.
 * - "Replay" button on llm_call steps opens the ReplayPanel
 *   (components/) with an editable textarea, hits
 *   POST /runs/{run_id}/steps/{step_id}/replay, and renders a
 *   side-by-side diff of original vs. replayed output.
 */

// TODO(Phase 5): implement the run detail/timeline page.
export default function RunDetailPage({
  params,
}: {
  params: { runId: string };
}) {
  return null;
}
