import { randomUUID } from "node:crypto";
import type { QuizQuestion, StepCheck, TaskStep, TeachTask } from "./types";

export interface TeachPlanStepInput {
  id?: string;
  title?: string;
  instruction?: string;
  why?: string;
  file?: string;
  fileHint?: string;
  whatToType?: string;
  check?: StepCheck;
  checkDescription?: string;
  hintL1?: string;
  hintL2?: string;
  hintL3?: string;
}

export interface TeachPlanQuizInput {
  question?: string;
  options?: string[];
  answerIndex?: number;
  explanation?: string;
}

export interface TeachPlanInput {
  prompt?: string;
  steps?: TeachPlanStepInput[];
  quiz?: TeachPlanQuizInput[];
  title?: string;
}

const CHECK_KINDS = new Set(["fileExists", "regex", "contains", "all"]);

function isNonEmpty(v: unknown): v is string {
  return typeof v === "string" && v.trim().length > 0;
}

function validateCheck(check: unknown, where: string, errors: string[]): void {
  if (!check || typeof check !== "object") {
    errors.push(`${where}: check is required and must be an object`);
    return;
  }
  const c = check as Record<string, unknown>;
  if (!isNonEmpty(c.kind as string)) {
    errors.push(`${where}: check.kind is required`);
    return;
  }
  if (!CHECK_KINDS.has(c.kind as string)) {
    errors.push(
      `${where}: check.kind "${String(c.kind)}" is invalid — must be one of fileExists, regex, contains, all`
    );
    return;
  }
  if (c.kind === "regex" && !isNonEmpty(c.pattern as string)) {
    errors.push(`${where}: check.kind "regex" requires a non-empty check.pattern`);
  }
  if (c.kind === "contains" && !isNonEmpty(c.value as string)) {
    errors.push(`${where}: check.kind "contains" requires a non-empty check.value`);
  }
  if (c.kind === "all") {
    if (!Array.isArray(c.checks) || c.checks.length === 0) {
      errors.push(`${where}: check.kind "all" requires a non-empty check.checks array`);
    } else {
      c.checks.forEach((sub: unknown, i: number) =>
        validateCheck(sub, `${where}.check.checks[${i}]`, errors)
      );
    }
  }
  // Regex must compile.
  if (c.kind === "regex" && isNonEmpty(c.pattern as string)) {
    try {
      new RegExp(c.pattern as string, typeof c.flags === "string" ? c.flags : "m");
    } catch {
      errors.push(`${where}: check.pattern "${String(c.pattern)}" is not a valid regex`);
    }
  }
}

/** Validate a teach_plan payload. Returns all errors; empty = valid. */
export function validateTeachPlan(input: TeachPlanInput): string[] {
  const errors: string[] = [];
  if (!isNonEmpty(input.prompt)) {
    errors.push("prompt: must be a non-empty string");
  }
  if (!Array.isArray(input.steps)) {
    errors.push("steps: must be an array of 3-7 steps");
    return errors;
  }
  if (input.steps.length < 3) {
    errors.push(
      `steps: too few — got ${input.steps.length}, need 3-7 steps. Split the prompt into smaller steps instead of making each step huge.`
    );
  }
  if (input.steps.length > 7) {
    errors.push(
      `steps: too many — got ${input.steps.length}, need 3-7 steps. The prompt is too big; teach the first slice now and split the rest.`
    );
  }
  input.steps.forEach((step, i) => {
    const where = `steps[${i}]${step?.title ? ` ("${step.title}")` : ""}`;
    if (!step || typeof step !== "object") {
      errors.push(`${where}: must be an object`);
      return;
    }
    if (!isNonEmpty(step.title)) errors.push(`${where}: title is required and must be non-empty`);
    if (!isNonEmpty(step.instruction)) errors.push(`${where}: instruction is required and must be non-empty`);
    if (!isNonEmpty(step.why)) errors.push(`${where}: why is required and must be non-empty`);
    if (!isNonEmpty(step.file)) errors.push(`${where}: file is required and must be non-empty`);
    if (!isNonEmpty(step.hintL1)) errors.push(`${where}: hintL1 is required and must be non-empty`);
    if (!isNonEmpty(step.hintL2)) errors.push(`${where}: hintL2 is required and must be non-empty`);
    if (!isNonEmpty(step.hintL3)) errors.push(`${where}: hintL3 is required and must be non-empty`);
    validateCheck(step.check, `${where}.check`, errors);
  });
  if (input.quiz !== undefined) {
    if (!Array.isArray(input.quiz)) {
      errors.push("quiz: must be an array of 2-3 questions when present");
    } else {
      if (input.quiz.length < 2 || input.quiz.length > 3) {
        errors.push(`quiz: must have 2-3 questions when present, got ${input.quiz.length}`);
      }
      input.quiz.forEach((q, i) => {
        const where = `quiz[${i}]`;
        if (!q || typeof q !== "object") {
          errors.push(`${where}: must be an object`);
          return;
        }
        if (!isNonEmpty(q.question)) errors.push(`${where}: question is required and must be non-empty`);
        if (!Array.isArray(q.options) || q.options.length < 2) {
          errors.push(`${where}: options must be an array with at least 2 options`);
        }
        if (
          typeof q.answerIndex !== "number" ||
          !Number.isInteger(q.answerIndex) ||
          (Array.isArray(q.options) && (q.answerIndex < 0 || q.answerIndex >= q.options.length))
        ) {
          errors.push(`${where}: answerIndex must be a valid index into options`);
        }
        if (!isNonEmpty(q.explanation)) errors.push(`${where}: explanation is required and must be non-empty`);
      });
    }
  }
  return errors;
}

