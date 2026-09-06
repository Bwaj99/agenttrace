"use client";

import { useState } from "react";
import { stringifyValue } from "@/lib/format";

/**
 * A labeled, collapsible, pretty-printed JSON (or plain text) block.
 * Used for a step's input/output in the detail panel, and for
 * original/replayed output in the replay diff.
 */
export default function JsonBlock({
  label,
  value,
  defaultOpen = true,
}: {
  label: string;
  value: unknown;
  defaultOpen?: boolean;
}) {
  const [open, setOpen] = useState(defaultOpen);

  if (value === null || value === undefined) {
    return (
      <div className="text-xs text-gray-400 dark:text-gray-500">
        {label}: <span className="italic">none</span>
      </div>
    );
  }

  return (
    <div className="overflow-hidden rounded-md border border-gray-200 dark:border-gray-700">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="flex w-full items-center justify-between bg-gray-50 px-3 py-1.5 text-xs font-medium text-gray-600 dark:bg-gray-800 dark:text-gray-300"
      >
        <span>{label}</span>
        <span aria-hidden>{open ? "▾" : "▸"}</span>
      </button>
      {open && (
        <pre className="max-h-96 overflow-auto whitespace-pre-wrap break-words bg-white p-3 text-xs text-gray-800 dark:bg-gray-900 dark:text-gray-200">
          {stringifyValue(value)}
        </pre>
      )}
    </div>
  );
}
