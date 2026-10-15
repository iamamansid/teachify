import * as fs from "node:fs";
import * as path from "node:path";
import type { StepCheck, TaskStep, VerifyResult } from "./types";

function checkOne(check: StepCheck, content: string, filePath?: string): VerifyResult {
  switch (check.kind) {
    case "fileExists": {
      if (!filePath) {
        return {
          pass: false,
          feedback:
            "I could not verify this step because no file was provided. Create the file, then run teach_check_step again with the file path.",
          failedCheck: "fileExists (no file given)",
        };
      }
      const abs = path.isAbsolute(filePath)
        ? filePath
        : path.join(process.cwd(), filePath);
      // Also accept a bare filename match: the learner may pass "server.js"
      // while the file lives in a demo folder. Try the exact path first,
      // then a recursive basename search in cwd (depth-limited, best-effort).
      if (fs.existsSync(abs)) return { pass: true, feedback: `Found ${filePath}.` };
      const found = findByBasename(process.cwd(), path.basename(filePath), 3);
      if (found) return { pass: true, feedback: `Found ${found}.` };
      return {
        pass: false,
        feedback: `I could not find "${filePath}" yet. Create it first, then check again.`,
        failedCheck: "fileExists",
      };
    }
    case "regex": {
      if (!check.pattern) {
        return { pass: false, feedback: "Task definition error: regex check has no pattern.", failedCheck: "regex" };
      }
      let re: RegExp;
      try {
        re = new RegExp(check.pattern, check.flags ?? "m");
      } catch (e) {
        return { pass: false, feedback: `Task definition error: invalid regex ${check.pattern}.`, failedCheck: "regex" };
      }
      if (re.test(content)) return { pass: true, feedback: "Pattern matched." };
      return {
        pass: false,
        feedback:
          "That pattern is not in your file yet. Re-read the step's what-to-type guidance and check spelling, quotes, and parentheses.",
        failedCheck: `regex ${check.pattern}`,
      };
    }
    case "contains": {
      if (!check.value) {
        return { pass: false, feedback: "Task definition error: contains check has no value.", failedCheck: "contains" };
      }
      if (content.includes(check.value)) return { pass: true, feedback: `Found "${check.value}".` };
      return {
        pass: false,
        feedback: `Your file does not contain "${check.value}" yet. Add it, then check again.`,
        failedCheck: `contains ${check.value}`,
      };
    }
    case "all": {
      if (!check.checks || check.checks.length === 0) {
        return { pass: false, feedback: "Task definition error: all check has no sub-checks.", failedCheck: "all" };
      }
      for (const sub of check.checks) {
        const r = checkOne(sub, content, filePath);
        if (!r.pass) return r;
      }
      return { pass: true, feedback: "All checks passed." };
    }
    default:
      return { pass: false, feedback: `Unknown check kind ${(check as { kind: string }).kind}.`, failedCheck: "unknown" };
  }
}

function findByBasename(dir: string, basename: string, depth: number): string | null {
  if (depth < 0) return null;
  let entries: fs.Dirent[];
  try {
    entries = fs.readdirSync(dir, { withFileTypes: true });
  } catch {
    return null;
  }
  for (const e of entries) {
    if (e.name === "node_modules" || e.name === ".git" || e.name === "dist") continue;
    const full = path.join(dir, e.name);
    if (e.isFile() && e.name === basename) return full;
    if (e.isDirectory()) {
      const hit = findByBasename(full, basename, depth - 1);
      if (hit) return hit;
    }
  }
  return null;
}

/**
 * Verify a step. The caller may pass `content` (file text) and/or `file`
 * (path). If only `file` is given, the verifier reads it from disk.
 * NEVER returns the solution — only pass/fail + targeted feedback.
 */
export function verifyStep(
  step: TaskStep,
  opts: { content?: string; file?: string }
): VerifyResult {
  let content = opts.content ?? "";
  const file = opts.file ?? step.file;

  if (!content && file) {
    const abs = path.isAbsolute(file) ? file : path.join(process.cwd(), file);
    if (fs.existsSync(abs)) {
      content = fs.readFileSync(abs, "utf-8");
    } else {
      const found = findByBasename(process.cwd(), path.basename(file), 3);
      if (found) content = fs.readFileSync(found, "utf-8");
    }
  }

  // fileExists checks don't need content; other checks do.
  if (step.check.kind === "fileExists") {
    return checkOne(step.check, content, file);
  }
  if (!content) {
    return {
      pass: false,
      feedback:
        `I have no file content to check for "${step.title}". Pass the file text as "content" ` +
        `or make sure "${file}" exists on disk, then try again.`,
      failedCheck: "no-content",
    };
  }
  const result = checkOne(step.check, content, file);
  if (!result.pass) {
    return {
      ...result,
      feedback: `${result.feedback} (Check: ${step.checkDescription})`,
    };
  }
  return result;
}
