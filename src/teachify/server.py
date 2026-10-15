"""Teachify MCP server (stdio).

Turns any MCP-capable LLM (Claude Code, Cursor, Codex, VS Code) into a
teacher, not a doer. The server NEVER writes code for the learner and
NEVER returns a full solution. It guides, verifies, hints, and quizzes.

Run:  teachify
Config (.mcp.json): { "mcpServers": { "teachify": { "command": "teachify" } } }
"""

from __future__ import annotations

import json
import time
from typing import Optional

from mcp.server.fastmcp import FastMCP

from .engine import hints, plan, session, tasks, teach_mode
from .engine.verifier import verify_step

mcp = FastMCP("teachify")


def _text(obj) -> str:
    """Serialize a tool result as a JSON text payload (parity with the v1 wire format)."""
    return json.dumps(obj, indent=2)


def _quiz_payload(question) -> dict:
    return {
        "question": question.question,
        "options": question.options,
        "answerIndex": question.answer_index,
        "explanation": question.explanation,
    }


CONCEPTS: dict[str, dict[str, str]] = {
    "rest": {
        "explanation": (
            "REST is a style for web APIs: resources (like /hello) are addressed by URLs, "
            "and HTTP verbs (GET, POST, PUT, DELETE) say what to do with them. "
            "GET should only read, never change data."
        ),
        "analogy": "Like a library: the URL is the shelf address, GET is 'let me read this book', POST is 'add a new book'.",
        "tryIt": "In your own words, explain why GET /hello should not create a user. Then name one POST endpoint you would add to a todo API.",
    },
    "express": {
        "explanation": (
            "Express is a minimal Node.js web framework. You create an app with express(), "
            "register routes with app.get()/app.post(), and start listening with app.listen(). "
            "Each route maps a URL + verb to a handler (req, res)."
        ),
        "analogy": "Like a reception desk: routes are the directory board — 'GET /hello → talk to this person'.",
        "tryIt": "Without looking at your code: what does app.listen() do, and what happens if you forget it?",
    },
    "spring-boot": {
        "explanation": (
            "Spring Boot is an opinionated Java framework that wires up a web server, dependency "
            "injection, and routing for you. @RestController marks a class as a web controller; "
            "@GetMapping binds a method to HTTP GET on a path."
        ),
        "analogy": "Like a restaurant: @RestController is the kitchen, @GetMapping is the menu — 'GET /hello → this dish'.",
        "tryIt": "Explain in one sentence what happens when a request hits GET /hello in your Spring app, from annotation to response.",
    },
    "annotation": {
        "explanation": (
            "An annotation (like @RestController) is metadata on a class or method. The framework "
            "reads it at startup and changes behaviour — e.g. registering the class as a controller "
            "— without you writing boilerplate."
        ),
        "analogy": "Like a sticky note on a box: 'fragile — handle as a controller'. The handler (Spring) reads the note.",
        "tryIt": "Name two Spring annotations you used and what each one caused Spring to do.",
    },
    "middleware": {
        "explanation": (
            "Middleware is a function that runs between receiving a request and sending a response "
            "— e.g. logging, auth, JSON parsing. In Express you register it with app.use(). "
            "It can inspect, modify, or short-circuit the request."
        ),
        "analogy": "Like airport security between check-in and the gate: every passenger passes through, some get stopped.",
        "tryIt": "Design (in words, no code) a middleware that logs the method + path of every request. Where would you register it?",
    },
    "dependency-injection": {
        "explanation": (
            "Dependency injection means a class receives its collaborators (e.g. a service) from the "
            "framework instead of creating them with `new`. Spring constructs and wires beans; "
            "your class just declares what it needs."
        ),
        "analogy": "Like a chef who is handed prepped ingredients instead of growing them. The kitchen (Spring) supplies them.",
        "tryIt": "In your controller, what would you inject if the greeting came from a service? Sketch the constructor in words.",
    },
    "closure": {
        "explanation": (
            "A closure is a function that remembers variables from the scope where it was created, "
            "even after that scope has finished. In JS, the handler (req, res) => { ... } closes over "
            "variables like `app` if it references them."
        ),
        "analogy": "Like a backpack: the function carries the variables it needs from home.",
        "tryIt": "Write (by hand) a tiny function that returns a counter function. Predict what each call returns before you run it.",
    },
    "async": {
        "explanation": (
            "Async code lets Node handle other requests while waiting for slow work (DB, network). "
            "async/await is syntax over Promises: await pauses that function until the Promise resolves, "
            "without blocking the whole server."
        ),
        "analogy": "Like ordering food: you get a buzzer (Promise) and sit down; the kitchen buzzes you when it is ready.",
        "tryIt": "Explain why blocking the event loop with a long sync loop would freeze ALL requests, not just yours.",
    },
}


