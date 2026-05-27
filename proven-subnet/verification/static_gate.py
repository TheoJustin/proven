"""Static Gate — Stage 1 of the validator's verification funnel.

Screens a miner-submitted Playwright test script and returns a structured
pass/fail verdict. Pure stdlib; no bittensor/torch/playwright imports.
"""

from __future__ import annotations

import ast
import shutil
import subprocess
from dataclasses import dataclass


@dataclass(frozen=True)
class GateResult:
    passed: bool
    reasons: tuple[str, ...] = ()


_ALLOWED_ROOTS: frozenset[str] = frozenset(
    {"os", "playwright", "pytest", "re", "typing"}
)

_BANNED_CALLS: frozenset[str] = frozenset(
    {
        "__import__",
        "compile",
        "eval",
        "exec",
        "globals",
        "input",
        "locals",
        "open",
        "vars",
    }
)

_BANNED_CALL_PREFIXES: tuple[str, ...] = (
    "os.remove",
    "os.rename",
    "os.replace",
    "os.rmdir",
    "os.system",
    "os.unlink",
    "os.walk",
    "shutil.",
    "socket.",
    "subprocess.",
    "time.sleep",
)


def analyze(script: str, *, ruff_executable: str | None = None) -> GateResult:
    """Return a GateResult describing whether *script* passes the static gate."""
    try:
        tree = ast.parse(script)
    except SyntaxError as exc:
        return GateResult(False, (f"syntax error: {exc}",))

    reasons: list[str] = []
    has_playwright = False

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                root = alias.name.split(".")[0]
                if root not in _ALLOWED_ROOTS:
                    reasons.append(f"disallowed import: {root}")
                if root == "playwright":
                    has_playwright = True

        elif isinstance(node, ast.ImportFrom):
            root = (node.module or "").split(".")[0]
            if root not in _ALLOWED_ROOTS:
                reasons.append(f"disallowed import: {root}")
            if root == "playwright":
                has_playwright = True

        elif isinstance(node, ast.Assert):
            if isinstance(node.test, ast.Constant):
                reasons.append("happy-path: assert on constant")
            elif (
                isinstance(node.test, ast.Compare)
                and isinstance(node.test.left, ast.Constant)
                and all(
                    isinstance(c, ast.Constant) for c in node.test.comparators
                )
            ):
                reasons.append("happy-path: assert on constant comparison")

        elif isinstance(node, ast.Call):
            name = _dotted_name(node.func)
            if name in _BANNED_CALLS:
                reasons.append(f"disallowed call: {name}")
            elif any(
                name == prefix.rstrip(".") or name.startswith(prefix)
                for prefix in _BANNED_CALL_PREFIXES
            ):
                reasons.append(f"disallowed call: {name}")
            elif (
                isinstance(node.func, ast.Name)
                and node.func.id == "expect"
                and node.args
                and isinstance(node.args[0], ast.Constant)
            ):
                reasons.append("happy-path: expect() on constant")

    if not has_playwright:
        reasons.append("must import playwright")

    # --- ruff E9,F lint (correctness only, no style) ---
    ruff = (
        ruff_executable
        if ruff_executable is not None
        else shutil.which("ruff")
    )
    if ruff:
        try:
            proc = subprocess.run(
                [
                    ruff,
                    "check",
                    "--select",
                    "E9,F",
                    "--output-format",
                    "concise",
                    "--stdin-filename",
                    "submission.py",
                    "-",
                ],
                input=script,
                capture_output=True,
                text=True,
                timeout=10,
            )
        except (FileNotFoundError, OSError, subprocess.TimeoutExpired):
            proc = None
        if proc is not None and proc.returncode != 0 and proc.stdout.strip():
            for line in proc.stdout.splitlines():
                line = line.strip()
                if (
                    line
                    and not line.startswith("Found")
                    and not line.startswith("[")
                ):
                    reasons.append(f"lint: {line}")

    passed = len(reasons) == 0
    return GateResult(passed, tuple(reasons))


def _dotted_name(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        parent = _dotted_name(node.value)
        return f"{parent}.{node.attr}" if parent else node.attr
    return ""
