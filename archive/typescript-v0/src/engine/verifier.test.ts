import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { verifyStep } from "./verifier.js";
import { getTask } from "./tasks.js";
import type { TaskStep } from "./types.js";

describe("verifier", () => {
  it("passes on correct JS content and fails on wrong content", () => {
    const task = getTask("js-express-hello")!;
    const routeStep = task.steps.find((s) => s.id === "add-route")!;
    const good = "const express = require('express');\nconst app = express();\napp.get('/hello', (req, res) => res.send('Hello'));\napp.listen(3000);";
    const bad = "const express = require('express');\nconst app = express();\n// no route here\n";
    assert.equal(verifyStep(routeStep, { content: good }).pass, true);
    assert.equal(verifyStep(routeStep, { content: bad }).pass, false);
  });

  it("passes on correct Java content and fails on wrong content", () => {
    const task = getTask("java-spring-hello")!;
    const mappingStep = task.steps.find((s) => s.id === "add-get-mapping")!;
    const good = "@RestController\npublic class HelloController {\n  @GetMapping(\"/hello\")\n  public String hello() { return \"Hello\"; }\n}";
    const bad = "@RestController\npublic class HelloController {\n  public String hello() { return \"Hello\"; }\n}";
    assert.equal(verifyStep(mappingStep, { content: good }).pass, true);
    const failed = verifyStep(mappingStep, { content: bad });
    assert.equal(failed.pass, false);
    // Feedback must be targeted, never the solution.
    assert.ok(!failed.feedback.includes("@GetMapping(\"/hello\")") || failed.feedback.includes("Check:"));
  });

  it("never reveals the solution in failure feedback", () => {
    const task = getTask("js-express-hello")!;
    const step: TaskStep = task.steps[1]; // import-express
    const failed = verifyStep(step, { content: "const x = 1;" });
    assert.equal(failed.pass, false);
    // The failure must not contain the full solution line.
    assert.ok(!failed.feedback.includes("const express = require('express');"));
  });

  it("fileExists check fails when file is missing", () => {
    const task = getTask("js-express-hello")!;
    const step = task.steps[0];
    const result = verifyStep(step, { content: "", file: "definitely-not-a-real-file-xyz-123.js" });
    assert.equal(result.pass, false);
  });
});
