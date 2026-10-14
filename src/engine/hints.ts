import type { TaskStep } from "./types";

/**
 * Escalating hint ladder. Level 3 is the most specific hint — it still
 * never types the code for the learner. The engine never returns a full
 * solution from any hint level.
 */
export function getHint(step: TaskStep, level: 1 | 2 | 3): string {
  switch (level) {
    case 1:
      return step.hintL1;
    case 2:
      return step.hintL2;
    case 3:
      return step.hintL3;
    default:
      return step.hintL1;
  }
}

export function hintForLevelLabel(level: number): string {
  if (level <= 1) return "nudge — direction, not the answer";
  if (level === 2) return "focused hint — the shape of the code";
  return "strong hint — almost there, you still type it";
}
