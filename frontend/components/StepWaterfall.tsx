"use client";

import type { RunDetail, StepNode } from "@/lib/types";
import { flattenStepsWithDepth } from "@/lib/steps";
import { formatDuration } from "@/lib/format";

function statusOf(step: StepNode): "success" | "error" | "running" {
  if (step.error) return "error";
  if (!step.ended_at) return "running";
  return "success";
}

const DOT_COLOR: Record<string, string> = {
  success: "bg-emerald-500",
  error: "bg-red-500",
  running: "bg-amber-500",
};

const BAR_COLOR: Record<string, string> = {
  success: "bg-emerald-500",
  error: "bg-red-500",
  running: "bg-amber-500",
};

// Fractions of the total run duration to draw tick marks / gridlines at.
const TICKS = [0, 0.25, 0.5, 0.75, 1];

const LABEL_COL_WIDTH = 210; // px — kept in sync with the axis's left offset below

/**
 * Figure out the time window the waterfall should draw against: the run's
 * own start/end when both are known, falling back to the latest step end
 * time (or "now") for a run that crashed without ever setting ended_at —
 * so a partial trace still renders a sensible timeline instead of a
 * zero-width one.
 */
function computeBounds(run: RunDetail, allSteps: StepNode[]) {
  const startMs = new Date(run.started_at).getTime();
  let endMs = run.ended_at ? new Date(run.ended_at).getTime() : null;
  if (endMs === null) {
    const stepEnds = allSteps
      .map((s) => (s.ended_at ? new Date(s.ended_at).getTime() : null))
      .filter((t): t is number => t !== null);
    endMs = stepEnds.length > 0 ? Math.max(...stepEnds) : startMs;
  }
  return { startMs, totalMs: Math.max(endMs - startMs, 1) };
}

/**
 * A time-scaled waterfall of a run's steps: each row's bar is positioned by
 * the step's actual start offset and sized by its actual duration, on a
 * shared axis — so a run dominated by one slow step reads as dominated by
 * one slow bar, not as three equal-looking list rows with a number next to
 * each. Nested steps are indented in the label column but plotted on the
 * same absolute time axis as everything else.
 */
export default function StepWaterfall({
  run,
  selectedId,
  slowestId,
  onSelect,
}: {
  run: RunDetail;
  selectedId: string | null;
  slowestId: string | null;
  onSelect: (step: StepNode) => void;
}) {
  const rows = flattenStepsWithDepth(run.steps);

  if (rows.length === 0) {
    return <p className="p-3 text-sm text-gray-400">This run has no steps yet.</p>;
  }

  const { startMs, totalMs } = computeBounds(
    run,
    rows.map((r) => r.step)
  );

  return (
    <div className="overflow-x-auto">
      <div className="min-w-[560px]">
        {/* time axis */}
        <div
          className="relative mb-2 h-4 border-b border-gray-200 dark:border-gray-700"
          style={{ marginLeft: LABEL_COL_WIDTH }}
        >
          {TICKS.map((t) => (
            <span
              key={t}
              className={`absolute font-mono text-[10px] text-gray-400 ${
                t === 0 ? "" : t === 1 ? "-translate-x-full" : "-translate-x-1/2"
              }`}
              style={{ left: `${t * 100}%` }}
            >
              {formatDuration(Math.round(totalMs * t))}
            </span>
          ))}
        </div>

        <div className="space-y-0.5">
          {rows.map(({ step, depth }) => {
            const status = statusOf(step);
            const offsetMs = new Date(step.started_at).getTime() - startMs;
            const widthMs = step.duration_ms ?? 0;
            const leftPct = Math.min(Math.max((offsetMs / totalMs) * 100, 0), 100);
            // Floor the width so a fast step (a handful of ms next to a
            // multi-second one) still renders as a visible, clickable
            // sliver instead of disappearing entirely.
            const widthPct = Math.max((widthMs / totalMs) * 100, 0.6);
            const isSelected = step.id === selectedId;
            const isSlowest = step.id === slowestId;

            return (
              <button
                key={step.id}
                type="button"
                onClick={() => onSelect(step)}
                className={`flex h-8 w-full items-center gap-2 rounded-md pr-2 text-left transition-colors ${
                  isSelected
                    ? "bg-blue-50 dark:bg-blue-900/30"
                    : "hover:bg-gray-50 dark:hover:bg-gray-800"
                }`}
              >
                {/* label column */}
                <span
                  className="flex shrink-0 items-center gap-1.5 overflow-hidden"
                  style={{ width: LABEL_COL_WIDTH, paddingLeft: depth * 14 }}
                >
                  <span className={`h-1.5 w-1.5 shrink-0 rounded-full ${DOT_COLOR[status]}`} />
                  <span className="shrink-0 font-mono text-[10px] uppercase tracking-wide text-gray-400">
                    {step.step_type}
                  </span>
                  <span className="truncate text-sm">{step.name}</span>
                </span>

                {/* time track */}
                <span className="relative h-4 flex-1 rounded bg-gray-100 dark:bg-gray-800/70">
                  {TICKS.slice(1, -1).map((t) => (
                    <span
                      key={t}
                      className="absolute top-0 h-full w-px bg-gray-200 dark:bg-gray-700"
                      style={{ left: `${t * 100}%` }}
                    />
                  ))}
                  <span
                    className={`absolute top-0 h-full rounded-sm ${BAR_COLOR[status]} ${
                      depth > 0 ? "opacity-70" : ""
                    } ${isSelected ? "ring-2 ring-blue-400" : ""}`}
                    style={{ left: `${leftPct}%`, width: `${widthPct}%` }}
                  />
                </span>

                {/* trailing duration + slowest flag */}
                {isSlowest && (
                  <span className="shrink-0 text-[10px] font-medium text-amber-600 dark:text-amber-400">
                    slowest
                  </span>
                )}
                <span className="w-14 shrink-0 text-right font-mono text-xs text-gray-400">
                  {formatDuration(step.duration_ms)}
                </span>
              </button>
            );
          })}
        </div>
      </div>
    </div>
  );
}
