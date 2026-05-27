"""Static Gate — Stage 1 of the validator's verification funnel.

Screens a miner-submitted Playwright test script and returns a structured
pass/fail verdict. Pure stdlib; no bittensor/torch/playwright imports.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass


@dataclass(frozen=True)
class GateResult:
    passed: bool
    reasons: tuple[str, ...] = ()


_ALLOWED_ROOTS: frozenset[str] = frozenset({"os", "playwright", "pytest", "re", "typing"})

_BANNED_CALLS: frozenset[str] = frozenset(
    {"__import__", "compile", "eval", "exec", "globals", "input", "locals", "open", "vars"}
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


def analyze(script: str) -> GateResult:
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

        elif isinstance(node, ast.Call):
            name = _dotted_name(node.func)
            if name in _BANNED_CALLS:
                reasons.append(f"disallowed call: {name}")
            elif any(
                name == prefix.rstrip(".") or name.startswith(prefix)
                for prefix in _BANNED_CALL_PREFIXES
            ):
                reasons.append(f"disallowed call: {name}")

    if not has_playwright:
        reasons.append("must import playwright")

    passed = len(reasons) == 0
    return GateResult(passed, tuple(reasons))


def _dotted_name(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        parent = _dotted_name(node.value)
        return f"{parent}.{node.attr}" if parent else node.attr
    return ""
