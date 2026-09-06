import type { StepNode } from "@/lib/types";
import { formatCost, formatDuration } from "@/lib/format";
import JsonBlock from "@/components/JsonBlock";
import ReplayPanel from "@/components/ReplayPanel";

/** Side panel shown when a step is selected in the timeline: full
 * input/output, token usage, duration, and (for llm_call steps) the
 * replay UI. */
export default function StepDetailPanel({ runId, step }: { runId: string; step: StepNode }) {
  return (
    <div className="space-y-4">
      <div>
        <div className="text-xs uppercase tracking-wide text-gray-400">{step.step_type}</div>
        <h3 className="break-words text-lg font-semibold">{step.name}</h3>
        <div className="mt-1 flex flex-wrap gap-x-3 text-xs text-gray-500">
          <span>duration: {formatDuration(step.duration_ms)}</span>
          <span>started: {new Date(step.started_at).toLocaleTimeString()}</span>
        </div>
      </div>

      {step.error && (
        <div className="max-h-48 overflow-auto whitespace-pre-wrap rounded-md bg-red-50 p-3 text-xs text-red-700 dark:bg-red-900/30 dark:text-red-300">
          {step.error}
        </div>
      )}

      {step.token_usage && (
        <div className="flex flex-wrap gap-x-4 gap-y-1 text-xs text-gray-500">
          <span>prompt tokens: {step.token_usage.prompt_tokens ?? "—"}</span>
          <span>completion tokens: {step.token_usage.completion_tokens ?? "—"}</span>
          <span>cost: {formatCost(step.token_usage.estimated_cost)}</span>
        </div>
      )}

      <JsonBlock label="Input" value={step.input} />
      <JsonBlock label="Output" value={step.output} />

      {step.step_type === "llm_call" && <ReplayPanel runId={runId} step={step} />}
    </div>
  );
}