def _explain_concept(concept: str, context: Optional[str] = None) -> dict:
    key = concept.lower().strip()
    hit = CONCEPTS.get(key)
    if hit is None:
        for k, v in CONCEPTS.items():
            if key in k or k in key:
                hit = v
                break
    if hit is not None:
        result = {
            "concept": concept,
            "explanation": hit["explanation"],
            "analogy": hit["analogy"],
            "tryItYourself": hit["tryIt"],
            "note": "Teachify explains — it does not write the code for you.",
        }
    else:
        result = {
            "concept": concept,
            "explanation": (
                f'I do not have a canned lesson for "{concept}" yet. Here is the teaching pattern: '
                "state the definition in one sentence, name the smallest example, then try it yourself. "
                f'Ask me to break "{concept}" into a 3-step task and I will build the steps (you still type the code).'
            ),
            "analogy": "Like learning to ride a bike: you need the balance idea + one small practice loop, not a lecture.",
            "tryItYourself": (
                f'In your own words, define "{concept}" in one sentence, then give one concrete '
                "example from code you have written."
            ),
            "note": "Teachify explains — it does not write the code for you.",
        }
    if context:
        result["context"] = context
    return result


_VALID_MODES = ("teach", "hint", "do")


def _validate_mode(mode: str) -> Optional[dict]:
    if mode not in _VALID_MODES:
        return {
            "error": f'Invalid mode "{mode}". Must be one of: teach, hint, do.',
            "hint": "Use teach (default, guide-only), hint (nudge-first), or do (boilerplate only on explicit request).",
        }
    return None


def _task_overview(task) -> dict:
    return {
        "id": task.id,
        "title": task.title,
        "description": task.description,
        "level": task.level,
        "estimatedMinutes": task.estimated_minutes,
        "totalSteps": len(task.steps),
        "learningOutcomes": task.learning_outcomes,
    }


@mcp.tool()
def teach_start_task(
    taskId: str,
    mode: str = "teach",
) -> str:
    """Start a guided learning task. Returns the task overview + step 1 only — never the full solution. The learner types every line.

    Args:
        taskId: Task id, e.g. js-express-hello or java-spring-hello.
        mode: teach = guide only, never types code. hint = nudge-first. do = only on explicit request, does boilerplate then quizzes you.
    """
    mode_err = _validate_mode(mode)
    if mode_err:
        return _text(mode_err)
    try:
        task = tasks.get_task(taskId)
    except Exception as exc:  # broken install -> clear message, not a traceback
        return _text({"error": str(exc), "hint": "Reinstall teachify and try again."})
    if task is None:
        return _text(
            {
                "error": f'Unknown taskId "{taskId}".',
                "availableTasks": tasks.list_task_summaries(),
            }
        )
    sess = session.create_session(taskId, mode)
    return _text(
        {
            "sessionId": sess.id,
            "mode": sess.mode,
            "task": _task_overview(task),
            "currentStep": session.to_public_step(task, 0),
            "rule": "The learner types every line. Teachify guides, verifies, hints, and quizzes — it never writes the solution.",
            "next": "Call teach_check_step with { sessionId, file, content } after the learner completes this step.",
        }
    )


