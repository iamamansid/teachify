import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { getTask, listTaskSummaries, loadTasks } from "./tasks.js";

describe("task loader", () => {
  it("loads both bundled tasks", () => {
    const tasks = loadTasks();
    assert.ok(tasks.length >= 2);
    assert.ok(tasks.some((t) => t.id === "js-express-hello"));
    assert.ok(tasks.some((t) => t.id === "java-spring-hello"));
  });

  it("each task has 5 steps and a quiz", () => {
    for (const t of loadTasks()) {
      assert.equal(t.steps.length, 5, `${t.id} should have 5 steps`);
      assert.ok(t.quiz.length >= 2, `${t.id} should have >=2 quiz questions`);
      for (const q of t.quiz) {
        assert.ok(q.answerIndex >= 0 && q.answerIndex < q.options.length);
      }
    }
  });

  it("summaries expose id/title/level/steps", () => {
    const summaries = listTaskSummaries();
    for (const s of summaries) {
      assert.ok(s.id && s.title && s.level && s.steps > 0);
    }
  });

  it("getTask returns undefined for unknown id", () => {
    assert.equal(getTask("no-such-task"), undefined);
  });
});
