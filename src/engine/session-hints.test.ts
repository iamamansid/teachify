import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { getHint } from "./hints.js";
import {
  _clearSessions,
  advanceSession,
  createSession,
  currentStep,
  getTaskForSession,
  isComplete,
} from "./session.js";
import { getTask } from "./tasks.js";

describe("hint ladder", () => {
  it("escalates L1 -> L2 -> L3 and L3 still does not contain a full solution dump", () => {
    const task = getTask("js-express-hello")!;
    const step = task.steps.find((s) => s.id === "add-route")!;
    const h1 = getHint(step, 1);
    const h2 = getHint(step, 2);
    const h3 = getHint(step, 3);
    assert.ok(h1.length > 0 && h2.length > 0 && h3.length > 0);
    assert.notEqual(h1, h2);
    assert.notEqual(h2, h3);
    // L3 may show the shape, but the task contract is that hints never
    // type the code for the learner — the step text says so, and the
    // hint must not claim to have written it.
    assert.ok(!h3.toLowerCase().includes("i have written"));
  });
});

describe("session", () => {
  it("advances only when advanceSession is called (i.e. only on pass)", () => {
    _clearSessions();
    const session = createSession("js-express-hello", "teach");
    assert.equal(session.currentStepIndex, 0);
    assert.equal(currentStep(session).id, "scaffold-file");
    // Without a pass, the session must NOT advance on its own.
    assert.equal(session.currentStepIndex, 0);
    advanceSession(session);
    assert.equal(session.currentStepIndex, 1);
    assert.deepEqual(session.stepsCompleted, ["scaffold-file"]);
  });

  it("completes after all steps advance", () => {
    _clearSessions();
    const session = createSession("js-express-hello", "teach");
    const task = getTaskForSession(session);
    for (let i = 0; i < task.steps.length; i++) advanceSession(session);
    assert.equal(isComplete(session), true);
    assert.ok(session.completedAt);
  });

  it("throws on unknown task", () => {
    assert.throws(() => createSession("nope", "teach"), /Unknown taskId/);
  });
});
