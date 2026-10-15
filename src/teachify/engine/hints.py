"""Escalating hint ladder. Level 3 is the most specific hint — it still
never types the code for the learner. The engine never returns a full
solution from any hint level.
"""

from .types import TaskStep


def get_hint(step: TaskStep, level: int) -> str:
    if level == 2:
        return step.hint_l2
    if level == 3:
        return step.hint_l3
    return step.hint_l1


def hint_for_level_label(level: int) -> str:
    if level <= 1:
        return "nudge — direction, not the answer"
    if level == 2:
        return "focused hint — the shape of the code"
    return "strong hint — almost there, you still type it"