@mcp.tool()
def teach_next_step(sessionId: str) -> str:
    """Return the current step. If the previous step is not yet verified, returns it again with a reminder — it never skips ahead or reveals the next solution.

    Args:
        sessionId: Session id from teach_start_task / teach_plan.
    """
    sess = session.get_session(sessionId)
    if sess is None:
        return _text({"error": f'Unknown sessionId "{sessionId}". Start with teach_start_task.', "hint": "Call teach_start_task or teach_plan first."})
    task = session.get_task_for_session(sess)
    if session.is_complete(sess):
        return _text(
            {
                "done": True,
                "message": "Task complete — every step verified. Call teach_quiz to check understanding, then teach_progress for a summary.",
                "stepsCompleted": len(sess.steps_completed),
                "totalSteps": len(task.steps),
            }
        )
    return _text(
        {
            "sessionId": sess.id,
            "currentStep": session.to_public_step(task, sess.current_step_index),
            "reminder": "Complete this step first, then call teach_check_step. Teachify will not advance on an unverified step.",
        }
    )


@mcp.tool()
def teach_check_step(
    sessionId: str,
    file: Optional[str] = None,
    content: Optional[str] = None,
) -> str:
    """Verify the learner's current step from file content or file path. Returns pass/fail + targeted feedback. On fail, never reveals the next solution.

    Args:
        sessionId: Session id from teach_start_task / teach_plan.
        file: Relative file path, e.g. server.js. If omitted, the step's file is used.
        content: File text to verify. If omitted, Teachify reads the file from disk.
    """
    sess = session.get_session(sessionId)
    if sess is None:
        return _text({"error": f'Unknown sessionId "{sessionId}". Start with teach_start_task.', "hint": "Call teach_start_task or teach_plan first."})
    task = session.get_task_for_session(sess)
    if session.is_complete(sess):
        return _text({"done": True, "message": "Task already complete. Call teach_quiz or teach_progress."})
    step = session.current_step(sess)
    session.record_attempt(sess, step.id)
    result = verify_step(step, content=content or "", file=file if file is not None else step.file)
    if not result.passed:
        if sess.attempts.get(step.id, 0) >= 3:
            sess.mastery_notes.append(
                f'Needed {sess.attempts[step.id]} attempts on "{step.title}" — revisit this concept.'
            )
        return _text(
            {
                "pass": False,
                "stepId": step.id,
                "stepTitle": step.title,
                "feedback": result.feedback,
                "attempts": sess.attempts.get(step.id, 0),
                "suggestion": "Stuck? Call teach_hint with level 1, then 2, then 3. Hints escalate but never type the code for you.",
            }
        )
    session.advance_session(sess)
    done = session.is_complete(sess)
    payload: dict = {
        "pass": True,
        "stepId": step.id,
        "stepTitle": step.title,
        "feedback": f'Nice — "{step.title}" verified. {"Task complete!" if done else "Moving to the next step."}',
        "progress": {"completed": len(sess.steps_completed), "total": len(task.steps)},
    }
    if done:
        payload["next"] = "Call teach_quiz to check understanding."
    else:
        payload["nextStepPreview"] = {
            "stepNumber": sess.current_step_index + 1,
            "title": task.steps[sess.current_step_index].title,
        }
        payload["note"] = "Full instructions for the next step come from teach_next_step — the preview above is title-only by design."
    return _text(payload)


