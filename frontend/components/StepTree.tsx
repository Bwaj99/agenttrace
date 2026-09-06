"use client";

import type { StepNode } from "@/lib/types";
import { formatDuration } from "@/lib/format";

function statusOf(step: StepNode): "success" | "error" | "running" {
  if (step.error) return "error";
  if (!step.ended_at) return "running";
  return "success";
}

const DOT_COLOR: Record<string, string> = {
  success: "bg-green-500",
  error: "bg-red-500",
  running: "bg-amber-500",
};

function StepRow({
  step,
  depth,
  selectedId,
  slowestId,
  onSelect,
}: {
  step: StepNode;
  depth: number;
  selectedId: string | null;
  slowestId: string | null;
  onSelect: (step: StepNode) => void;
}) {
  const status = statusOf(step);
  const isSelected = step.id === selectedId;
  const isSlowest = step.id === slowestId;

  return (
    <div>
      <button
        type="button"
        onClick={() => onSelect(step)}
        style={{ paddingLeft: `${depth * 1.25 + 0.75}rem` }}
        className={`flex w-full items-center gap-2 rounded-md py-1.5 pr-3 text-left text-sm transition-colors ${
          isSelected
            ? "bg-blue-50 dark:bg-blue-900/30"
            : "hover:bg-gray-50 dark:hover:bg-gray-800"
        }`}
      >
        <span className={`h-2 w-2 shrink-0 rounded-full ${DOT_COLOR[status]}`} aria-hidden />
        <span className="shrink-0 font-mono text-[10px] uppercase tracking-wide text-gray-400">
          {step.step_type}
        </span>
        <span className="truncate">{step.name}</span>
        {isSlowest && (
          <span className="shrink-0 text-[10px] font-medium text-amber-600 dark:text-amber-400">
            slowest
          </span>
        )}
        <span className="ml-auto shrink-0 text-xs text-gray-400">
          {formatDuration(step.duration_ms)}
        </span>
      </button>
      {step.children.map((child) => (
        <StepRow
          key={child.id}
          step={child}
          depth={depth + 1}
          selectedId={selectedId}
          slowestId={slowestId}
          onSelect={onSelect}
        />
      ))}
    </div>
  );
}

/** Vertical, indented tree of a run's steps — the timeline view. */
export default function StepTree({
  steps,
  selectedId,
  slowestId,
  onSelect,
}: {
  steps: StepNode[];
  selectedId: string | null;
  slowestId: string | null;
  onSelect: (step: StepNode) => void;
}) {
  if (steps.length === 0) {
    return <p className="p-3 text-sm text-gray-400">This run has no steps yet.</p>;
  }

  return (
    <div className="space-y-0.5">
      {steps.map((step) => (
        <StepRow
          key={step.id}
          step={step}
          depth={0}
          selectedId={selectedId}
          slowestId={slowestId}
          onSelect={onSelect}
        />
      ))}
    </div>
  );
}
