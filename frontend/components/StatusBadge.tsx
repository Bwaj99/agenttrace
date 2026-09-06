import type { RunStatus } from "@/lib/types";

const STYLES: Record<string, string> = {
  completed: "bg-green-100 text-green-800 dark:bg-green-900/40 dark:text-green-300",
  failed: "bg-red-100 text-red-800 dark:bg-red-900/40 dark:text-red-300",
  running: "bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-300",
};
const FALLBACK_STYLE = "bg-gray-100 text-gray-800 dark:bg-gray-800 dark:text-gray-300";

export default function StatusBadge({ status }: { status: RunStatus }) {
  return (
    <span
      className={`inline-block whitespace-nowrap rounded-full px-2 py-0.5 text-xs font-medium ${
        STYLES[status] ?? FALLBACK_STYLE
      }`}
    >
      {status}
    </span>
  );
}
