"""Teachify core types. Keep these stable — they are the contract
between task JSON files, the verifier, the MCP tools, and clients.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal, Optional

# "teach" = guide only, never types code.
# "hint" = nudge-first.
# "do" = only on explicit request, does boilerplate then quizzes you.
TeachMode = Literal["teach", "hint", "do"]

CheckKind = Literal["fileExists", "regex", "contains", "all"]


@dataclass
class StepCheck:
    kind: str  # one of fileExists | regex | contains | all
    pattern: Optional[str] = None  # regex source (no surrounding slashes); flags default to "m"
    value: Optional[str] = None  # contains: literal substring that must be present
    checks: Optional[list] = None  # all: every sub-check must pass (list of StepCheck)
    flags: Optional[str] = None  # regex flags, e.g. "ms"


@dataclass
class QuizQuestion:
    question: str
    options: list[str] = field(default_factory=list)
    # Index into options — for LLM grading only. The LLM must NOT reveal this upfront.
    answer_index: int = 0
    explanation: str = ""


@dataclass
class TaskStep:
    id: str = ""
    title: str = ""
    instruction: str = ""  # what the learner should DO (not the code itself)
    why: str = ""  # why this step matters — the mental model, in 1-2 sentences
    file: str = ""  # relative file the learner should edit, e.g. "server.js"
    file_hint: str = ""  # where in the file, in human words
    what_to_type: str = ""  # guidance on what to type, without pasting the full solution
    check: StepCheck = field(default_factory=lambda: StepCheck(kind="fileExists"))
    check_description: str = ""
    hint_l1: str = ""
    hint_l2: str = ""
    hint_l3: str = ""  # most specific hint — still never types the code


@dataclass
class TeachTask:
    id: str = ""
    title: str = ""
    description: str = ""
    level: str = "beginner"  # beginner | intermediate | advanced
    estimated_minutes: int = 15
    learning_outcomes: list[str] = field(default_factory=list)
    steps: list[TaskStep] = field(default_factory=list)
    quiz: list[QuizQuestion] = field(default_factory=list)


@dataclass
class Session:
    id: str = ""
    task_id: str = ""
    mode: str = "teach"
    started_at: float = 0.0
    current_step_index: int = 0
    steps_completed: list[str] = field(default_factory=list)
    attempts: dict[str, int] = field(default_factory=dict)
    hints_used: int = 0
    mastery_notes: list[str] = field(default_factory=list)
    completed_at: Optional[float] = None


@dataclass
class VerifyResult:
    passed: bool
    feedback: str
    failed_check: Optional[str] = None
