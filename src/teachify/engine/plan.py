"""Teach Mode planning: validate a teach_plan payload and build a dynamic task."""

from __future__ import annotations

import re
import uuid

from .types import QuizQuestion, StepCheck, TaskStep, TeachTask

CHECK_KINDS = {"fileExists", "regex", "contains", "all"}


def _is_non_empty(value) -> bool:
    return isinstance(value, str) and value.strip() != ""


def _validate_check(check, where: str, errors: list[str]) -> None:
    if not isinstance(check, dict):
        errors.append(f"{where}: check is required and must be an object")
        return
    kind = check.get("kind")
    if not _is_non_empty(kind):
        errors.append(f"{where}: check.kind is required")
        return
    if kind not in CHECK_KINDS:
        errors.append(
            f'{where}: check.kind "{kind}" is invalid — must be one of fileExists, regex, contains, all'
        )
        return
    if kind == "regex":
        if not _is_non_empty(check.get("pattern")):
            errors.append(f'{where}: check.kind "regex" requires a non-empty check.pattern')
        else:
            try:
                re.compile(check["pattern"], re.MULTILINE)
            except re.error:
                errors.append(f'{where}: check.pattern "{check["pattern"]}" is not a valid regex')
    if kind == "contains" and not _is_non_empty(check.get("value")):
        errors.append(f'{where}: check.kind "contains" requires a non-empty check.value')
    if kind == "all":
        sub = check.get("checks")
        if not isinstance(sub, list) or not sub:
            errors.append(f'{where}: check.kind "all" requires a non-empty check.checks array')
        else:
            for i, item in enumerate(sub):
                _validate_check(item, f"{where}.check.checks[{i}]", errors)


def validate_teach_plan(payload: dict | None) -> list[str]:
    """Validate a teach_plan payload. Returns all errors; empty = valid."""
    errors: list[str] = []
    payload = payload or {}
    prompt = payload.get("prompt")
    steps = payload.get("steps")
    if not _is_non_empty(prompt):
        errors.append("prompt: must be a non-empty string")
    if not isinstance(steps, list):
        errors.append("steps: must be an array of 3-7 steps")
        return errors
    if len(steps) < 3:
        errors.append(
            f"steps: too few — got {len(steps)}, need 3-7 steps. "
            "Split the prompt into smaller steps instead of making each step huge."
        )
    if len(steps) > 7:
        errors.append(
            f"steps: too many — got {len(steps)}, need 3-7 steps. "
            "The prompt is too big; teach the first slice now and split the rest."
        )
    for i, step in enumerate(steps):
        title = step.get("title") if isinstance(step, dict) else None
        where = f"steps[{i}]" + (f' ("{title}")' if _is_non_empty(title) else "")
        if not isinstance(step, dict):
            errors.append(f"{where}: must be an object")
            continue
        if not _is_non_empty(step.get("title")):
            errors.append(f"{where}: title is required and must be non-empty")
        if not _is_non_empty(step.get("instruction")):
            errors.append(f"{where}: instruction is required and must be non-empty")
        if not _is_non_empty(step.get("why")):
            errors.append(f"{where}: why is required and must be non-empty")
        if not _is_non_empty(step.get("file")):
            errors.append(f"{where}: file is required and must be non-empty")
        if not _is_non_empty(step.get("hintL1")):
            errors.append(f"{where}: hintL1 is required and must be non-empty")
        if not _is_non_empty(step.get("hintL2")):
            errors.append(f"{where}: hintL2 is required and must be non-empty")
        if not _is_non_empty(step.get("hintL3")):
            errors.append(f"{where}: hintL3 is required and must be non-empty")
        _validate_check(step.get("check"), f"{where}.check", errors)

    quiz = payload.get("quiz")
    if quiz is not None:
        if not isinstance(quiz, list):
            errors.append("quiz: must be an array of 2-3 questions when present")
        else:
            if len(quiz) < 2 or len(quiz) > 3:
                errors.append(f"quiz: must have 2-3 questions when present, got {len(quiz)}")
            for i, q in enumerate(quiz):
                where = f"quiz[{i}]"
                if not isinstance(q, dict):
                    errors.append(f"{where}: must be an object")
                    continue
                if not _is_non_empty(q.get("question")):
                    errors.append(f"{where}: question is required and must be non-empty")
                options = q.get("options")
                if not isinstance(options, list) or len(options) < 2:
                    errors.append(f"{where}: options must be an array with at least 2 options")
                answer_index = q.get("answerIndex")
                if (
                    not isinstance(answer_index, int)
                    or isinstance(answer_index, bool)
                    or not isinstance(options, list)
                    or answer_index < 0
                    or answer_index >= len(options)
                ):
                    errors.append(f"{where}: answerIndex must be a valid index into options")
                if not _is_non_empty(q.get("explanation")):
                    errors.append(f"{where}: explanation is required and must be non-empty")
    return errors


