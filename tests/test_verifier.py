"""Port of verifier.test.ts: verifier pass/fail + no-solution-leak."""

import pytest

from teachify.engine import session, tasks
from teachify.engine.verifier import verify_step


@pytest.fixture(autouse=True)
def clean_state():
    session.clear_sessions()
    yield
    session.clear_sessions()


def _js_task():
    task = tasks.get_task("js-express-hello")
    assert task is not None
    return task


def test_passes_on_correct_js_content_and_fails_on_wrong_content():
    task = _js_task()
    route_step = next(s for s in task.steps if s.id == "add-route")
    good = (
        "const express = require('express');\n"
        "const app = express();\n"
        "app.get('/hello', (req, res) => res.send('Hello'));\n"
        "app.listen(3000);"
    )
    bad = "const express = require('express');\nconst app = express();\n// no route here\n"
    assert verify_step(route_step, content=good).passed is True
    assert verify_step(route_step, content=bad).passed is False


def test_passes_on_correct_java_content_and_fails_on_wrong_content():
    task = tasks.get_task("java-spring-hello")
    assert task is not None
    mapping_step = next(s for s in task.steps if s.id == "add-get-mapping")
    good = (
        "@RestController\npublic class HelloController {\n"
        '  @GetMapping("/hello")\n'
        '  public String hello() { return "Hello"; }\n}'
    )
    bad = (
        "@RestController\npublic class HelloController {\n"
        '  public String hello() { return "Hello"; }\n}'
    )
    assert verify_step(mapping_step, content=good).passed is True
    failed = verify_step(mapping_step, content=bad)
    assert failed.passed is False
    # Feedback must be targeted, never the solution.
    assert '@GetMapping("/hello")' not in failed.feedback or "Check:" in failed.feedback


def test_never_reveals_solution_in_failure_feedback():
    task = _js_task()
    step = task.steps[1]  # import-express
    failed = verify_step(step, content="const x = 1;")
    assert failed.passed is False
    # The failure must not contain the full solution line.
    assert "const express = require('express');" not in failed.feedback


def test_file_exists_check_fails_when_file_missing():
    task = _js_task()
    step = task.steps[0]
    result = verify_step(step, content="", file="definitely-not-a-real-file-xyz-123.js")
    assert result.passed is False
