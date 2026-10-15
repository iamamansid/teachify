# Teach Mode — Full Spec

Teach Mode is the product. The pre-authored task library is the demo.

## What Teach Mode is

Like an Agent / Ask mode toggle, but for learning: when Teach Mode is on, the user asks with the **same prompt** they would give an agent — "implement JWT auth", "add pagination to this API", "fix this bug" — and the LLM **guides step-by-step instead of doing it**.

- Same prompt. Different behaviour.
- The user types every line. The LLM guides, verifies, hints, quizzes.

## When to use Teach Mode

Use it whenever the goal is learning, not just shipping:

| Prompt type | Example | Teach Mode does |
|---|---|---|
| Implement | "Implement JWT auth in Express" | Breaks into 5 steps, guides each |
| Add a feature | "Add pagination to this API" | Breaks into 4 steps, guides each |
| Fix | "Fix this null-pointer bug" | Breaks into reproduce → locate → fix → verify |
| Refactor | "Refactor this handler into a service" | Breaks into extract → wire → verify |
| Learn | "Teach me middleware" | Explains, then builds a 3-step task to try it |

Do **not** use Teach Mode when the user explicitly wants the work done for them (they said "just do it", "no teaching"). Teach Mode is opt-in per prompt.

## The loop

```
teach_mode_on
  → loads teachify/prompts/teach-mode.md (rules + examples)
teach_plan { prompt, steps, quiz }   (alias: teach_start_from_prompt)
  → Teachify validates → dynamic task teach-<id> + session → step 1 only
teach_next_step → learner types → teach_check_step
  → fail: feedback + teach_hint L1 → L2 → L3
  → pass: next step (title-only preview)
teach_quiz → teach_progress
```

## Step-sizing rules

- **3–7 steps.** Fewer than 3 = steps too big. More than 7 = prompt too big → split, teach the first slice now.
- **One action, one file, one concept per step.** If a step needs two files or two ideas, split it.
- **Each step must be verifiable** (see check-writing rules below).
- **Each step needs:** non-empty `title`, `instruction`, `why`, `file`, `hintL1`, `hintL2`, `hintL3`, valid `check`. Optional fields (`fileHint`, `whatToType`, `checkDescription`, `id`) get sensible defaults if omitted.

## Check-writing rules

| Kind | Use for | Example |
|---|---|---|
| `fileExists` | Scaffolding | Create the file |
| `regex` | Code patterns | Route / annotation / function present |
| `contains` | Literal must be present | File contains `page` |
| `all` | Combine sub-checks | File exists AND contains pattern |

- Keep regex **forgiving**: allow `const` / `let` / `var`, single / double quotes, optional semicolons. The verifier checks *learning*, not formatting.
- For `regex`, `pattern` must be non-empty and must compile. For `contains`, `value` must be non-empty. For `all`, `checks` must be a non-empty array (validated recursively).
- Never write a check that passes on an empty file. A check must prove the learner did the step.

## Hint rules

- L1 = nudge (direction, not the answer).
- L2 = shape (the shape of the code, not the code).
- L3 = strongest hint (almost there — the learner still types it).
- Hints never type code, never paste a full solution, never claim "I have written…".
- If the learner needs L3 twice on the same concept, the quiz should revisit that concept.

## Quiz rules

- 2–3 questions when a plan supplies a quiz. If the plan omits a quiz, Teachify supplies a default 2-question quiz (what you built + what to do on failure).
- Questions test **understanding**, not recall of exact code. ("What does signing a token prove?" not "What line did you type?")
- `answerIndex` + `explanation` are for LLM grading only. The LLM asks first, never reveals answers upfront.

## Failure modes

| Failure | What happens | What the LLM should do |
|---|---|---|
| Prompt too big (>7 steps) | `teach_plan` rejects: "too many steps" | Split — teach the first slice, say what comes next |
| Prompt too vague | No plan yet | Ask **1** clarifying question, then plan |
| Plan invalid (missing hint, bad check, <3 steps) | `teach_plan` rejects, naming step/field | Fix the named field, call `teach_plan` again. No session is created on rejection |
| Learner fails a check | `teach_check_step` returns pass:false + feedback | Feedback → hint → retry. Session does not advance |
| LLM tries to dump the full solution | Teachify returns step 1 only; `teach_check_step` preview is title-only | Do not paste remaining steps in chat. Guide one step at a time |
| Session lost (server restart) | In-memory sessions cleared (v0.2) | Re-plan with `teach_plan`. Persistence lands in v0.3 |

## Validation (what Teachify enforces)

`teach_plan` validation (`src/teachify/engine/plan.py`):

- `prompt` non-empty.
- `steps` is an array of 3–7.
- Each step: non-empty `title`, `instruction`, `why`, `file`, `hintL1`, `hintL2`, `hintL3`; valid `check`.
- `quiz`, if present: 2–3 questions, each with non-empty `question`, ≥2 `options`, valid `answerIndex`, non-empty `explanation`.

Invalid → `{ error, errors: [...] }`, no session created. Valid → dynamic task `teach-<id>` + session + step 1 only.

## System prompt

The canonical Teach Mode system prompt is `teachify/prompts/teach-mode.md` (shipped as package data), loaded by `teach_mode_on`. It contains the full rules, the vague/too-big handling, and two title-only examples (JWT auth → 5 steps, pagination → 4 steps). The loader falls back to an embedded rules summary if the file is missing, so `teach_mode_on` never fails.
