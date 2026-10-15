// Teachify core types. Keep these stable — they are the contract
// between task JSON files, the verifier, the MCP tools, and clients.

export type TeachMode = "teach" | "hint" | "do";

export type CheckKind = "fileExists" | "regex" | "contains" | "all";

export interface StepCheck {
  kind: CheckKind;
  /** For kind=regex: regex source (no surrounding slashes). Flags default to "m". */
  pattern?: string;
  /** For kind=contains: literal substring that must be present. */
  value?: string;
  /** For kind=all: every sub-check must pass. */
  checks?: StepCheck[];
  /** Optional regex flags, e.g. "ms" for multiline+dotall. */
  flags?: string;
}

export interface QuizQuestion {
  question: string;
  options: string[];
  /** Index into options — for LLM grading only. The LLM must NOT reveal this upfront. */
  answerIndex: number;
  explanation: string;
}

export interface TaskStep {
  id: string;
  title: string;
  /** What the learner should DO (not the code itself). */
  instruction: string;
  /** Why this step matters — the mental model, in 1-2 sentences. */
  why: string;
  /** Relative file the learner should edit, e.g. "server.js". */
  file: string;
  /** Where in the file, in human words — never pixel coordinates. */
  fileHint: string;
  /** Guidance on what to type, without pasting the full solution. */
  whatToType: string;
  check: StepCheck;
  /** Human-readable description of how the step is verified. */
  checkDescription: string;
  hintL1: string;
  hintL2: string;
  /** Level 3 is the most specific hint — it still never types the code for the learner. */
  hintL3: string;
}

export interface TeachTask {
  id: string;
  title: string;
  description: string;
  level: "beginner" | "intermediate" | "advanced";
  estimatedMinutes: number;
  /** What the learner will be able to explain after finishing. */
  learningOutcomes: string[];
  steps: TaskStep[];
  quiz: QuizQuestion[];
}

export interface Session {
  id: string;
  taskId: string;
  mode: TeachMode;
  startedAt: number;
  currentStepIndex: number;
  /** Step ids the learner has passed verification for. */
  stepsCompleted: string[];
  /** Attempts per step id. */
  attempts: Record<string, number>;
  hintsUsed: number;
  /** Free-text mastery notes appended by the engine (e.g. "needed 2 hints on routing"). */
  masteryNotes: string[];
  completedAt?: number;
}

export interface VerifyResult {
  pass: boolean;
  feedback: string;
  /** Which check failed, for targeted feedback. */
  failedCheck?: string;
}

export interface PublicStep {
  stepId: string;
  stepNumber: number;
  totalSteps: number;
  title: string;
  instruction: string;
  why: string;
  file: string;
  fileHint: string;
  whatToType: string;
  checkDescription: string;
}
