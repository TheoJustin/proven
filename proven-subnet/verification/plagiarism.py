"""AST fingerprint and within-epoch duplicate detection — NUL-9."""

import ast
import hashlib
import json
from collections import defaultdict
from pathlib import Path


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


class FirstSubmitterRegistry:
    """Persistent cross-epoch registry: fingerprint → first submitter."""

    def __init__(self, max_entries: int = 100_000) -> None:
        self._max = max_entries
        self._entries: dict[str, dict] = {}

    def register(self, submitter: str, script: str, timestamp: float) -> bool:
        fp = fingerprint(script)
        if fp not in self._entries:
            self._entries[fp] = {"submitter": submitter, "timestamp": timestamp}
            self._evict()
            return False
        return self._entries[fp]["submitter"] != submitter

    def first_submitter(self, script: str) -> str | None:
        """Return the first submitter of *script*, or None if unseen.

        Returns None (does not raise) for unparseable input.
        """
        try:
            fp = fingerprint(script)
        except ValueError:
            return None
        entry = self._entries.get(fp)
        return entry["submitter"] if entry else None

    def _evict(self) -> None:
        if len(self._entries) > self._max:
            oldest = sorted(self._entries.items(), key=lambda kv: kv[1]["timestamp"])
            for fp, _ in oldest[: len(self._entries) - self._max]:
                del self._entries[fp]

    def to_dict(self) -> dict:
        return {fp: dict(data) for fp, data in self._entries.items()}

    @classmethod
    def from_dict(cls, data: dict, max_entries: int = 100_000) -> "FirstSubmitterRegistry":
        reg = cls(max_entries=max_entries)
        reg._entries = {fp: dict(v) for fp, v in data.items()}
        return reg

    def save(self, path) -> None:
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        Path(path).write_text(json.dumps(self.to_dict()), encoding="utf-8")

    @classmethod
    def load(cls, path, max_entries: int = 100_000) -> "FirstSubmitterRegistry":
        p = Path(path)
        if not p.exists():
            return cls(max_entries=max_entries)
        return cls.from_dict(json.loads(p.read_text(encoding="utf-8")), max_entries=max_entries)
