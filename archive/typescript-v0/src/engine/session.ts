import { randomUUID } from "node:crypto";
import type { PublicStep, Session, TeachMode, TeachTask } from "./types";
import { getTask } from "./tasks";

const sessions = new Map<string, Session>();

export function createSession(taskId: string, mode: TeachMode = "teach"): Session {
  const task = getTask(taskId);
  if (!task) {
    throw new Error(
      `Unknown taskId "${taskId}". Available: ${listKnownTaskIds().join(", ")}`
    );
  }
  return createSessionForTask(task, mode);
}

/** Create a session for an already-resolved task (JSON or dynamic). */
export function createSessionForTask(task: TeachTask, mode: TeachMode = "teach"): Session {
  const session: Session = {
    id: randomUUID(),
    taskId: task.id,
    mode,
    startedAt: Date.now(),
    currentStepIndex: 0,
    stepsCompleted: [],
    attempts: {},
    hintsUsed: 0,
    masteryNotes: [],
  };
  sessions.set(session.id, session);
  return session;
}

export function getSession(sessionId: string): Session | undefined {
  return sessions.get(sessionId);
}

export function getTaskForSession(session: Session): TeachTask {
  const task = getTask(session.taskId);
  if (!task) throw new Error(`Session ${session.id} references unknown task ${session.taskId}`);
  return task;
}

export function currentStep(session: Session) {
  const task = getTaskForSession(session);
  return task.steps[session.currentStepIndex];
}

export function isComplete(session: Session): boolean {
  return session.currentStepIndex >= getTaskForSession(session).steps.length;
}

/** Mark the current step passed and advance. Returns the new current step (or undefined if done). */
export function advanceSession(session: Session): void {
  const task = getTaskForSession(session);
  const step = task.steps[session.currentStepIndex];
  if (step && !session.stepsCompleted.includes(step.id)) {
    session.stepsCompleted.push(step.id);
  }
  session.currentStepIndex += 1;
  if (isComplete(session)) session.completedAt = Date.now();
}

export function recordAttempt(session: Session, stepId: string): void {
  session.attempts[stepId] = (session.attempts[stepId] ?? 0) + 1;
}

export function toPublicStep(task: TeachTask, index: number): PublicStep {
  const step = task.steps[index];
  return {
    stepId: step.id,
    stepNumber: index + 1,
    totalSteps: task.steps.length,
    title: step.title,
    instruction: step.instruction,
    why: step.why,
    file: step.file,
    fileHint: step.fileHint,
    whatToType: step.whatToType,
    checkDescription: step.checkDescription,
  };
}

export function listKnownTaskIds(): string[] {
  // Lazy import to avoid a cycle at module load in tests.
  // eslint-disable-next-line @typescript-eslint/no-require-imports
  const { loadTasks } = require("./tasks") as typeof import("./tasks");
  return loadTasks().map((t) => t.id);
}

/** Test-only: clear all sessions. */
export function _clearSessions() {
  sessions.clear();
}
