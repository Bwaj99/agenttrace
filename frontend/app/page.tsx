"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { listRuns } from "@/lib/api";
import type { RunSummary } from "@/lib/types";
import StatusBadge from "@/components/StatusBadge";
import { formatCost, formatDuration } from "@/lib/format";

/** Runs list page ("/"): a table of every run with summary stats,
 * linking through to each run's timeline/detail page. */
export default function RunsListPage() {
  const [runs, setRuns] = useState<RunSummary[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    listRuns()
      .then((data) => {
        if (!cancelled) setRuns(data);
      })
      .catch((err) => {
        if (!cancelled) setError(err instanceof Error ? err.message : String(err));
      });
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <main className="mx-auto max-w-5xl px-6 py-10">
      <h1 className="mb-1 text-2xl font-bold">AgentTrace</h1>
      <p className="mb-6 text-sm text-gray-500">Runs captured from your instrumented agents.</p>

      {error && (
        <div className="mb-4 rounded-md bg-red-50 p-3 text-sm text-red-700 dark:bg-red-900/30 dark:text-red-300">
          Couldn&apos;t reach the backend: {error}
        </div>
      )}

      {!error && runs === null && <p className="text-sm text-gray-400">Loading…</p>}

      {runs !== null && runs.length === 0 && (
        <div className="rounded-md border border-dashed border-gray-300 p-8 text-center text-sm text-gray-500 dark:border-gray-700">
          No runs yet. Generate one with the demo agent:
          <pre className="mx-auto mt-2 inline-block rounded bg-gray-100 px-2 py-1 text-xs dark:bg-gray-800">
            docker compose run demo-agent
          </pre>
        </div>
      )}

      {runs !== null && runs.length > 0 && (
        <div className="overflow-x-auto rounded-lg border border-gray-200 dark:border-gray-700">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 text-left text-xs uppercase tracking-wide text-gray-500 dark:bg-gray-800">
              <tr>
                <th className="px-4 py-2 font-medium">Name</th>
                <th className="px-4 py-2 font-medium">Started</th>
                <th className="px-4 py-2 font-medium">Duration</th>
                <th className="px-4 py-2 font-medium">Steps</th>
                <th className="px-4 py-2 font-medium">Cost</th>
                <th className="px-4 py-2 font-medium">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100 dark:divide-gray-800">
              {runs.map((run) => (
                <tr key={run.id} className="hover:bg-gray-50 dark:hover:bg-gray-800/60">
                  <td className="px-4 py-2">
                    <Link
                      href={`/runs/${run.id}`}
                      className="font-medium text-blue-600 hover:underline dark:text-blue-400"
                    >
                      {run.name}
                    </Link>
                  </td>
                  <td className="px-4 py-2 text-gray-500">
                    {new Date(run.started_at).toLocaleString()}
                  </td>
                  <td className="px-4 py-2 text-gray-500">{formatDuration(run.duration_ms)}</td>
                  <td className="px-4 py-2 text-gray-500">{run.step_count}</td>
                  <td className="px-4 py-2 text-gray-500">{formatCost(run.total_cost)}</td>
                  <td className="px-4 py-2">
                    <StatusBadge status={run.status} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </main>
  );
}
