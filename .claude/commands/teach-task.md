---
description: "Start a pre-authored Teachify demo task and learn it step-by-step"
---

# /teach-task — guided demo task

Start one of Teachify's pre-authored demo tasks. The task id comes from `$ARGUMENTS` (e.g. `/teach-task js-express-hello`). Available ids: `js-express-hello`, `java-spring-hello`. If no id is given, list tasks with `teach_list_tasks` and ask which one to start.

## Procedure

1. Call `teach_start_task` with `{ taskId }`. It returns the task overview + **step 1 only** — never the full solution.
2. Show the learner the current step: instruction, why it matters, which file, and what to type (guidance, not the solution).
3. Wait for the learner to type it, then verify with `teach_check_step` (`{ sessionId, file, content }`).
   - Fail → targeted feedback, then `teach_hint` (levels 1 → 2 → 3).
   - Pass → next step (title-only preview).
4. When all steps pass, run `teach_quiz`. Ask each question **without** revealing `answerIndex`/`explanation`. Grade, explain, and point back to the step that taught any missed concept.

## Hard rules

- Never write the user's code. Never reveal the full solution.
- Hints escalate but never type the code — not even at level 3.