def _slugify(title: str, index: int) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", (title or "").lower()).strip("-")[:40]
    return f"{slug}-{index + 1}" if slug else f"step-{index + 1}"


def _coerce_check(raw) -> StepCheck:
    raw = raw or {}
    sub = None
    if isinstance(raw.get("checks"), list):
        sub = [_coerce_check(c) for c in raw["checks"]]
    return StepCheck(
        kind=raw.get("kind", ""),
        pattern=raw.get("pattern"),
        value=raw.get("value"),
        checks=sub,
        flags=raw.get("flags"),
    )


def build_dynamic_task(payload: dict) -> TeachTask:
    """Build a TeachTask from a validated teach_plan payload.

    Call validate_teach_plan first. Fills defaults for optional fields
    (id, fileHint, whatToType, checkDescription, quiz) — the required
    fields are guaranteed by validation.
    """
    raw_steps = payload.get("steps") or []
    steps: list[TaskStep] = []
    for i, s in enumerate(raw_steps):
        step_id = s.get("id", "")
        step_id = step_id.strip() if _is_non_empty(step_id) else _slugify(s.get("title", ""), i)
        file_val = (s.get("file") or "").strip()
        steps.append(
            TaskStep(
                id=step_id,
                title=(s.get("title") or "").strip(),
                instruction=(s.get("instruction") or "").strip(),
                why=(s.get("why") or "").strip(),
                file=file_val,
                file_hint=(s.get("fileHint") or "").strip() or f"In {file_val}",
                what_to_type=(s.get("whatToType") or "").strip() or (s.get("instruction") or "").strip(),
                check=_coerce_check(s.get("check")),
                check_description=(s.get("checkDescription") or "").strip() or f"Verify: {s.get('title', '')}",
                hint_l1=(s.get("hintL1") or "").strip(),
                hint_l2=(s.get("hintL2") or "").strip(),
                hint_l3=(s.get("hintL3") or "").strip(),
            )
        )

    raw_quiz = payload.get("quiz")
    if raw_quiz:
        quiz = [
            QuizQuestion(
                question=(q.get("question") or "").strip(),
                options=[str(o) for o in (q.get("options") or [])],
                answer_index=q.get("answerIndex", 0),
                explanation=(q.get("explanation") or "").strip(),
            )
            for q in raw_quiz
        ]
    else:
        quiz = [
            QuizQuestion(
                question="What did you build in this task, in your own words?",
                options=["A step I typed and verified myself", "A snippet the AI wrote for me"],
                answer_index=0,
                explanation="In Teach Mode you type every line and verify each step — that is how the skill sticks.",
            ),
            QuizQuestion(
                question="What should you do when a step fails verification?",
                options=[
                    "Read the feedback, try again, and use teach_hint if stuck",
                    "Ask the AI to write the step for you",
                ],
                answer_index=0,
                explanation="Failing verification is part of learning. Feedback + hints guide you; the AI never types the code.",
            ),
        ]

    short_id = uuid.uuid4().hex[:8]
    prompt = (payload.get("prompt") or "").strip()
    title = (payload.get("title") or "").strip() or f"Teach: {prompt[:80]}"
    return TeachTask(
        id=f"teach-{short_id}",
        title=title,
        description=f"Teach Mode plan for: {prompt}",
        level="beginner",
        estimated_minutes=15 + len(steps) * 3,
        learning_outcomes=[f"Complete: {prompt}", "Explain each step in your own words"],
        steps=steps,
        quiz=quiz,
    )
