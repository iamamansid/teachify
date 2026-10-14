# Architecture — Teachify v0.1

## Teach Mode flow (any prompt) — the product

```
User prompt (same as for an agent)     LLM plans                Teachify enforces
"Implement JWT auth"          →  teach_mode_on (loads prompt)
                                →  teach_plan { prompt, steps, quiz }
                                     │  validate: 3-7 steps, hints, checks, quiz
                                     ▼
                               ┌──────────────────┐
                               │  Dynamic task    │  teach-<id> registered in-memory
                               │  + session       │  step 1 only returned
                               └──────────────────┘
                                     │
                                     ▼  guide loop (same as demo tasks)
                               teach_next_step → learner types → teach_check_step
                                     │  fail → teach_hint L1→L3
                                     ▼  pass → next step (title-only preview)
                               teach_quiz → teach_progress
```

**Why planning lives in the LLM:** it has the user's context — stack, files, existing code, error messages. A static planner cannot see those.

**Why enforcement lives in Teachify:** the LLM proposes, Teachify validates and enforces. Validation rejects bad plans (too few/many steps, missing hints, bad checks) before a session exists. Verification advances only on pass. Step-1-only + title-only previews make it structurally hard for the LLM to dump a full solution, even if it tries.

Dynamic tasks use the **same invariants** as pre-authored tasks (see Session flow below): never the full solution, advance only on pass, hints never type code, quiz answers LLM-only.

## Why MCP-first

Teachify is an **MCP server over stdio**, not a VS Code-only extension and not a desktop overlay.

- One server works in Claude Code, Cursor, Codex, VS Code, and any MCP client. No per-IDE rewrite.
- The LLM already has the chat UI, the model, and the user's trust. Teachify gives that LLM *teaching tools* — it doesn't need to own the UI.
- Stdio = local-first, no network, no API keys, no hosted service. The server reads task JSON from disk and verifies file content the client passes in.
- The VS Code extension is a **thin client**: it spawns the server and shows tasks / current step. All teaching logic stays in the server.

```
┌─────────────┐     MCP / stdio (JSON-RPC)     ┌──────────────────┐
│  LLM client │ ◄────────────────────────────► │ Teachify server  │
│ Claude Code │  tools/call: teach_*            │  src/server.ts   │
│ Cursor      │                                 │                  │
│ VS Code     │                                 │  engine/         │
└─────────────┘                                 │   tasks.ts       │
                                                │   session.ts     │
                                                │   verifier.ts    │
                                                │   hints.ts       │
                                                │  tasks/*.json    │
                                                └──────────────────┘
```

## Session flow

```
teach_start_task(taskId, mode)
  → createSession() → sessionId, step 1 (public fields only)
       │
       ▼
learner types the step in their editor
       │
       ▼
teach_check_step(sessionId, file?, content?)
  → verifier runs step.check against content / file on disk
  → FAIL: feedback + attempts++, suggest teach_hint. Session does NOT advance.
  → PASS: stepsCompleted.push, currentStepIndex++, return next-step title preview
       │
       ▼
teach_next_step(sessionId) → full instructions for current step
       │
       ▼ (repeat until currentStepIndex == steps.length)
teach_quiz(sessionId) → questions (LLM asks, grades, explains)
teach_progress(sessionId) → summary
```

Key invariants:

1. **Never the full solution.** `teach_start_task` returns step 1 only. `teach_next_step` returns the current step only. `teach_check_step` on pass returns a title-only preview of the next step.
2. **Advance only on pass.** The session advances only inside `teach_check_step` when the verifier returns `pass: true`. `teach_next_step` never advances.
3. **Hints never type code.** L1 = nudge, L2 = shape, L3 = strongest hint. L3 still requires the learner to type.
4. **Quiz answers are LLM-only.** `teach_quiz` returns `answerIndex` + `explanation` so the LLM can grade — the LLM must ask the learner first and not reveal them upfront.

## Task JSON schema

File: `src/tasks/<task-id>.json`. Validated on load by `engine/tasks.ts`.

```jsonc
{
  "id": "js-express-hello",
  "title": "Build GET /hello with Express (JavaScript)",
  "description": "...",
  "level": "beginner",               // beginner | intermediate | advanced
  "estimatedMinutes": 15,
  "learningOutcomes": ["..."],
  "steps": [
    {
      "id": "scaffold-file",
      "title": "Create server.js",
      "instruction": "What the learner should DO (not the code).",
      "why": "Why this step matters, 1-2 sentences.",
      "file": "server.js",          // relative file the learner edits
      "fileHint": "Where in the file, in human words.",
      "whatToType": "Guidance on what to type, without the full solution.",
      "check": { "kind": "fileExists" },   // see check kinds below
      "checkDescription": "Human-readable verification description.",
      "hintL1": "Nudge — direction, not the answer.",
      "hintL2": "Focused hint — the shape of the code.",
      "hintL3": "Strong hint — almost there, you still type it."
    }
  ],
  "quiz": [
    {
      "question": "...",
      "options": ["...", "..."],
      "answerIndex": 1,
      "explanation": "Why this answer is right."
    }
  ]
}
```

### Check kinds (`StepCheck`)

| kind | Fields | Meaning |
|---|---|---|
| `fileExists` | — | File must exist on disk (exact path, or basename search in cwd) |
| `regex` | `pattern`, `flags?` (default `"m"`) | File content must match the regex |
| `contains` | `value` | File content must contain the literal substring |
| `all` | `checks[]` | Every sub-check must pass |

Regex tips: use `flags: "ms"` when the pattern spans lines. Keep patterns forgiving (allow `const`/`let`/`var`, single/double quotes) — the verifier checks *learning*, not formatting.

## How to add a new task

1. Copy `src/tasks/js-express-hello.json` to `src/tasks/<your-task>.json`.
2. Fill in 3–7 steps. Each step: one action, one `why`, one check, three hints.
3. Write 2–3 quiz questions that test *understanding*, not recall of the exact code.
4. Run `npm run build && npm test`. The loader validates the schema; the verifier tests prove pass/fail behaviour.
5. Add the task id to `README.md` tasks list and to the VS Code quick-pick (optional).

## What is deliberately NOT in v0.1

- **No persistence.** Sessions (including dynamic Teach Mode tasks) live in an in-memory `Map`. Restarting the server clears sessions. v0.2 adds JSON-file persistence.
- **No browser overlay / pixel cursor.** The "ghost cursor" is a *conceptual* highlight (file + fileHint), not screen coordinates. The v0.3 browser overlay will highlight DOM nodes, not pixels — far more reliable than screenshot grounding.
- **No network calls, no API keys.** The server is local-first by design.
