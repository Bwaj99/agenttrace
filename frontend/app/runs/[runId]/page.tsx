"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { getRun } from "@/lib/api";
import type { RunDetail, StepNode } from "@/lib/types";
import StatusBadge from "@/components/StatusBadge";
import SummaryBar from "@/components/SummaryBar";
import StepWaterfall from "@/components/StepWaterfall";
import StepDetailPanel from "@/components/StepDetailPanel";

/** Run detail page ("/runs/[runId]"): cost/latency summary, a
 * time-scaled step waterfall, and a detail panel for the selected step. */
export default function RunDetailPage({ params }: { params: { runId: string } }) {
  const { runId } = params;
  const [run, setRun] = useState<RunDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [selected, setSelected] = useState<StepNode | null>(null);

  useEffect(() => {
    let cancelled = false;
    getRun(runId)
      .then((data) => {
        if (cancelled) return;
        setRun(data);
        // Auto-select the first top-level step so the panel isn't empty.
        if (data.steps.length > 0) setSelected(data.steps[0]);
      })
      .catch((err) => {
        if (!cancelled) setError(err instanceof Error ? err.message : String(err));
      });
    return () => {
      cancelled = true;
    };
  }, [runId]);

  if (error) {
    return (
      <main className="mx-auto max-w-5xl px-6 py-10">
        <BackLink />
        <div className="mt-4 rounded-md bg-red-50 p-3 text-sm text-red-700 dark:bg-red-900/30 dark:text-red-300">
          Couldn&apos;t load this run: {error}
        </div>
      </main>
    );
  }

  if (!run) {
    return (
      <main className="mx-auto max-w-5xl px-6 py-10">
        <p className="text-sm text-gray-400">Loading…</p>
      </main>
    );
  }

  return (
    <main className="mx-auto max-w-6xl px-6 py-10">
      <BackLink />

      <div className="mb-6 mt-3 flex items-center gap-3">
        <h1 className="text-xl font-bold">{run.name}</h1>
        <StatusBadge status={run.status} />
      </div>

      <div className="mb-6">
        <SummaryBar run={run} />
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-[minmax(0,1fr)_420px]">
        <div className="rounded-lg border border-gray-200 p-3 dark:border-gray-700">
          <StepWaterfall
            run={run}
            selectedId={selected?.id ?? null}
            slowestId={run.slowest_step_id}
            onSelect={setSelected}
          />
        </div>
        <div className="rounded-lg border border-gray-200 p-4 dark:border-gray-700">
          {selected ? (
            <StepDetailPanel runId={run.id} step={selected} />
          ) : (
            <p className="text-sm text-gray-400">Select a step to see details.</p>
          )}
        </div>
      </div>
    </main>
  );
}

function BackLink() {
  return (
    <Link href="/" className="text-sm text-blue-600 hover:underline dark:text-blue-400">
      &larr; back to runs
    </Link>
  );
}
