/** Shared helpers for walking a run's nested step tree. */

import type { StepNode } from "./types";

/** Depth-first flatten of a step tree — parent always appears before its children. */
export function flattenSteps(steps: StepNode[]): StepNode[] {
  const out: StepNode[] = [];
  const walk = (list: StepNode[]) => {
    for (const step of list) {
      out.push(step);
      walk(step.children);
    }
  };
  walk(steps);
  return out;
}

/** Same traversal, paired with each step's nesting depth (0 = top-level). */
export function flattenStepsWithDepth(
  steps: StepNode[],
  depth = 0
): { step: StepNode; depth: number }[] {
  const out: { step: StepNode; depth: number }[] = [];
  for (const step of steps) {
    out.push({ step, depth });
    out.push(...flattenStepsWithDepth(step.children, depth + 1));
  }
  return out;
}
