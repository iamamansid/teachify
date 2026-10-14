# Teachify — Learn by Doing

> **The AI guides. You type. You learn.**

Every LLM agent today is an autopilot: it writes the code, you watch, you learn nothing. Junior engineers are shipping code they can't explain or debug — and the research backs it: AI-assisted juniors scored lower on follow-up comprehension and debugging tests than peers who coded unaided.

Teachify flips the default. It's an **MCP connector** that turns any LLM (Claude Code, Cursor, Codex, VS Code) into a **teacher, not a doer**:

- The AI **guides** — step by step, with the *why* behind each step.
- **You type every line.** The AI never writes your code.
- The AI **verifies** each step (regex / file checks), gives **escalating hints** (L1 → L3, still never the solution), and **quizzes** you at the end so the learning sticks.

## Teach Mode — same prompt, guided instead of done

Copilot has Agent / Ask modes. Teachify adds **Teach Mode for any LLM**.

Same prompt you would give an agent. Different result: instead of doing it, the LLM guides you through it, step by step.

```
You:  "Teach Mode on. Implement JWT auth."
AI:   Teach Mode on. Breaking "Implement JWT auth" into 5 steps…
      Step 1/5 — Create the auth route file. Why: … [file + what to type]
You:  [create the file]
AI:   ✅ Verified. Step 2/5 — Add the login endpoint shape…
You:  [type it, get stuck]
AI:   Hint (L1): … — you still type the code.
… after step 5 …
AI:   🎉 All steps verified. Quiz: What does signing a token actually prove?
You:  [answer — and can explain it]
```

### How it works

1. **Turn Teach Mode on** — call `teach_mode_on` to load the Teach Mode system prompt (`src/prompts/teach-mode.md`).
2. **Plan from any prompt** — the LLM breaks your prompt into 3–7 verifiable steps and calls `teach_plan` with `{ prompt, steps, quiz }` (alias: `teach_start_from_prompt`). Teachify validates the plan (3–7 steps, every step has instruction / why / file / hints / check, quiz 2–3 questions) and creates a session. Invalid plans are rejected with errors naming the failing step/field — no session is created.
3. **Guide / verify / quiz** — one step at a time with `teach_next_step` → you type → `teach_check_step` → `teach_hint` (L1–L3) if stuck → `teach_quiz` at the end.

The planning lives in the LLM (it has your context). The enforcement lives in Teachify (validation, verification, step-1-only, never-leak). See `docs/TEACH-MODE.md` for the full spec and `docs/ARCHITECTURE.md` for the flow.

### Try it instantly (no planning needed)

The two demo tasks below are pre-authored plans — same Teach Mode loop, zero planning. Start with one of these to feel the loop, then use Teach Mode on your own prompt.

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
| `teach_mode_on {}` | Turn on Teach Mode. Returns the system prompt + rules + how-to-use |
| `teach_plan { prompt, steps, quiz?, title?, mode? }` | Plan a session from ANY prompt. Validates 3–7 steps + 2–3 quiz Qs. Returns step 1 only |
| `teach_start_from_prompt { … }` | Alias of `teach_plan` — same schema, same behaviour |
| `teach_list_tasks` | List available tasks |
| `teach_start_task { taskId, mode? }` | Start a pre-authored demo task. Returns overview + **step 1 only**. Modes: `teach` (default, guide-only), `hint`, `do` (boilerplate only on explicit request, then quizzes you) |
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

## Tasks (v0.1) — demo library, not the product

The 2 pre-authored tasks are the demo library. **Teach Mode for any prompt is the product** (see top of this README).

- `js-express-hello` — Build GET /hello with Express, 5 steps, beginner
- `java-spring-hello` — Build GET /hello with Spring Boot `@RestController`, 5 steps, beginner

Add a new task: drop a JSON file in `src/tasks/` following the schema in `docs/ARCHITECTURE.md`, then `npm run build`. No server code changes needed.

## Roadmap

- **v0.2** — Planner quality + persistence: better step-sizing for big prompts, JSON-file session persistence, more demo tasks (React, SQL, Docker, DSA).
- **v0.3** — Browser overlay (highlight via DOM, not pixels) for web tasks (AWS console, GitHub, etc.).
- **v1.0** — Community task library + task sharing, mastery tracking, classroom mode.

## Contributing

See `CONTRIBUTING.md` (coming with first release) — TL;DR: new tasks are the best first PR. One JSON file + tests. No solution-dumping: every step must be verifiable and every hint must preserve the learner typing the code.

## Global Talent Visa note

Teachify is built as a **real tool for real learners**, not as a stars-chasing exercise. If you use it as GTV evidence, read `docs/GTV-EVIDENCE.md`: Tech Nation wants 1 mandatory + 2 optional criteria + 3 letters, judged holistically. Stars help, but forks, PRs, downloads, testimonials, talks, and media matter as much — and evidence that looks created solely for the application is penalised. Build the evidence by building the users.

## License

MIT — see `LICENSE`.
