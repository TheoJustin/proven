"""Seeded mutation engine and oracle admission for the validator funnel.

The functions in this module are deliberately pure: they mutate source text or
in-memory file maps and return materialisable mutants without importing
Playwright, Docker, bittensor, or the Willify app at import time.
"""

from __future__ import annotations

import hashlib
import random
import re
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass


SourceTree = Mapping[str, str]
OracleRunner = Callable[[Mapping[str, str]], bool]


@dataclass(frozen=True)
class Mutant:
    """A generated, materialisable mutation of the reference source tree."""

    mutant_id: str
    feature_area: str
    operator: str
    files: dict[str, str]
    description: str


def normalize_source_tree(reference_source: str | SourceTree) -> dict[str, str]:
    """Return a path->text source tree for either a single string or mapping."""

    if isinstance(reference_source, str):
        return {"index.html": reference_source}
    return {str(path): str(contents) for path, contents in reference_source.items()}


def generate_mutants(
    reference_source: str | SourceTree,
    feature_area: str,
    seed: int | str,
    n: int,
) -> list[Mutant]:
    """Generate up to *n* deterministic mutants for *feature_area*.

    The operator library intentionally targets observable UI behavior instead
    of implementation internals: text changes, attribute removal/renaming,
    href rewrites, feature-scoped element removal, and small JavaScript logic
    flips.  The same reference, feature area, seed, and n produce the same
    ordered mutant set, allowing a validator to precompute one private epoch
    horde and score every miner against it.
    """

    if n <= 0:
        return []

    rng = random.Random(str(seed))
    reference_tree = normalize_source_tree(reference_source)
    candidates: list[Mutant] = []

    operators = [
        _mutate_text,
        _remove_attribute,
        _rename_attribute,
        _rewrite_href,
        _remove_feature_element,
        _flip_js_logic,
    ]
    attempts = 0
    max_attempts = max(n * len(operators) * 8, 24)
    seen: set[str] = set()

    while len(candidates) < n and attempts < max_attempts:
        attempts += 1
        operator = rng.choice(operators)
        result = operator(reference_tree, feature_area, rng)
        if result is None:
            continue
        op_name, files, description = result
        digest = _tree_digest(files)
        if digest == _tree_digest(reference_tree) or digest in seen:
            continue
        seen.add(digest)
        candidates.append(
            Mutant(
                mutant_id=_mutant_id(feature_area, seed, len(candidates), digest),
                feature_area=feature_area,
                operator=op_name,
                files=dict(files),
                description=description,
            )
        )

    return candidates


def blunt_killer_mutant(
    reference_source: str | SourceTree,
    feature_area: str,
) -> Mutant:
    """Return a mutant with the feature area's DOM content blanked."""

    reference_tree = normalize_source_tree(reference_source)
    files = dict(reference_tree)
    changed = False
    for path, contents in reference_tree.items():
        if _looks_like_html(path):
            blanked = _blank_feature_area(contents, feature_area)
            if blanked != contents:
                files[path] = blanked
                changed = True
    if not changed:
        # Fall back to a deterministic, obviously broken document body for
        # fixtures that do not carry feature-area markers yet.
        for path, contents in reference_tree.items():
            if _looks_like_html(path):
                files[path] = re.sub(
                    r"<body\b[^>]*>.*?</body>",
                    '<body data-blunt-killer="true"></body>',
                    contents,
                    flags=re.IGNORECASE | re.DOTALL,
                )
                changed = True
                break
    digest = _tree_digest(files)
    return Mutant(
        mutant_id=_mutant_id(feature_area, "blunt", 0, digest),
        feature_area=feature_area,
        operator="blunt_killer",
        files=files,
        description=f"Blanked feature area {feature_area!r}",
    )


def admit(
    candidates: Sequence[Mutant],
    oracle_suite: OracleRunner,
    reference: str | SourceTree,
) -> list[Mutant]:
    """Keep only mutants killed by the golden oracle suite.

    ``oracle_suite`` returns True when its assertions pass against a source
    tree and False when they fail.  Admission first verifies that the oracle
    passes on the reference; if not, no mutants are safe to score against.
    A candidate is admitted only when the oracle fails against that mutant,
    filtering equivalent/unkillable mutants out of ``N_mut``.
    """

    reference_tree = normalize_source_tree(reference)
    if not oracle_suite(reference_tree):
        return []
    admitted: list[Mutant] = []
    for mutant in candidates:
        if not oracle_suite(mutant.files):
            admitted.append(mutant)
    return admitted


def _mutate_text(tree: SourceTree, feature_area: str, rng: random.Random):
    path, html = _pick_html(tree, rng)
    if path is None:
        return None
    scoped = _feature_patterns(feature_area)
    text_match = None
    for match in re.finditer(r">([^<>]{3,120})<", html):
        if any(
            p.search(html[max(0, match.start() - 300) : match.end() + 300])
            for p in scoped
        ):
            text_match = match
            break
    if text_match is None:
        text_match = next(re.finditer(r">([^<>]{3,120})<", html), None)
    if text_match is None:
        return None
    replacement = f">{text_match.group(1).strip()} BROKEN<"
    return _replace(path, tree, html, text_match.span(), replacement, "text_swap")


