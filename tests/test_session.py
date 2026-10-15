"""Port of session-hints.test.ts + tasks.test.ts: hint ladder + session lifecycle + task loader."""

import pytest

from teachify.engine import hints, session, tasks


@pytest.fixture(autouse=True)
def clean_state():
    tasks.clear_dynamic_tasks()
    session.clear_sessions()
    tasks.clear_task_cache()
    yield
    tasks.clear_dynamic_tasks()
    session.clear_sessions()
    tasks.clear_task_cache()


# --- task loader ---


def test_loads_both_bundled_tasks():
    loaded = tasks.load_tasks()
    assert len(loaded) >= 2
    ids = {t.id for t in loaded}
    assert "js-express-hello" in ids
    assert "java-spring-hello" in ids


def test_each_task_has_5_steps_and_quiz():
    for task in tasks.load_tasks():
        assert len(task.steps) == 5, f"{task.id} should have 5 steps"
        assert len(task.quiz) >= 2, f"{task.id} should have >=2 quiz questions"
        for q in task.quiz:
            assert 0 <= q.answer_index < len(q.options)


def test_summaries_expose_id_title_level_steps():
    for summary in tasks.list_task_summaries():
        assert summary["id"] and summary["title"] and summary["level"] and summary["steps"] > 0


def test_get_task_returns_none_for_unknown_id():
    assert tasks.get_task("no-such-task") is None


# --- hint ladder ---


def test_hint_ladder_escalates_and_never_claims_to_have_written():
    task = tasks.get_task("js-express-hello")
    assert task is not None
    step = next(s for s in task.steps if s.id == "add-route")
    h1 = hints.get_hint(step, 1)
    h2 = hints.get_hint(step, 2)
    h3 = hints.get_hint(step, 3)
    assert h1 and h2 and h3
    assert h1 != h2
    assert h2 != h3
    # The hint must not claim to have written the code for the learner.
    assert "i have written" not in h3.lower()


# --- session lifecycle ---


def test_advances_only_when_advance_session_called():
    sess = session.create_session("js-express-hello", "teach")
    assert sess.current_step_index == 0
    assert session.current_step(sess).id == "scaffold-file"
    # Without a pass, the session must NOT advance on its own.
    assert sess.current_step_index == 0
    session.advance_session(sess)
    assert sess.current_step_index == 1
    assert sess.steps_completed == ["scaffold-file"]


def test_completes_after_all_steps_advance():
    sess = session.create_session("js-express-hello", "teach")
    task = session.get_task_for_session(sess)
    for _ in range(len(task.steps)):
        session.advance_session(sess)
    assert session.is_complete(sess) is True
    assert sess.completed_at is not None


def test_throws_on_unknown_task():
    with pytest.raises(ValueError, match="Unknown taskId"):
        session.create_session("nope", "teach")
