/**
 * TypeScript mirrors of the backend's Pydantic response models
 * (backend/schemas.py). Keep these in sync manually — this is a
 * small enough API surface that generating a client wasn't worth the
 * extra build-time dependency for v1.
 */

export type StepType = "llm_call" | "tool_call" | "custom" | string;
export type RunStatus = "running" | "completed" | "failed" | string;

export interface TokenUsage {
  prompt_tokens: number | null;
  completion_tokens: number | null;
  estimated_cost: number | null;
}

export interface StepNode {
  id: string;
  parent_step_id: string | null;
  name: string;
  step_type: StepType;
  started_at: string;
  ended_at: string | null;
  duration_ms: number | null;
  input: unknown;
  output: unknown;
  error: string | null;
  token_usage: TokenUsage | null;
  children: StepNode[];
}

export interface RunSummary {
  id: string;
  name: string;
  started_at: string;
  ended_at: string | null;
  status: RunStatus;
  metadata: Record<string, unknown>;
  step_count: number;
  total_prompt_tokens: number;
  total_completion_tokens: number;
  total_cost: number;
  duration_ms: number | null;
}

export interface RunDetail extends RunSummary {
  steps: StepNode[];
  slowest_step_id: string | null;
}

export interface ReplayResult {
  replay_id: string;
  step_id: string;
  requested_at: string;
  modified_input: unknown;
  original_output: unknown;
  replayed_output: unknown;
  token_usage: TokenUsage | null;
  error: string | null;
}
