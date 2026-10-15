"""Session store + Teach Mode session lifecycle."""

from __future__ import annotations

import time
import uuid

from .tasks import get_task
from .types import Session, TeachTask

_sessions: dict[str, Session] = {}


def create_session(task_id: str, mode: str = "teach") -> Session:
    task = get_task(task_id)
    if task is None:
        from .tasks import list_known_task_ids

        raise ValueError(f'Unknown taskId "{task_id}". Available: {", ".join(list_known_task_ids())}')
    return create_session_for_task(task, mode)


def create_session_for_task(task: TeachTask, mode: str = "teach") -> Session:
    """Create a session for an already-resolved task (JSON or dynamic)."""
    session = Session(
        id=uuid.uuid4().hex,
        task_id=task.id,
        mode=mode,
        started_at=time.time(),
        current_step_index=0,
    )
    _sessions[session.id] = session
    return session


def get_session(session_id: str) -> Session | None:
    return _sessions.get(session_id)


def get_task_for_session(session: Session) -> TeachTask:
    task = get_task(session.task_id)
    if task is None:
        raise ValueError(f"Session {session.id} references unknown task {session.task_id}")
    return task


def current_step(session: Session):
    task = get_task_for_session(session)
    return task.steps[session.current_step_index]


def is_complete(session: Session) -> bool:
    return session.current_step_index >= len(get_task_for_session(session).steps)


def advance_session(session: Session) -> None:
    """Mark the current step passed and advance. Only ever called on a passing check."""
    task = get_task_for_session(session)
    step = task.steps[session.current_step_index]
    if step and step.id not in session.steps_completed:
        session.steps_completed.append(step.id)
    session.current_step_index += 1
    if is_complete(session):
        session.completed_at = time.time()


def record_attempt(session: Session, step_id: str) -> None:
    session.attempts[step_id] = session.attempts.get(step_id, 0) + 1


def to_public_step(task: TeachTask, index: int) -> dict:
    """Public (solution-safe) view of one step."""
    step = task.steps[index]
    return {
        "stepId": step.id,
        "stepNumber": index + 1,
        "totalSteps": len(task.steps),
        "title": step.title,
        "instruction": step.instruction,
        "why": step.why,
        "file": step.file,
        "fileHint": step.file_hint,
        "whatToType": step.what_to_type,
        "checkDescription": step.check_description,
    }


def clear_sessions() -> None:
    """Test-only: clear all sessions."""
    _sessions.clear()
