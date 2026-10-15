"""Task loading: bundled JSON tasks (package data) + Teach Mode dynamic tasks."""

from __future__ import annotations

import json
from importlib import resources

from .types import QuizQuestion, StepCheck, TaskStep, TeachTask

_REQUIRED_STEP_FIELDS = [
    "id",
    "title",
    "instruction",
    "why",
    "file",
    "fileHint",
    "whatToType",
    "check",
    "checkDescription",
    "hintL1",
    "hintL2",
    "hintL3",
]


def _tasks_dir():
    """Locate bundled task JSON files via package data.

    Raises a clear, actionable error when nothing is found (instead of a
    traceback) so a broken install tells the user what to do.
    """
    try:
        tasks_pkg = resources.files("teachify") / "tasks"
        if tasks_pkg.is_dir():
            names = [p.name for p in tasks_pkg.iterdir() if p.name.endswith(".json")]
            if names:
                return tasks_pkg
    except Exception:
        pass
    raise RuntimeError(
        "Teachify: no task JSON files found in the installed package. "
        "Reinstall with `pip install --force-reinstall teachify` and make sure "
        "package data is included."
    )


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


def _coerce_step(raw: dict) -> TaskStep:
    return TaskStep(
        id=raw.get("id", ""),
        title=raw.get("title", ""),
        instruction=raw.get("instruction", ""),
        why=raw.get("why", ""),
        file=raw.get("file", ""),
        file_hint=raw.get("fileHint", ""),
        what_to_type=raw.get("whatToType", ""),
        check=_coerce_check(raw.get("check")),
        check_description=raw.get("checkDescription", ""),
        hint_l1=raw.get("hintL1", ""),
        hint_l2=raw.get("hintL2", ""),
        hint_l3=raw.get("hintL3", ""),
    )


def _coerce_quiz(raw: dict) -> QuizQuestion:
    return QuizQuestion(
        question=raw.get("question", ""),
        options=[str(o) for o in (raw.get("options") or [])],
        answer_index=raw.get("answerIndex", 0),
        explanation=raw.get("explanation", ""),
    )


def validate_task(raw, source: str) -> TeachTask:
    """Validate one task JSON document; errors name the file and step."""
    if not isinstance(raw, dict):
        raise ValueError(f"Task {source}: not an object")
    task_id = raw.get("id")
    if not task_id or not isinstance(task_id, str):
        raise ValueError(f"Task {source}: missing id")
    steps = raw.get("steps")
    if not isinstance(steps, list) or not steps:
        raise ValueError(f"Task {source} ({task_id}): steps must be a non-empty array")
    quiz = raw.get("quiz")
    if not isinstance(quiz, list) or not quiz:
        raise ValueError(f"Task {source} ({task_id}): quiz must be a non-empty array")
    for step in steps:
        if not isinstance(step, dict):
            raise ValueError(f"Task {source} ({task_id}): a step is not an object")
        for key in _REQUIRED_STEP_FIELDS:
            val = step.get(key)
            if val is None or val == "":
                raise ValueError(
                    f"Task {source} ({task_id}) step {step.get('id', '?')}: missing {key}"
                )
    return TeachTask(
        id=task_id,
        title=raw.get("title", ""),
        description=raw.get("description", ""),
        level=raw.get("level", "beginner"),
        estimated_minutes=raw.get("estimatedMinutes", 15),
        learning_outcomes=list(raw.get("learningOutcomes") or []),
        steps=[_coerce_step(s) for s in steps],
        quiz=[_coerce_quiz(q) for q in quiz],
    )


_cache: list[TeachTask] | None = None
_dynamic_tasks: dict[str, TeachTask] = {}


def register_dynamic_task(task: TeachTask) -> None:
    """Register a Teach Mode dynamic task (from teach_plan)."""
    _dynamic_tasks[task.id] = task


def clear_dynamic_tasks() -> None:
    """Test-only: clear dynamic tasks."""
    _dynamic_tasks.clear()


def clear_task_cache() -> None:
    """Test-only: clear the loader cache so tests can reload."""
    global _cache
    _cache = None


def load_tasks() -> list[TeachTask]:
    """Load all bundled task definitions. Results are cached per process."""
    global _cache
    if _cache is not None:
        return _cache
    tasks: list[TeachTask] = []
    tasks_dir = _tasks_dir()
    for entry in sorted(tasks_dir.iterdir()):
        if not entry.name.endswith(".json"):
            continue
        try:
            raw = json.loads(entry.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise ValueError(f"Task {entry.name}: invalid JSON — {exc}") from exc
        tasks.append(validate_task(raw, entry.name))
    _cache = tasks
    return tasks


def get_task(task_id: str) -> TeachTask | None:
    dynamic = _dynamic_tasks.get(task_id)
    if dynamic is not None:
        return dynamic
    for task in load_tasks():
        if task.id == task_id:
            return task
    return None


def list_task_summaries() -> list[dict]:
    def summary(task: TeachTask) -> dict:
        return {
            "id": task.id,
            "title": task.title,
            "description": task.description,
            "level": task.level,
            "estimatedMinutes": task.estimated_minutes,
            "steps": len(task.steps),
        }

    return [summary(t) for t in load_tasks()] + [summary(t) for t in _dynamic_tasks.values()]


def list_known_task_ids() -> list[str]:
    return [t.id for t in load_tasks()]