function slugify(title: string, index: number): string {
  const slug = title
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "")
    .slice(0, 40);
  return slug ? `${slug}-${index + 1}` : `step-${index + 1}`;
}

/**
 * Build a TeachTask from a validated teach_plan payload.
 * Caller must run validateTeachPlan first. Fills defaults for optional
 * fields (id, fileHint, whatToType, checkDescription, quiz) — the
 * required fields are guaranteed by validation.
 */
export function buildDynamicTask(input: TeachPlanInput): TeachTask {
  const steps: TaskStep[] = (input.steps ?? []).map((s, i) => ({
    id: isNonEmpty(s.id) ? s.id!.trim() : slugify(s.title ?? "", i),
    title: (s.title ?? "").trim(),
    instruction: (s.instruction ?? "").trim(),
    why: (s.why ?? "").trim(),
    file: (s.file ?? "").trim(),
    fileHint: isNonEmpty(s.fileHint) ? s.fileHint!.trim() : `In ${s.file}`,
    whatToType: isNonEmpty(s.whatToType) ? s.whatToType!.trim() : (s.instruction ?? "").trim(),
    check: s.check as StepCheck,
    checkDescription: isNonEmpty(s.checkDescription)
      ? s.checkDescription!.trim()
      : `Verify: ${s.title}`,
    hintL1: (s.hintL1 ?? "").trim(),
    hintL2: (s.hintL2 ?? "").trim(),
    hintL3: (s.hintL3 ?? "").trim(),
  }));

  const quiz: QuizQuestion[] =
    input.quiz && input.quiz.length > 0
      ? input.quiz.map((q) => ({
          question: (q.question ?? "").trim(),
          options: (q.options ?? []).map((o) => String(o)),
          answerIndex: q.answerIndex ?? 0,
          explanation: (q.explanation ?? "").trim(),
        }))
      : [
          {
            question: `What did you build in this task, in your own words?`,
            options: ["A step I typed and verified myself", "A snippet the AI wrote for me"],
            answerIndex: 0,
            explanation:
              "In Teach Mode you type every line and verify each step — that is how the skill sticks.",
          },
          {
            question: `What should you do when a step fails verification?`,
            options: [
              "Read the feedback, try again, and use teach_hint if stuck",
              "Ask the AI to write the step for you",
            ],
            answerIndex: 0,
            explanation:
              "Failing verification is part of learning. Feedback + hints guide you; the AI never types the code.",
          },
        ];

  const shortId = randomUUID().replace(/-/g, "").slice(0, 8);
  const prompt = (input.prompt ?? "").trim();
  return {
    id: `teach-${shortId}`,
    title: isNonEmpty(input.title) ? input.title!.trim() : `Teach: ${prompt.slice(0, 80)}`,
    description: `Teach Mode plan for: ${prompt}`,
    level: "beginner",
    estimatedMinutes: 15 + steps.length * 3,
    learningOutcomes: [`Complete: ${prompt}`, "Explain each step in your own words"],
    steps,
    quiz,
  };
}