@mcp.tool()
def teach_hint(sessionId: str, level: int = 1) -> str:
    """Escalating hints for the current step. Level 1 = nudge, 2 = shape of the code, 3 = strongest hint. Level 3 still does NOT type the code for the learner.

    Args:
        sessionId: Session id from teach_start_task / teach_plan.
        level: 1, 2, or 3.
    """
    if level not in (1, 2, 3):
        return _text({"error": f'Invalid level {level}. Must be 1, 2, or 3.', "hint": "Use level 1 for a nudge, 2 for the shape, 3 for the strongest hint."})
    sess = session.get_session(sessionId)
    if sess is None:
        return _text({"error": f'Unknown sessionId "{sessionId}".', "hint": "Call teach_start_task or teach_plan first."})
    task = session.get_task_for_session(sess)
    if session.is_complete(sess):
        return _text({"done": True, "message": "Task complete — no hints needed. Try teach_quiz."})
    step = session.current_step(sess)
    sess.hints_used += 1
    return _text(
        {
            "stepId": step.id,
            "stepTitle": step.title,
            "level": level,
            "hint": hints.get_hint(step, level),
            "rule": "Hints guide — you still type the code.",
        }
    )


@mcp.tool()
def teach_quiz(sessionId: str) -> str:
    """Return 2-3 questions about what the learner just did. Questions include options; answerIndex + explanation are for LLM grading ONLY — the LLM must ask the learner first and not reveal answers upfront.

    Args:
        sessionId: Session id from teach_start_task / teach_plan.
    """
    sess = session.get_session(sessionId)
    if sess is None:
        return _text({"error": f'Unknown sessionId "{sessionId}".', "hint": "Call teach_start_task or teach_plan first."})
    task = session.get_task_for_session(sess)
    return _text(
        {
            "sessionId": sess.id,
            "taskTitle": task.title,
            "progress": {"completed": len(sess.steps_completed), "total": len(task.steps)},
            "questions": [_quiz_payload(q) for q in task.quiz],
            "gradingInstruction": "Ask the learner each question WITHOUT showing answerIndex/explanation. Grade their answer, then share the explanation. If they miss one, point them back to the step that taught it.",
        }
    )


@mcp.tool()
def teach_explain(concept: str, context: Optional[str] = None) -> str:
    """Short explanation of a concept + analogy + a try-it-yourself prompt. Explains, never writes the learner's code.

    Args:
        concept: Concept to explain, e.g. REST, middleware, annotation, closure.
        context: Optional context, e.g. the task the learner is on.
    """
    return _text(_explain_concept(concept, context))


@mcp.tool()
def teach_progress(sessionId: str) -> str:
    """Progress summary for a session: steps done, time spent, attempts, hints, mastery notes.

    Args:
        sessionId: Session id from teach_start_task / teach_plan.
    """
    sess = session.get_session(sessionId)
    if sess is None:
        return _text({"error": f'Unknown sessionId "{sessionId}".', "hint": "Call teach_start_task or teach_plan first."})
    task = session.get_task_for_session(sess)
    done = session.is_complete(sess)
    elapsed_min = round((time.time() - sess.started_at) / 60)
    return _text(
        {
            "sessionId": sess.id,
            "task": {"id": task.id, "title": task.title},
            "mode": sess.mode,
            "progress": {
                "completed": len(sess.steps_completed),
                "total": len(task.steps),
                "stepsCompleted": sess.steps_completed,
                "currentStep": None if done else task.steps[sess.current_step_index].title,
                "done": done,
            },
            "effort": {
                "elapsedMinutes": elapsed_min,
                "attempts": sess.attempts,
                "hintsUsed": sess.hints_used,
            },
            "masteryNotes": sess.mastery_notes if sess.mastery_notes else ["No struggle spots recorded yet — keep going."],
            "next": "Done. Call teach_quiz to lock in understanding, then start a new task."
            if done
            else "Call teach_next_step to continue.",
        }
    )


