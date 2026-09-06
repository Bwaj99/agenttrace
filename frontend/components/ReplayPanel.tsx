"use client";

import { useState } from "react";
import { replayStep } from "@/lib/api";
import type { ReplayResult, StepNode } from "@/lib/types";
import { extractOutputText, extractPromptText } from "@/lib/format";

/**
 * Editable textarea (pre-filled with the original step's input) that
 * calls the replay endpoint and renders a side-by-side diff of the
 * original vs. replayed output. Only rendered for llm_call steps —
 * see StepDetailPanel.
 */
export default function ReplayPanel({ runId, step }: { runId: string; step: StepNode }) {
  const [expanded, setExpanded] = useState(false);
  const [draft, setDraft] = useState(() => extractPromptText(step.input));
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<ReplayResult | null>(null);

  const runReplay = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await replayStep(runId, step.id, { prompt: draft });
      setResult(res);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  };

  if (!expanded) {
    return (
      <button
        type="button"
        onClick={() => setExpanded(true)}
        className="mt-2 rounded-md bg-blue-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-blue-700"
      >
        Replay this step
      </button>
    );
  }

  return (
    <div className="mt-2 space-y-3 rounded-md border border-gray-200 p-3 dark:border-gray-700">
      <div>
        <label className="mb-1 block text-xs font-medium text-gray-500" htmlFor="replay-input">
          Modified prompt
        </label>
        <textarea
          id="replay-input"
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          rows={6}
          className="w-full rounded-md border border-gray-300 bg-white p-2 font-mono text-sm text-gray-900 dark:border-gray-600 dark:bg-gray-900 dark:text-gray-100"
        />
      </div>

      <div className="flex items-center gap-3">
        <button
          type="button"
          onClick={runReplay}
          disabled={loading || draft.trim().length === 0}
          className="rounded-md bg-blue-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {loading ? "Running…" : "Run replay"}
        </button>
        <button
          type="button"
          onClick={() => setExpanded(false)}
          className="text-xs text-gray-500 hover:underline"
        >
          Cancel
        </button>
      </div>

      {error && (
        <div className="rounded-md bg-red-50 p-2 text-xs text-red-700 dark:bg-red-900/30 dark:text-red-300">
          {error}
        </div>
      )}

      {result && (
        <div>
          <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
            <div>
              <div className="mb-1 text-xs font-medium text-gray-500">Original output</div>
              <pre className="max-h-64 overflow-auto whitespace-pre-wrap rounded-md bg-gray-50 p-2 text-xs dark:bg-gray-800">
                {extractOutputText(result.original_output) || "—"}
              </pre>
            </div>
            <div>
              <div className="mb-1 text-xs font-medium text-gray-500">Replayed output</div>
              <pre className="max-h-64 overflow-auto whitespace-pre-wrap rounded-md bg-blue-50 p-2 text-xs dark:bg-blue-900/20">
                {extractOutputText(result.replayed_output) || "—"}
              </pre>
            </div>
          </div>
          {result.token_usage && (
            <div className="mt-2 text-xs text-gray-500">
              tokens: {result.token_usage.prompt_tokens ?? "—"} prompt /{" "}
              {result.token_usage.completion_tokens ?? "—"} completion
            </div>
          )}
        </div>
      )}
    </div>
  );
}
