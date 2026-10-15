import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { buildDynamicTask, validateTeachPlan } from "./plan.js";
import { _clearDynamicTasks, getTask, registerDynamicTask } from "./tasks.js";
import {
  _clearSessions,
  advanceSession,
  createSessionForTask,
  currentStep,
  getTaskForSession,
  isComplete,
} from "./session.js";
import { verifyStep } from "./verifier.js";
import { getTeachModePrompt, TEACH_MODE_RULES } from "./teach-mode.js";

function validPlan() {
  return {
    prompt: "Add pagination to this API",
    steps: [
      {
        title: "Decide the pagination inputs",
        instruction: "Decide which query params control page and limit.",
        why: "A clear contract keeps the API predictable.",
        file: "src/routes/items.js",
        fileHint: "Top of the route handler.",
        whatToType: "Read the current handler and note where page/limit would apply.",
        check: { kind: "contains", value: "page" } as const,
        checkDescription: "File mentions page.",
        hintL1: "Look for where the list is returned.",
        hintL2: "The handler needs to read two query params.",
        hintL3: "Read page and limit from the query string.",
      },
      {
        title: "Apply the limit",
        instruction: "Limit how many items the query returns.",
        why: "Limiting protects the server from huge responses.",
        file: "src/routes/items.js",
        fileHint: "Where the query runs.",
        whatToType: "Apply a limit to the query.",
        check: { kind: "contains", value: "limit" } as const,
        checkDescription: "File mentions limit.",
        hintL1: "Find the query.",
        hintL2: "The query builder has a limit option.",
        hintL3: "Call the limit method with the parsed limit.",
      },
      {
        title: "Apply the offset",
        instruction: "Skip items for earlier pages.",
        why: "Offset is what makes page 2 different from page 1.",
        file: "src/routes/items.js",
        fileHint: "Next to the limit.",
        whatToType: "Skip (page-1)*limit items.",
        check: { kind: "contains", value: "offset" } as const,
        checkDescription: "File mentions offset.",
        hintL1: "You need to skip, not just limit.",
        hintL2: "Offset depends on page and limit.",
        hintL3: "Offset is (page minus one) times limit.",
      },
      {
        title: "Return pagination metadata",
        instruction: "Return page, limit, and total alongside results.",
        why: "Clients need metadata to build next/prev links.",
        file: "src/routes/items.js",
        fileHint: "Where the response is built.",
        whatToType: "Include metadata in the response object.",
        check: { kind: "contains", value: "total" } as const,
        checkDescription: "File mentions total.",
        hintL1: "The response needs more than the list.",
        hintL2: "Include page, limit, total.",
        hintL3: "Add a meta object with page, limit, total.",
      },
    ],
    quiz: [
      {
        question: "What does offset do?",
        options: ["Skips items for earlier pages", "Sorts items"],
        answerIndex: 0,
        explanation: "Offset skips (page-1)*limit items.",
      },
      {
        question: "Why return metadata?",
        options: ["So clients can paginate", "To make responses bigger"],
        answerIndex: 0,
        explanation: "Metadata lets clients build next/prev.",
      },
    ],
  };
}

describe("teach_plan validation", () => {
  it("accepts a valid 4-step plan", () => {
    assert.deepEqual(validateTeachPlan(validPlan()), []);
  });

  it("rejects too few steps (2)", () => {
    const plan = validPlan();
    plan.steps = plan.steps.slice(0, 2);
    const errors = validateTeachPlan(plan);
    assert.ok(errors.some((e) => e.includes("steps") && e.includes("too few")));
  });

  it("rejects too many steps (8)", () => {
    const plan = validPlan();
    const extra = { ...plan.steps[0], title: "Extra step" };
    plan.steps = [...plan.steps, extra, extra, extra, extra];
    assert.equal(plan.steps.length, 8);
    const errors = validateTeachPlan(plan);
    assert.ok(errors.some((e) => e.includes("too many")));
  });

  it("rejects missing hintL3 and names the step", () => {
    const plan = validPlan();
    // @ts-expect-error testing invalid input
    delete plan.steps[1].hintL3;
    const errors = validateTeachPlan(plan);
    assert.ok(errors.some((e) => e.includes("steps[1]") && e.includes("hintL3")));
  });

  it("rejects a bad check kind and names the step", () => {
    const plan = validPlan();
    // @ts-expect-error testing invalid input
    plan.steps[0].check = { kind: "teleport" };
    const errors = validateTeachPlan(plan);
    assert.ok(errors.some((e) => e.includes("steps[0]") && e.includes("teleport")));
  });

  it("rejects a quiz with only 1 question", () => {
    const plan = validPlan();
    plan.quiz = plan.quiz.slice(0, 1);
    const errors = validateTeachPlan(plan);
    assert.ok(errors.some((e) => e.includes("quiz")));
  });
});

describe("dynamic tasks end-to-end", () => {
  it("valid plan creates a dynamic task, session starts at step 1 only", () => {
    _clearDynamicTasks();
    _clearSessions();
    const task = buildDynamicTask(validPlan());
    assert.ok(task.id.startsWith("teach-"));
    registerDynamicTask(task);
    assert.equal(getTask(task.id)?.id, task.id);
    const session = createSessionForTask(task, "teach");
    assert.equal(session.currentStepIndex, 0);
    assert.equal(currentStep(session).title, "Decide the pagination inputs");
    // Only step 1 is the current step — no full-solution dump.
    assert.equal(getTaskForSession(session).steps.length, 4);
  });

  it("check step pass advances; quiz returns questions", () => {
    _clearDynamicTasks();
    _clearSessions();
    const task = buildDynamicTask(validPlan());
    registerDynamicTask(task);
    const session = createSessionForTask(task, "teach");
    const step = currentStep(session);
    const result = verifyStep(step, { content: "const page = 1;", file: "src/routes/items.js" });
    assert.equal(result.pass, true);
    advanceSession(session);
    assert.equal(session.currentStepIndex, 1);
    assert.equal(session.stepsCompleted[0], step.id);
    assert.equal(getTaskForSession(session).quiz.length, 2);
    assert.equal(isComplete(session), false);
  });
});

describe("teach_mode_on", () => {
  it("returns rules + howToUse content via the prompt loader", () => {
    assert.ok(TEACH_MODE_RULES.length >= 5);
    assert.ok(TEACH_MODE_RULES[0].toLowerCase().includes("never write"));
    const prompt = getTeachModePrompt();
    assert.ok(prompt.includes("Teach Mode"));
    assert.ok(prompt.includes("Never write"));
    assert.ok(prompt.includes("teach_plan"));
    assert.ok(prompt.includes("JWT auth"));
  });
});
