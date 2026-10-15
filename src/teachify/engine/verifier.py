"""Step verifier. NEVER returns the solution — only pass/fail + targeted feedback."""

from __future__ import annotations

import os
import re

from .types import StepCheck, TaskStep, VerifyResult

_FLAG_MAP = {"m": re.MULTILINE, "s": re.DOTALL, "i": re.IGNORECASE}

_SKIP_DIRS = {"node_modules", ".git", "dist", ".venv", "__pycache__", "build"}


def _flags(flag_str: str | None) -> int:
    flags = 0
    for ch in (flag_str or "m"):
        flags |= _FLAG_MAP.get(ch, 0)
    return flags


def find_by_basename(directory: str, basename: str, depth: int) -> str | None:
    if depth < 0:
        return None
    try:
        entries = list(os.scandir(directory))
    except OSError:
        return None
    for entry in entries:
        if entry.name in _SKIP_DIRS:
            continue
        full = entry.path
        if entry.is_file(follow_symlinks=False) and entry.name == basename:
            return full
        if entry.is_dir(follow_symlinks=False):
            hit = find_by_basename(full, basename, depth - 1)
            if hit:
                return hit
    return None


def _abs(file_path: str) -> str:
    return file_path if os.path.isabs(file_path) else os.path.join(os.getcwd(), file_path)


def check_one(check: StepCheck, content: str, file_path: str | None = None) -> VerifyResult:
    kind = check.kind
    if kind == "fileExists":
        if not file_path:
            return VerifyResult(
                passed=False,
                feedback=(
                    "I could not verify this step because no file was provided. "
                    "Create the file, then run teach_check_step again with the file path."
                ),
                failed_check="fileExists (no file given)",
            )
        if os.path.exists(_abs(file_path)):
            return VerifyResult(passed=True, feedback=f"Found {file_path}.")
        found = find_by_basename(os.getcwd(), os.path.basename(file_path), 3)
        if found:
            return VerifyResult(passed=True, feedback=f"Found {found}.")
        return VerifyResult(
            passed=False,
            feedback=f'I could not find "{file_path}" yet. Create it first, then check again.',
            failed_check="fileExists",
        )
    if kind == "regex":
        if not check.pattern:
            return VerifyResult(
                passed=False,
                feedback="Task definition error: regex check has no pattern.",
                failed_check="regex",
            )
        try:
            compiled = re.compile(check.pattern, _flags(check.flags))
        except re.error:
            return VerifyResult(
                passed=False,
                feedback=f"Task definition error: invalid regex {check.pattern}.",
                failed_check="regex",
            )
        if compiled.search(content):
            return VerifyResult(passed=True, feedback="Pattern matched.")
        return VerifyResult(
            passed=False,
            feedback=(
                "That pattern is not in your file yet. Re-read the step's what-to-type "
                "guidance and check spelling, quotes, and parentheses."
            ),
            failed_check=f"regex {check.pattern}",
        )
    if kind == "contains":
        if not check.value:
            return VerifyResult(
                passed=False,
                feedback="Task definition error: contains check has no value.",
                failed_check="contains",
            )
        if check.value in content:
            return VerifyResult(passed=True, feedback=f'Found "{check.value}".')
        return VerifyResult(
            passed=False,
            feedback=f'Your file does not contain "{check.value}" yet. Add it, then check again.',
            failed_check=f"contains {check.value}",
        )
    if kind == "all":
        if not check.checks:
            return VerifyResult(
                passed=False,
                feedback="Task definition error: all check has no sub-checks.",
                failed_check="all",
            )
        for sub in check.checks:
            result = check_one(sub, content, file_path)
            if not result.passed:
                return result
        return VerifyResult(passed=True, feedback="All checks passed.")
    return VerifyResult(
        passed=False,
        feedback=f"Unknown check kind {kind}.",
        failed_check="unknown",
    )


def _read_from_disk(file_path: str) -> str:
    abs_path = _abs(file_path)
    if os.path.exists(abs_path):
        try:
            with open(abs_path, encoding="utf-8") as fh:
                return fh.read()
        except OSError:
            return ""
    found = find_by_basename(os.getcwd(), os.path.basename(file_path), 3)
    if found:
        try:
            with open(found, encoding="utf-8") as fh:
                return fh.read()
        except OSError:
            return ""
    return ""


def verify_step(step: TaskStep, content: str = "", file: str | None = None) -> VerifyResult:
    """Verify a step. `content` may be passed directly; otherwise the file is
    read from disk. NEVER returns the solution — only pass/fail + feedback."""
    file_path = file if file is not None else step.file
    if not content and file_path:
        content = _read_from_disk(file_path)

    # fileExists checks don't need content; other checks do.
    if step.check.kind == "fileExists":
        return check_one(step.check, content, file_path)
    if not content:
        return VerifyResult(
            passed=False,
            feedback=(
                f'I have no file content to check for "{step.title}". Pass the file text as "content" '
                f'or make sure "{file_path}" exists on disk, then try again.'
            ),
            failed_check="no-content",
        )
    result = check_one(step.check, content, file_path)
    if not result.passed:
        return VerifyResult(
            passed=False,
            feedback=f"{result.feedback} (Check: {step.check_description})",
            failed_check=result.failed_check,
        )
    return result
