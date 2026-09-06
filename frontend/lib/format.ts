/** Small display-formatting helpers shared across pages/components. */

export function formatDuration(ms: number | null | undefined): string {
  if (ms == null) return "—";
  if (ms < 1000) return `${ms}ms`;
  return `${(ms / 1000).toFixed(2)}s`;
}

export function formatCost(cost: number | null | undefined): string {
  if (cost == null || cost === 0) return "—";
  return `$${cost.toFixed(6)}`;
}

/** Renders any step input/output/token value as readable text: plain
 * strings pass through, everything else is pretty-printed JSON. */
export function stringifyValue(value: unknown): string {
  if (value == null) return "";
  if (typeof value === "string") return value;
  return JSON.stringify(value, null, 2);
}

/** Best-effort extraction of the human-readable text from a step's
 * stored output, which may be a plain string, the SDK's {model, text}
 * shape for a recognized LLM response, or an arbitrary JSON value. */
export function extractOutputText(value: unknown): string {
  if (value == null) return "";
  if (typeof value === "string") return value;
  if (typeof value === "object" && "text" in (value as Record<string, unknown>)) {
    const text = (value as Record<string, unknown>).text;
    if (typeof text === "string") return text;
  }
  return JSON.stringify(value, null, 2);
}

/** Best-effort extraction of a prompt string from a step's stored
 * input, for pre-filling the replay textarea. */
export function extractPromptText(value: unknown): string {
  if (typeof value === "string") return value;
  if (value && typeof value === "object") {
    const obj = value as Record<string, unknown>;
    for (const key of ["prompt", "text", "input", "query"]) {
      if (typeof obj[key] === "string") return obj[key] as string;
    }
  }
  return JSON.stringify(value, null, 2);
}
