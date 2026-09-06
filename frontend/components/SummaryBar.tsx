import type { RunDetail, StepNode } from "@/lib/types";
import { formatCost, formatDuration } from "@/lib/format";

function flatten(steps: StepNode[]): StepNode[] {
  const out: StepNode[] = [];
  const walk = (list: StepNode[]) => {
    for (const step of list) {
      out.push(step);
      walk(step.children);
    }
  };
  walk(steps);
  return out;
}

/** Cost/latency summary bar shown at the top of a run detail page. */
export default function SummaryBar({ run }: { run: RunDetail }) {
  const slowest = flatten(run.steps).find((s) => s.id === run.slowest_step_id);
  const totalTokens = run.total_prompt_tokens + run.total_completion_tokens;

  const tiles = [
    { label: "Total tokens", value: totalTokens > 0 ? totalTokens.toLocaleString() : "—" },
    { label: "Total cost", value: formatCost(run.total_cost) },
    { label: "Duration", value: formatDuration(run.duration_ms) },
    {
      label: "Slowest step",
      value: slowest ? `${slowest.name} (${formatDuration(slowest.duration_ms)})` : "—",
    },
  ];

  return (
    <div className="grid grid-cols-2 gap-4 rounded-lg border border-gray-200 bg-white p-4 dark:border-gray-700 dark:bg-gray-900 sm:grid-cols-4">
      {tiles.map((tile) => (
        <div key={tile.label} className="min-w-0">
          <div className="text-xs text-gray-400">{tile.label}</div>
          <div className="truncate text-lg font-semibold">{tile.value}</div>
        </div>
      ))}
    </div>
  );
}
