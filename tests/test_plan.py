"""Port of teach-plan.test.ts: teach_plan validation + dynamic tasks end-to-end."""

import pytest

from teachify.engine import plan, session, tasks
from teachify.engine import teach_mode


def _step(**overrides):
    base = {
        "title": "Decide the pagination inputs",
        "instruction": "Decide which query params control page and limit.",
        "why": "A clear contract keeps the API predictable.",
        "file": "src/routes/items.js",
        "fileHint": "Top of the route handler.",
        "whatToType": "Read the current handler and note where page/limit would apply.",
        "check": {"kind": "contains", "value": "page"},
        "checkDescription": "File mentions page.",
        "hintL1": "Look for where the list is returned.",
        "hintL2": "The handler needs to read two query params.",
        "hintL3": "Read page and limit from the query string.",
    }
    base.update(overrides)
    return base


def _valid_plan():
    return {
        "prompt": "Add pagination to this API",
        "steps": [
            _step(),
            _step(
                title="Apply the limit",
                instruction="Limit how many items the query returns.",
                why="Limiting protects the server from huge responses.",
                fileHint="Where the query runs.",
                whatToType="Apply a limit to the query.",
                check={"kind": "contains", "value": "limit"},
                checkDescription="File mentions limit.",
                hintL1="Find the query.",
                hintL2="The query builder has a limit option.",
                hintL3="Call the limit method with the parsed limit.",
            ),
            _step(
                title="Apply the offset",
                instruction="Skip items for earlier pages.",
                why="Offset is what makes page 2 different from page 1.",
                fileHint="Next to the limit.",
                whatToType="Skip (page-1)*limit items.",
                check={"kind": "contains", "value": "offset"},
                checkDescription="File mentions offset.",
                hintL1="You need to skip, not just limit.",
                hintL2="Offset depends on page and limit.",
                hintL3="Offset is (page minus one) times limit.",
            ),
            _step(
                title="Return pagination metadata",
                instruction="Return page, limit, and total alongside results.",
                why="Clients need metadata to build next/prev links.",
                fileHint="Where the response is built.",
                whatToType="Include metadata in the response object.",
                check={"kind": "contains", "value": "total"},
                checkDescription="File mentions total.",
                hintL1="The response needs more than the list.",
                hintL2="Include page, limit, total.",
                hintL3="Add a meta object with page, limit, total.",
            ),
        ],
        "quiz": [
            {
                "question": "What does offset do?",
                "options": ["Skips items for earlier pages", "Sorts items"],
                "answerIndex": 0,
                "explanation": "Offset skips (page-1)*limit items.",
            },
            {
                "question": "Why return metadata?",
                "options": ["So clients can paginate", "To make responses bigger"],
                "answerIndex": 0,
                "explanation": "Metadata lets clients build next/prev.",
            },
        ],
    }


@pytest.fixture(autouse=True)
def clean_state():
    tasks.clear_dynamic_tasks()
    session.clear_sessions()
    yield
    tasks.clear_dynamic_tasks()
    session.clear_sessions()


def test_accepts_valid_4_step_plan():
    assert plan.validate_teach_plan(_valid_plan()) == []


def test_rejects_too_few_steps():
    payload = _valid_plan()
    payload["steps"] = payload["steps"][:2]
    errors = plan.validate_teach_plan(payload)
    assert any("steps" in e and "too few" in e for e in errors)


def test_rejects_too_many_steps():
    payload = _valid_plan()
    extra = dict(payload["steps"][0], title="Extra step")
    payload["steps"] = payload["steps"] + [extra] * 4
    assert len(payload["steps"]) == 8
    errors = plan.validate_teach_plan(payload)
    assert any("too many" in e for e in errors)


def test_rejects_missing_hintL3_and_names_step():
    payload = _valid_plan()
    del payload["steps"][1]["hintL3"]
    errors = plan.validate_teach_plan(payload)
    assert any("steps[1]" in e and "hintL3" in e for e in errors)


def test_rejects_bad_check_kind_and_names_step():
    payload = _valid_plan()
    payload["steps"][0]["check"] = {"kind": "teleport"}
    errors = plan.validate_teach_plan(payload)
    assert any("steps[0]" in e and "teleport" in e for e in errors)


def test_rejects_quiz_with_only_1_question():
    payload = _valid_plan()
    payload["quiz"] = payload["quiz"][:1]
    errors = plan.validate_teach_plan(payload)
    assert any("quiz" in e for e in errors)


def test_valid_plan_creates_dynamic_task_session_at_step_1_only():
    task = plan.build_dynamic_task(_valid_plan())
    assert task.id.startswith("teach-")
    tasks.register_dynamic_task(task)
    assert tasks.get_task(task.id).id == task.id
    sess = session.create_session_for_task(task, "teach")
    assert sess.current_step_index == 0
    assert session.current_step(sess).title == "Decide the pagination inputs"
    # Only step 1 is the current step — no full-solution dump.
    assert len(session.get_task_for_session(sess).steps) == 4


def test_check_step_pass_advances_and_quiz_returns():
    from teachify.engine.verifier import verify_step

    task = plan.build_dynamic_task(_valid_plan())
    tasks.register_dynamic_task(task)
    sess = session.create_session_for_task(task, "teach")
    step = session.current_step(sess)
    result = verify_step(step, content="const page = 1;", file="src/routes/items.js")
    assert result.passed is True
    session.advance_session(sess)
    assert sess.current_step_index == 1
    assert sess.steps_completed[0] == step.id
    assert len(session.get_task_for_session(sess).quiz) == 2
    assert session.is_complete(sess) is False


def test_teach_mode_on_returns_rules_and_prompt():
    assert len(teach_mode.TEACH_MODE_RULES) >= 5
    assert "never write" in teach_mode.TEACH_MODE_RULES[0].lower()
    prompt = teach_mode.get_teach_mode_prompt()
    assert "Teach Mode" in prompt
    assert "Never write" in prompt
    assert "teach_plan" in prompt
    assert "JWT auth" in prompt
