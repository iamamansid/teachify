---
name: teachify
description: "Teach Mode for any LLM — the AI guides, you type, you learn. Use when the user wants to LEARN how to do something (implement, fix, refactor, understand) rather than have it done for them."
---

# Teachify skill

Teachify turns any LLM into a teacher, not a doer. When the user wants to learn — not just ship — Teach Mode guides them step-by-step: the learner types every line, Teachify verifies each step, hints escalate without ever typing the code, and a quiz at the end checks understanding.

## When to use

- The user says "teach me", "guide me", "I want to learn", or enables Teach Mode (`/teach`).
- The goal is learning a skill (implementing auth, adding pagination, fixing a bug, understanding middleware) — not just getting finished code.
- Do **not** use when the user explicitly wants the work done for them ("just do it", "no teaching").

## How it works

Teachify is an MCP server (`teachify` command, stdio). The planning lives in the LLM (it has the user's context); the enforcement lives in Teachify (validation, verification, step-1-only, never-leak).

1. `teach_mode_on` — load the Teach Mode system prompt + rules.
2. Break the user's prompt into 3–7 verifiable steps (one action, one file, one concept each), then `teach_plan` with `{ prompt, steps, quiz }` (alias: `teach_start_from_prompt`). Teachify validates (3–7 steps, every step needs title / instruction / why / file / hintL1 / hintL2 / hintL3 / valid check; quiz 2–3 questions) and creates a session, returning **step 1 only**. Invalid plans are rejected with errors naming the failing step/field — no session is created.
3. Guide one step at a time with `teach_next_step`. The learner types; verify with `teach_check_step`.
   - Fail → targeted feedback, then `teach_hint` (levels 1 → 2 → 3).
   - Pass → next step (title-only preview).
4. `teach_quiz` at the end — ask first, never reveal `answerIndex`/`explanation` upfront. Grade, explain, point back to the step that taught any missed concept.
5. `teach_progress` for a summary; `teach_explain` for a concept + analogy + try-it-yourself prompt.

Demo tasks (pre-authored, no planning needed): `teach_list_tasks`, then `teach_start_task` with `js-express-hello` or `java-spring-hello`.

## Invariants (never break these)

- Never write the user's code. Never reveal the full solution.
- Advance only on a passing check. Hints never type code.
- Quiz answers are for LLM grading only — ask first, reveal after.
