import * as fs from "node:fs";
import * as path from "node:path";
import type { TeachTask } from "./types";

/** Candidate directories that may hold task JSON files. */
function candidateTaskDirs(): string[] {
  const here = __dirname;
  return [
    path.join(here, "..", "tasks"), // dist/engine -> dist/tasks (after copy-tasks.js)
    path.join(here, "tasks"), // dist/engine/tasks (defensive)
    path.join(process.cwd(), "src", "tasks"),
    path.join(process.cwd(), "dist", "tasks"),
    path.join(process.cwd(), "teachify", "src", "tasks"),
  ];
}

function findTasksDir(): string {
  for (const dir of candidateTaskDirs()) {
    if (fs.existsSync(dir) && fs.statSync(dir).isDirectory()) {
      const files = fs.readdirSync(dir).filter((f) => f.endsWith(".json"));
      if (files.length > 0) return dir;
    }
  }
  throw new Error(
    `Teachify: no task JSON files found. Searched: ${candidateTaskDirs().join(", ")}. ` +
      `Run "npm run build" so scripts/copy-tasks.js copies src/tasks/*.json to dist/tasks/.`
  );
}

function validateTask(raw: unknown, file: string): TeachTask {
  const t = raw as Partial<TeachTask>;
  if (!t || typeof t !== "object") throw new Error(`Task ${file}: not an object`);
  if (!t.id || typeof t.id !== "string") throw new Error(`Task ${file}: missing id`);
  if (!Array.isArray(t.steps) || t.steps.length === 0)
    throw new Error(`Task ${file} (${t.id}): steps must be a non-empty array`);
  if (!Array.isArray(t.quiz) || t.quiz.length === 0)
    throw new Error(`Task ${file} (${t.id}): quiz must be a non-empty array`);
  for (const step of t.steps as unknown as Array<Record<string, unknown>>) {
    for (const key of [
      "id",
      "title",
      "instruction",
      "why",
      "file",
      "fileHint",
      "whatToType",
      "check",
      "checkDescription",
      "hintL1",
      "hintL2",
      "hintL3",
    ]) {
      if (step[key] === undefined || step[key] === null || step[key] === "") {
        throw new Error(`Task ${file} (${t.id}) step ${step.id ?? "?"}: missing ${key}`);
      }
    }
  }
  return t as TeachTask;
}

let cache: TeachTask[] | null = null;
const dynamicTasks = new Map<string, TeachTask>();

/** Register a Teach Mode dynamic task (from teach_plan). */
export function registerDynamicTask(task: TeachTask): void {
  dynamicTasks.set(task.id, task);
}

/** Test-only: clear dynamic tasks. */
export function _clearDynamicTasks(): void {
  dynamicTasks.clear();
}

/** Load all task definitions. Results are cached per process. */
export function loadTasks(): TeachTask[] {
  if (cache) return cache;
  const dir = findTasksDir();
  const tasks: TeachTask[] = [];
  for (const file of fs.readdirSync(dir).sort()) {
    if (!file.endsWith(".json")) continue;
    const raw = JSON.parse(fs.readFileSync(path.join(dir, file), "utf-8"));
    tasks.push(validateTask(raw, file));
  }
  cache = tasks;
  return tasks;
}

export function getTask(taskId: string): TeachTask | undefined {
  const dynamic = dynamicTasks.get(taskId);
  if (dynamic) return dynamic;
  return loadTasks().find((t) => t.id === taskId);
}

export function listTaskSummaries() {
  const json = loadTasks().map((t) => ({
    id: t.id,
    title: t.title,
    description: t.description,
    level: t.level,
    estimatedMinutes: t.estimatedMinutes,
    steps: t.steps.length,
  }));
  const dynamic = [...dynamicTasks.values()].map((t) => ({
    id: t.id,
    title: t.title,
    description: t.description,
    level: t.level,
    estimatedMinutes: t.estimatedMinutes,
    steps: t.steps.length,
  }));
  return [...json, ...dynamic];
}

/** Test-only: clear the loader cache so tests can reload. */
export function _clearTaskCache() {
  cache = null;
}
