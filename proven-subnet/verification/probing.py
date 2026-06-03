"""DOM probing heuristics for selector-manifest-aware validation."""

from __future__ import annotations

import ast
from typing import Any


_PROBING_CALL_NAMES = frozenset(
    {
        "query_selector",
        "query_selector_all",
        "eval_on_selector",
        "eval_on_selector_all",
    }
)

_JS_DOM_PROBES = (
    "querySelector(",
    "querySelectorAll(",
    "getElementById(",
    "getElementsByClassName(",
    "getElementsByName(",
    "getElementsByTagName(",
    "document.body",
    "document.documentElement",
)

_BROAD_SELECTORS = frozenset({"*", "html", "body", ":scope"})


def has_selector_manifest(selector_manifest: Any = None) -> bool:
    """Return True when the validator supplied any selector manifest content."""

    if selector_manifest is None:
        return False
    if isinstance(selector_manifest, dict):
        return any(selector_manifest.values())
    if isinstance(selector_manifest, (list, tuple, set)):
        return len(selector_manifest) > 0
    return bool(selector_manifest)


def crawls_dom_despite_manifest(
    script: str, selector_manifest: Any = None
) -> bool:
    """Detect scripts that probe/crawl the DOM after receiving selectors.

    The red flag is only active when a manifest is present. With selectors in
    hand, miners should use targeted Playwright locators instead of broad DOM
    discovery APIs or JavaScript DOM scans.
    """

    if not has_selector_manifest(selector_manifest) or not script:
        return False

    try:
        tree = ast.parse(script)
    except SyntaxError:
        return False

    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            name = _dotted_name(node.func)
            attr = name.rsplit(".", 1)[-1]
            if attr in _PROBING_CALL_NAMES:
                return True
            if attr == "evaluate" and _call_contains_dom_probe(node):
                return True
            if (
                attr == "locator"
                and node.args
                and _is_broad_selector(node.args[0])
            ):
                return True
            if attr in {"all", "count"} and _looks_like_locator_chain(name):
                return True

        if isinstance(node, ast.For) and _iterates_locator_collection(
            node.iter
        ):
            return True
        if isinstance(node, (ast.ListComp, ast.SetComp, ast.GeneratorExp)):
            if any(
                _iterates_locator_collection(gen.iter)
                for gen in node.generators
            ):
                return True

    return False


def _call_contains_dom_probe(node: ast.Call) -> bool:
    return any(
        isinstance(arg, ast.Constant)
        and isinstance(arg.value, str)
        and any(probe in arg.value for probe in _JS_DOM_PROBES)
        for arg in node.args
    )


def _is_broad_selector(node: ast.AST) -> bool:
    return (
        isinstance(node, ast.Constant)
        and isinstance(node.value, str)
        and node.value.strip() in _BROAD_SELECTORS
    )


def _iterates_locator_collection(node: ast.AST) -> bool:
    if isinstance(node, ast.Call):
        name = _dotted_name(node.func)
        return name.endswith(".all") or name.endswith(".query_selector_all")
    return False


def _looks_like_locator_chain(name: str) -> bool:
    return ".locator" in name or name.startswith("locator")


def _dotted_name(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        parent = _dotted_name(node.value)
        return f"{parent}.{node.attr}" if parent else node.attr
    if isinstance(node, ast.Call):
        return _dotted_name(node.func)
    return ""
