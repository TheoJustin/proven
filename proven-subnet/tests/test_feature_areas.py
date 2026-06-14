"""Tests for verification.feature_areas — catalogue integrity vs the fixture."""

import pathlib

from verification.feature_areas import (
    WILLIFY_HOMEPAGE,
    get_feature_area,
    load_reference_files,
)
from verification.mutation import blunt_killer, generate_mutants

_REFERENCE_ROOT = (
    pathlib.Path(__file__).resolve().parents[1] / "docker" / "reference"
)


def _ref_files():
    return load_reference_files(WILLIFY_HOMEPAGE, _REFERENCE_ROOT)


def test_get_feature_area_roundtrip():
    assert get_feature_area("willify_homepage") is WILLIFY_HOMEPAGE


def test_manifest_is_well_formed():
    manifest = WILLIFY_HOMEPAGE.manifest()
    assert manifest["feature_area"] == "willify_homepage"
    names = {e["name"] for e in manifest["elements"]}
    assert {
        "read_more_button",
        "homepage_heading",
        "register_link",
    } <= names
    for element in manifest["elements"]:
        assert element["selector"]
        assert "role" in element
        assert "accessible_name" in element


def test_oracle_suite_exists():
    assert pathlib.Path(WILLIFY_HOMEPAGE.oracle_suite).is_file()


def test_every_operator_anchor_is_unique_in_reference():
    content = _ref_files()[WILLIFY_HOMEPAGE.reference_relpath]
    for op in WILLIFY_HOMEPAGE.operators:
        assert content.count(op.find) == 1, op.name


def test_every_operator_produces_a_distinct_mutant():
    files = _ref_files()
    reference = files[WILLIFY_HOMEPAGE.reference_relpath]
    n = len(WILLIFY_HOMEPAGE.operators)
    mutants = generate_mutants(files, WILLIFY_HOMEPAGE.operators, seed=0, n=n)
    assert len(mutants) == n
    seen = set()
    for m in mutants:
        mutated = m.files[WILLIFY_HOMEPAGE.reference_relpath]
        assert mutated != reference
        seen.add(mutated)
    assert len(seen) == n  # every mutant is distinct


def test_blunt_killer_blanks_manifest_elements():
    files = _ref_files()
    bk = blunt_killer(files, WILLIFY_HOMEPAGE.blunt_operators)
    mutated = bk.files[WILLIFY_HOMEPAGE.reference_relpath]
    assert '<button id="read-more-button"' not in mutated
    assert "Where Music Meets Comfort" not in mutated
    assert 'id="sign-up">Register</a>' not in mutated
