"""AST fingerprint and within-epoch duplicate detection — NUL-9."""

import ast
import hashlib
from collections import defaultdict


def fingerprint(script: str) -> str:
    """Return a hex digest of the canonical AST dump of *script*.

    Insensitive to whitespace/comments; sensitive to identifiers, literals,
    and structure (strict policy).  Raises ValueError if *script* has a
    syntax error.
    """
    try:
        tree = ast.parse(script)
    except SyntaxError as exc:
        raise ValueError(f"script does not parse: {exc}") from exc
    return hashlib.sha256(ast.dump(tree).encode()).hexdigest()


def duplicate_submitters(submissions) -> set[str]:
    """Return the set of submitter ids that are exact-copy duplicates.

    *submissions* is an iterable of (submitter_id, script) pairs.  Within
    each group sharing a fingerprint, the lexicographically smallest id keeps
    credit; every other id in the group is a duplicate and is returned.
    Scripts that do not parse are skipped silently.
    """
    groups: dict[str, list[str]] = defaultdict(list)
    for submitter_id, script in submissions:
        try:
            fp = fingerprint(script)
        except ValueError:
            continue
        groups[fp].append(submitter_id)

    duplicates: set[str] = set()
    for ids in groups.values():
        if len(ids) > 1:
            keeper = min(ids)
            duplicates.update(sid for sid in ids if sid != keeper)
    return duplicates