@mcp.tool()
def teach_mode_on() -> str:
    """Turn on Teach Mode. Returns the Teach Mode system prompt + rules. After this, take the user's prompt as-is, break it into 3-7 steps, and call teach_plan — never write the user's code."""
    return _text(
        {
            "mode": "teach",
            "systemPrompt": teach_mode.get_teach_mode_prompt(),
            "rules": teach_mode.TEACH_MODE_RULES,
            "howToUse": teach_mode.TEACH_MODE_HOW_TO_USE,
            "examplePrompt": teach_mode.TEACH_MODE_EXAMPLE_PROMPT,
            "next": "Break the user's prompt into 3-7 verifiable steps and call teach_plan with {prompt, steps, quiz}. Guide one step at a time after that.",
        }
    )


def _handle_teach_plan(
    prompt: Optional[str],
    steps: Optional[list],
    quiz: Optional[list],
    title: Optional[str],
    mode: str,
) -> str:
    payload = {"prompt": prompt, "steps": steps, "quiz": quiz, "title": title}
    errors = plan.validate_teach_plan(payload)
    if errors:
        return _text(
            {
                "error": "Teach plan rejected — fix the errors and call teach_plan again. No session was created.",
                "errors": errors,
                "hint": "Steps must be 3-7, one action / one file / one concept each, each with non-empty title, instruction, why, file, hintL1, hintL2, hintL3, and a valid check. Quiz, if present, must be 2-3 questions.",
            }
        )
    task = plan.build_dynamic_task(payload)
    tasks.register_dynamic_task(task)
    sess = session.create_session_for_task(task, mode)
    return _text(
        {
            "sessionId": sess.id,
            "taskId": task.id,
            "mode": sess.mode,
            "prompt": (prompt or "").strip(),
            "task": _task_overview(task),
            "currentStep": session.to_public_step(task, 0),
            "rule": "The learner types every line. Teachify guides, verifies, hints, and quizzes — it never writes the solution. Step 1 only is returned here.",
            "next": "Call teach_check_step with { sessionId, file, content } after the learner completes this step.",
        }
    )


@mcp.tool()
def teach_plan(
    prompt: str,
    steps: list,
    quiz: Optional[list] = None,
    title: Optional[str] = None,
    mode: str = "teach",
) -> str:
    """Plan a Teach Mode session from ANY user prompt. Validates 3-7 steps (each with instruction, why, file, hints, check) and 2-3 quiz questions. On valid, creates a session and returns step 1 only — never the full solution. On invalid, returns clear errors and creates nothing.

    Args:
        prompt: The user's original prompt, as-is — e.g. 'Implement JWT auth'.
        steps: 3-7 steps, one action / one file / one concept each, each with title, instruction, why, file, hints, check.
        quiz: Optional 2-3 quiz questions. If omitted, Teachify supplies a default 2-question quiz.
        title: Optional short title for the plan.
        mode: teach (default), hint, or do.
    """
    mode_err = _validate_mode(mode)
    if mode_err:
        return _text(mode_err)
    return _handle_teach_plan(prompt, steps, quiz, title, mode)


@mcp.tool()
def teach_start_from_prompt(
    prompt: str,
    steps: list,
    quiz: Optional[list] = None,
    title: Optional[str] = None,
    mode: str = "teach",
) -> str:
    """Alias of teach_plan for discoverability. Same schema, same behaviour: plan a Teach Mode session from ANY user prompt.

    Args:
        prompt: The user's original prompt, as-is — e.g. 'Implement JWT auth'.
        steps: 3-7 steps, one action / one file / one concept each, each with title, instruction, why, file, hints, check.
        quiz: Optional 2-3 quiz questions. If omitted, Teachify supplies a default 2-question quiz.
        title: Optional short title for the plan.
        mode: teach (default), hint, or do.
    """
    mode_err = _validate_mode(mode)
    if mode_err:
        return _text(mode_err)
    return _handle_teach_plan(prompt, steps, quiz, title, mode)


@mcp.tool()
def teach_list_tasks() -> str:
    """List available learning tasks (id, title, level, steps)."""
    try:
        return _text({"tasks": tasks.list_task_summaries()})
    except Exception as exc:
        return _text({"error": str(exc), "hint": "Reinstall teachify and try again."})
