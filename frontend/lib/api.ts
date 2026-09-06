/**
 * Thin fetch wrapper around the AgentTrace FastAPI backend.
 *
 * All calls are client-side (see the "use client" pages) rather than
 * server-rendered, since this is a local dev tool where the backend
 * may not be reachable at Next.js build time inside Docker — fetching
 * from the browser after the page loads avoids coupling the frontend
 * build to the backend being up.
 */

import type { ReplayResult, RunDetail, RunSummary } from "./types";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${API_URL}${path}`, {
      ...init,
      headers: { "Content-Type": "application/json", ...(init?.headers || {}) },
      cache: "no-store",
    });
  } catch {
    throw new Error(`could not reach the backend at ${API_URL} — is it running?`);
  }

  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      if (body?.detail) detail = body.detail;
    } catch {
      // response wasn't JSON — fall back to statusText
    }
    throw new Error(detail);
  }

  return res.json();
}

export function listRuns(): Promise<RunSummary[]> {
  return apiFetch<RunSummary[]>("/runs");
}

export function getRun(runId: string): Promise<RunDetail> {
  return apiFetch<RunDetail>(`/runs/${runId}`);
}

export function replayStep(
  runId: string,
  stepId: string,
  modifiedInput: unknown
): Promise<ReplayResult> {
  return apiFetch<ReplayResult>(`/runs/${runId}/steps/${stepId}/replay`, {
    method: "POST",
    body: JSON.stringify({ modified_input: modifiedInput }),
  });
}
