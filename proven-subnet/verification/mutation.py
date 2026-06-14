"""Mutation Engine — dynamic, seeded fault injection for the Reference app.

Pure and stdlib-only: operates on in-memory source (relpath -> text) and a list
of declarative :class:`Operator` transforms supplied by the Feature Area
catalogue (``verification/feature_areas.py``). Seeding makes the per-epoch mutant
set reproducible, so every miner in an epoch faces the *identical* set and
``K_i / N_mut`` is comparable across miners.

Each :class:`Operator` is an exact ``find`` -> ``replace`` substring rewrite on a
known anchor in a target file. This is reliable because the validator owns the
fixture and knows its exact markup; it also keeps the engine trivially testable
against fixture HTML (operators produce observable diffs; equivalent edits are
caught later by the Oracle admission filter in ``verification/oracle.py``).
"""

from __future__ import annotations

import random
from dataclasses import dataclass


@dataclass(frozen=True)
class Operator:
    """A single declarative mutation: rewrite ``find`` to ``replace`` once.

    ``kind`` is a human-facing label (e.g. ``"rename_attr"``, ``"swap_text"``,
    ``"remove_element"``); it is cosmetic and does not affect application.
    """

    name: str
    kind: str
    target_file: str
    find: str
    replace: str
    description: str = ""

    def applies_to(self, files) -> bool:
        return self.find in files.get(self.target_file, "")


@dataclass
class Mutant:
    """A generated app variant: only the files that differ from the reference."""

    name: str
    operator: str
    description: str
    files: dict  # relpath -> mutated content (changed files only)


def apply_operators(reference_files, operators):
    """Return a full file map with every applicable *operator* applied in order.

    Operators whose ``find`` anchor is absent are skipped (no-op), so a stale
    operator never raises — it simply contributes nothing.
    """
    files = dict(reference_files)
    for op in operators:
        content = files.get(op.target_file)
        if content is not None and op.find in content:
            files[op.target_file] = content.replace(op.find, op.replace, 1)
    return files


def _changed_only(reference_files, mutated_files):
    return {
        relpath: content
        for relpath, content in mutated_files.items()
        if content != reference_files.get(relpath)
    }


def generate_mutants(reference_files, operators, seed, n):
    """Return up to *n* single-operator mutants, deterministic for *seed*.

    Only operators whose anchor is present in *reference_files* are eligible.
    The eligible set is shuffled with ``random.Random(seed)`` and the first *n*
    are materialised, so the same seed yields the same set and order while
    different seeds (likely) differ. If fewer than *n* operators apply, every
    eligible operator is returned.
    """
    eligible = [op for op in operators if op.applies_to(reference_files)]
    rng = random.Random(seed)
    rng.shuffle(eligible)
    selected = eligible[: max(0, n)]

    mutants = []
    for op in selected:
        mutated = apply_operators(reference_files, [op])
        changed = _changed_only(reference_files, mutated)
        if not changed:
            continue
        mutants.append(
            Mutant(
                name=op.name,
                operator=op.kind,
                description=op.description,
                files=changed,
            )
        )
    return mutants


def blunt_killer(reference_files, blank_operators, name="blunt_killer"):
    """Build the Tautology Trap mutant: the feature area blanked out.

    *blank_operators* remove/empty every element a genuine test of the feature
    area would assert on. A real test fails against this mutant; a happy-path
    "ghost" that asserts nothing real still passes — which the funnel treats as
    ``P_clean = 0``.
    """
    mutated = apply_operators(reference_files, blank_operators)
    changed = _changed_only(reference_files, mutated)
    return Mutant(
        name=name,
        operator="blunt_killer",
        description="Feature area content blanked (Tautology Trap).",
        files=changed,
    )
