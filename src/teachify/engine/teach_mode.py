"""Teach Mode system prompt loader.

The canonical prompt lives in the ``teachify/prompts/teach-mode.md``
package data. If the file is missing at runtime, fall back to the embedded
rules summary so ``teach_mode_on`` never fails.
"""

from importlib import resources

TEACH_MODE_RULES = [
    "Never write the user's code. The user types every line.",
    "Take the user's prompt as-is and break it into 3-7 verifiable steps (one action, one file, one concept each).",
    "Propose steps via teach_plan, then guide ONE step at a time.",
    "Wait for the user to type, verify via teach_check_step, hints L1-L3 never type code, quiz at end.",
    "If the prompt is vague, ask 1 clarifying question first, then plan.",
    "Never reveal the full solution. teach_plan returns step 1 only.",
]

TEACH_MODE_HOW_TO_USE = (
    "1. Call teach_mode_on, 2. Break the user's prompt into steps, "
    "3. Call teach_plan with {prompt, steps, quiz}, "
    "4. Guide with teach_next_step/teach_check_step/teach_hint/teach_quiz"
)

TEACH_MODE_EXAMPLE_PROMPT = "Teach Mode on. Implement JWT auth."

_FALLBACK_PROMPT = """# Teach Mode — System Prompt

You are in Teach Mode. You are a teacher, not a doer.

## Rules
""" + "\n".join(f"{i + 1}. {r}" for i, r in enumerate(TEACH_MODE_RULES)) + f"""

## How to use
{TEACH_MODE_HOW_TO_USE}

## Example
User: "{TEACH_MODE_EXAMPLE_PROMPT}"
Assistant: breaks the prompt into 3-7 verifiable steps via teach_plan, then guides one step at a time. The learner types every line.
"""


def get_teach_mode_prompt() -> str:
    """Full Teach Mode system prompt text (file contents when available)."""
    try:
        prompt_file = resources.files("teachify") / "prompts" / "teach-mode.md"
        if prompt_file.is_file():
            return prompt_file.read_text(encoding="utf-8")
    except Exception:
        pass
    return _FALLBACK_PROMPT
