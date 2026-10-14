# Teachify — Learn by Doing

> **The AI guides. You type. You learn.**

Every LLM agent today is an autopilot: it writes the code, you watch, you learn nothing. Junior engineers are shipping code they can't explain or debug — and the research backs it: AI-assisted juniors scored lower on follow-up comprehension and debugging tests than peers who coded unaided.

Teachify flips the default. It's an **MCP connector** that turns any LLM (Claude Code, Cursor, Codex, VS Code) into a **teacher, not a doer**:

- The AI **guides** — step by step, with the *why* behind each step.
- **You type every line.** The AI never writes your code.
- The AI **verifies** each step (regex / file checks), gives **escalating hints** (L1 → L3, still never the solution), and **quizzes** you at the end so the learning sticks.

## 20-second demo

```
You:  "Teach me to build GET /hello in Express."
AI:   Step 1/5 — Create server.js. [why + where]
You:  [creates server.js]
AI:   ✅ Verified. Step 2/5 — Import Express at the top…
You:  [types const express = require('express');]
AI:   ✅ Verified. Step 3/5 — Create the app…
… 5 steps later …
AI:   🎉 All steps verified. Quiz: What does app.get() actually do?
You:  [answers — and can explain it]
```

Watch the full 20-sec video: *(add demo GIF / YouTube link on launch day)*

## How Teachify is different

Most AI coding help is autopilot: it writes the code, you watch, and you keep none of the skill. Teachify is built on the opposite principle — **guided doing**:

|  | Autopilot help | Teachify |
|---|---|---|
| Who writes the code | The AI | **You** |
| Step size | Whole solution at once | One verified step at a time |
| When you're stuck | It gives the answer | It gives an escalating hint — you still type it |
| What you keep after | A finished task | The skill + the finished task |
| How it checks learning | Nothing | Step verification + end-of-task quiz |

The core verbs are `teach_start_task`, `teach_check_step`, `teach_hint`, `teach_quiz` — tools for teaching, not for doing the work for you.

## Install

**Prerequisites:** Node 20+.

```bash
git clone https://github.com/iamamansid/teachify.git
cd teachify
npm install
npm run build
```

### Claude Code

Add to your project's `.mcp.json` (or `~/.claude.json`):

```json
{
  "mcpServers": {
    "teachify": {
      "command": "node",
      "args": ["/absolute/path/to/teachify/dist/server.js"]
    }
  }
}
```

Then in Claude Code:

```
> Teach me js-express-hello in Teach Mode.
```

### Cursor / Codex / any MCP client

Point your MCP client at the same command:

- Command: `node`
- Args: `["/absolute/path/to/teachify/dist/server.js"]`
- Transport: stdio

### VS Code (thin client)

The `vscode-extension/` folder is a thin client that lists tasks and shows the current step in a sidebar. It spawns the MCP server — all teaching logic stays in the server.

```bash
cd vscode-extension
npm install
npm run build
# then F5 in VS Code to run the extension host
```

## Tools

| Tool | What it does |
|---|---|
| `teach_list_tasks` | List available tasks |
| `teach_start_task { taskId, mode? }` | Start a task. Returns overview + **step 1 only**. Modes: `teach` (default, guide-only), `hint`, `do` (boilerplate only on explicit request, then quizzes you) |
| `teach_next_step { sessionId }` | Current step. Never skips ahead |
| `teach_check_step { sessionId, file?, content? }` | Verify the current step. Pass/fail + targeted feedback. On fail, never reveals the next solution |
| `teach_hint { sessionId, level? 1\|2\|3 }` | Escalating hints. L3 still does NOT type the code |
| `teach_quiz { sessionId }` | 2–3 questions. `answerIndex` is for LLM grading only — the LLM must ask first, not reveal answers |
| `teach_explain { concept, context? }` | Short explanation + analogy + try-it-yourself prompt |
| `teach_progress { sessionId }` | Steps done, time, attempts, hints, mastery notes |

## Example session (abridged)

```
User: Teach me java-spring-hello.
AI (teach_start_task): Session abc… — Build GET /hello with Spring Boot (Java).
  Step 1/5: Create HelloController.java. Why: Spring discovers controllers by scanning classes…
User: [creates the file]
AI (teach_check_step): ✅ Verified. Step 2/5: Add @RestController…
User: [types it, gets stuck]
AI (teach_hint level 1): Spring needs to know this class is a web controller. There is an annotation for that…
User: [types @RestController]
AI (teach_check_step): ✅ Verified…
… after step 5 …
AI (teach_quiz): Q1: What does @RestController do? …
```

## Tasks (v0.1)

- `js-express-hello` — Build GET /hello with Express, 5 steps, beginner
- `java-spring-hello` — Build GET /hello with Spring Boot `@RestController`, 5 steps, beginner

Add a new task: drop a JSON file in `src/tasks/` following the schema in `docs/ARCHITECTURE.md`, then `npm run build`. No server code changes needed.

## Roadmap

- **v0.2** — Real LLM planner: free-form "teach me X" → generated steps (still verified, still never auto-types). More tasks (React, SQL, Docker, DSA). Progress persistence (JSON file).
- **v0.3** — Browser overlay (ghost cursor highlight via DOM, not pixels) for web tasks (AWS console, GitHub, etc.).
- **v1.0** — Community task library + task sharing, mastery tracking, classroom mode.

## Contributing

See `CONTRIBUTING.md` (coming with first release) — TL;DR: new tasks are the best first PR. One JSON file + tests. No solution-dumping: every step must be verifiable and every hint must preserve the learner typing the code.

## Global Talent Visa note

Teachify is built as a **real tool for real learners**, not as a stars-chasing exercise. If you use it as GTV evidence, read `docs/GTV-EVIDENCE.md`: Tech Nation wants 1 mandatory + 2 optional criteria + 3 letters, judged holistically. Stars help, but forks, PRs, downloads, testimonials, talks, and media matter as much — and evidence that looks created solely for the application is penalised. Build the evidence by building the users.

## License

MIT — see `LICENSE`.