def _remove_attribute(tree: SourceTree, feature_area: str, rng: random.Random):
    path, html = _pick_html(tree, rng)
    if path is None:
        return None
    match = re.search(r"\s(?:id|class|aria-label|role|data-testid)=([\"']).*?\1", html)
    if match is None:
        return None
    return _replace(path, tree, html, match.span(), "", "attribute_remove")


def _rename_attribute(tree: SourceTree, feature_area: str, rng: random.Random):
    path, html = _pick_html(tree, rng)
    if path is None:
        return None
    match = re.search(r"\s(id|data-testid)=([\"'])(.*?)\2", html)
    if match is None:
        return None
    quote = match.group(2)
    replacement = f" {match.group(1)}={quote}{match.group(3)}-mutated{quote}"
    return _replace(path, tree, html, match.span(), replacement, "attribute_rename")


def _rewrite_href(tree: SourceTree, feature_area: str, rng: random.Random):
    path, html = _pick_html(tree, rng)
    if path is None:
        return None
    match = re.search(r"\s(href|src)=([\"'])(?!#|javascript:)(.*?)\2", html)
    if match is None:
        return None
    replacement = f" {match.group(1)}={match.group(2)}#mutated{match.group(2)}"
    return _replace(path, tree, html, match.span(), replacement, "href_rewrite")


def _remove_feature_element(tree: SourceTree, feature_area: str, rng: random.Random):
    path, html = _pick_html(tree, rng)
    if path is None:
        return None
    blanked = _blank_feature_area(html, feature_area)
    if blanked == html:
        match = re.search(
            r"<button\b[^>]*>.*?</button>|<a\b[^>]*>.*?</a>", html, re.I | re.S
        )
        if match is None:
            return None
        return _replace(path, tree, html, match.span(), "", "element_remove")
    files = dict(tree)
    files[path] = blanked
    return "element_remove", files, f"Removed feature-area element in {path}"


def _flip_js_logic(tree: SourceTree, feature_area: str, rng: random.Random):
    js_files = [(p, c) for p, c in tree.items() if p.endswith(".js")]
    if not js_files:
        return None
    path, contents = rng.choice(js_files)
    replacements = [
        ("===", "!=="),
        ("!==", "==="),
        ("true", "false"),
        ("false", "true"),
    ]
    for old, new in replacements:
        match = re.search(re.escape(old), contents)
        if match:
            return _replace(path, tree, contents, match.span(), new, "js_logic_flip")
    return None


def _replace(
    path: str, tree: SourceTree, contents: str, span, replacement: str, op_name: str
):
    files = dict(tree)
    files[path] = contents[: span[0]] + replacement + contents[span[1] :]
    return op_name, files, f"Applied {op_name} in {path}"


def _pick_html(tree: SourceTree, rng: random.Random) -> tuple[str | None, str]:
    html_files = [(p, c) for p, c in tree.items() if _looks_like_html(p)]
    if not html_files:
        return None, ""
    return rng.choice(html_files)


def _looks_like_html(path: str) -> bool:
    return path.endswith((".html", ".htm"))


def _feature_patterns(feature_area: str) -> list[re.Pattern[str]]:
    escaped = re.escape(feature_area)
    slug = re.escape(feature_area.replace("_", "-").replace(" ", "-"))
    return [
        re.compile(rf"data-feature-area=([\"'])({escaped}|{slug})\1", re.I),
        re.compile(rf"(?:id|class)=([\"'])[^\"']*({escaped}|{slug})[^\"']*\1", re.I),
    ]


def _blank_feature_area(html: str, feature_area: str) -> str:
    patterns = _feature_patterns(feature_area)
    for pattern in patterns:
        match = pattern.search(html)
        if not match:
            continue
        tag_start = html.rfind("<", 0, match.start())
        if tag_start < 0:
            continue
        tag_match = re.match(r"<([a-zA-Z][\w:-]*)\b", html[tag_start:])
        if tag_match is None:
            continue
        tag = tag_match.group(1)
        close = re.search(rf"</{re.escape(tag)}\s*>", html[match.end() :], re.I)
        if close is None:
            element_end = html.find(">", match.end()) + 1
        else:
            element_end = match.end() + close.end()
        return (
            html[:tag_start]
            + f'<div data-feature-area="{feature_area}" data-blanked="true"></div>'
            + html[element_end:]
        )
    return html


def _tree_digest(tree: SourceTree) -> str:
    h = hashlib.sha256()
    for path in sorted(tree):
        h.update(path.encode())
        h.update(b"\0")
        h.update(tree[path].encode())
        h.update(b"\0")
    return h.hexdigest()


def _mutant_id(feature_area: str, seed: int | str, index: int, digest: str) -> str:
    raw = f"{feature_area}:{seed}:{index}:{digest}".encode()
    return hashlib.sha256(raw).hexdigest()[:16]
