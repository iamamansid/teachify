import * as fs from "node:fs";
import * as path from "node:path";

/**
 * Teach Mode system prompt loader.
 *
 * The canonical prompt lives in src/prompts/teach-mode.md (copied to
 * dist/prompts/teach-mode.md on build). If the file is missing at runtime
 * (e.g. tests running from a different cwd), fall back to the embedded
 * rules summary so teach_mode_on never fails.
 */

export const TEACH_MODE_RULES = [
  "Never write the user's code. The user types every line.",
  "Take the user's prompt as-is and break it into 3-7 verifiable steps (one action, one file, one concept each).",
  "Propose steps via teach_plan, then guide ONE step at a time.",
  "Wait for the user to type, verify via teach_check_step, hints L1-L3 never type code, quiz at end.",
  "If the prompt is vague, ask 1 clarifying question first, then plan.",
  "Never reveal the full solution. teach_plan returns step 1 only.",
];

export const TEACH_MODE_HOW_TO_USE =
  "1. Call teach_mode_on, 2. Break the user's prompt into steps, 3. Call teach_plan with {prompt, steps, quiz}, 4. Guide with teach_next_step/teach_check_step/teach_hint/teach_quiz";

export const TEACH_MODE_EXAMPLE_PROMPT = "Teach Mode on. Implement JWT auth.";

const FALLBACK_PROMPT = `# Teach Mode — System Prompt

You are in Teach Mode. You are a teacher, not a doer.

## Rules
${TEACH_MODE_RULES.map((r, i) => `${i + 1}. ${r}`).join("\n")}

## How to use
${TEACH_MODE_HOW_TO_USE}

## Example
User: "${TEACH_MODE_EXAMPLE_PROMPT}"
Assistant: breaks the prompt into 3-7 verifiable steps via teach_plan, then guides one step at a time. The learner types every line.
`;

function candidatePromptPaths(): string[] {
  const here = __dirname;
  return [
    path.join(here, "..", "prompts", "teach-mode.md"), // dist/engine -> dist/prompts
    path.join(here, "..", "..", "src", "prompts", "teach-mode.md"), // repo root layout
    path.join(process.cwd(), "src", "prompts", "teach-mode.md"),
    path.join(process.cwd(), "dist", "prompts", "teach-mode.md"),
    path.join(process.cwd(), "teachify", "src", "prompts", "teach-mode.md"),
  ];
}

/** Full Teach Mode system prompt text (file contents when available). */
export function getTeachModePrompt(): string {
  for (const p of candidatePromptPaths()) {
    try {
      if (fs.existsSync(p)) return fs.readFileSync(p, "utf-8");
    } catch {
      // try next candidate
    }
  }
  return FALLBACK_PROMPT;
}
