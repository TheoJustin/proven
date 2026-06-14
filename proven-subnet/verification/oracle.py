"""Oracle admission filter — admit only genuinely killable mutants.

The Golden Oracle Suite is the validator's private, exhaustive ground-truth test
for a feature area. A candidate mutant is *admitted* only if the oracle passes on
the clean reference (sanity) and fails on the candidate (the fault is observably
killable). Equivalent mutants — where the oracle still passes — are dropped so
``N_mut`` and the achievable kill ceiling stay honest and comparable across
miners.

``run_oracle`` is injected (``run_oracle(url) -> bool``, True iff the suite
passes against the app at *url*) so this stays pure and unit-testable; the
validator supplies a real implementation that runs the suite via pytest.
"""

from __future__ import annotations


def admit(candidates, run_oracle, reference_url):
    """Filter ``(mutant, url)`` *candidates* to the oracle-killable subset.

    Returns the admitted ``(mutant, url)`` pairs, preserving input order. Raises
    ``RuntimeError`` if the oracle does not pass on *reference_url*, since no
    admission decision can be trusted in that state.
    """
    if not run_oracle(reference_url):
        raise RuntimeError(
            "Golden Oracle Suite failed on the reference app; "
            "cannot admit mutants."
        )

    admitted = []
    for mutant, url in candidates:
        if not run_oracle(url):  # oracle killed by the mutant -> admit
            admitted.append((mutant, url))
    return admitted
