"""Tests for verification.feature_areas — catalogue integrity vs the fixture."""

import pathlib
import random

import pytest

from verification.feature_areas import (
    FEATURE_AREAS,
    WILLIFY_HOMEPAGE,
    get_feature_area,
    load_reference_files,
    select_feature_area,
)
from verification.mutation import blunt_killer, generate_mutants

_REFERENCE_ROOT = (
    pathlib.Path(__file__).resolve().parents[1] / "docker" / "reference"
)

_AREAS = list(FEATURE_AREAS.values())
_IDS = [a.name for a in _AREAS]


def _ref_files(area):
    return load_reference_files(area, _REFERENCE_ROOT)


def test_catalogue_has_expected_areas():
    assert {
        "willify_homepage",
        "willify_register",
        "willify_songs",
        "willify_about",
    } <= set(FEATURE_AREAS)


def test_get_feature_area_roundtrip():
    assert get_feature_area("willify_homepage") is WILLIFY_HOMEPAGE


@pytest.mark.parametrize("area", _AREAS, ids=_IDS)
def test_manifest_is_well_formed(area):
    manifest = area.manifest()
    assert manifest["feature_area"] == area.name
    assert manifest["elements"]
    for element in manifest["elements"]:
        assert element["selector"]
        assert "role" in element
        assert "accessible_name" in element


@pytest.mark.parametrize("area", _AREAS, ids=_IDS)
def test_oracle_suite_exists(area):
    assert pathlib.Path(area.oracle_suite).is_file()


@pytest.mark.parametrize("area", _AREAS, ids=_IDS)
def test_every_operator_anchor_is_unique_in_reference(area):
    content = _ref_files(area)[area.reference_relpath]
    for op in area.operators:
        assert content.count(op.find) == 1, f"{area.name}:{op.name}"


@pytest.mark.parametrize("area", _AREAS, ids=_IDS)
def test_every_operator_produces_a_distinct_mutant(area):
    files = _ref_files(area)
    reference = files[area.reference_relpath]
    n = len(area.operators)
    mutants = generate_mutants(files, area.operators, seed=0, n=n)
    assert len(mutants) == n
    seen = set()
    for m in mutants:
        mutated = m.files[area.reference_relpath]
        assert mutated != reference
        seen.add(mutated)
    assert len(seen) == n


@pytest.mark.parametrize("area", _AREAS, ids=_IDS)
def test_blunt_operators_apply_and_change_reference(area):
    files = _ref_files(area)
    content = files[area.reference_relpath]
    for op in area.blunt_operators:
        assert op.find in content, f"{area.name}:{op.name}"
    bk = blunt_killer(files, area.blunt_operators)
    assert bk.files[area.reference_relpath] != content


def test_blunt_killer_blanks_homepage_manifest_elements():
    files = _ref_files(WILLIFY_HOMEPAGE)
    bk = blunt_killer(files, WILLIFY_HOMEPAGE.blunt_operators)
    mutated = bk.files[WILLIFY_HOMEPAGE.reference_relpath]
    assert '<button id="read-more-button"' not in mutated
    assert "Where Music Meets Comfort" not in mutated
    assert 'id="sign-up">Register</a>' not in mutated


def test_select_feature_area_pins_and_rotates():
    assert select_feature_area("willify_songs").name == "willify_songs"
    assert select_feature_area("rotate") in _AREAS
    assert select_feature_area(None) in _AREAS


def test_select_feature_area_unknown_raises():
    with pytest.raises(KeyError):
        select_feature_area("does_not_exist")


def test_select_feature_area_is_seed_reproducible():
    # Same seed -> same area (reproducible); seeds vary -> selection varies.
    a = select_feature_area("rotate", rng=random.Random(7))
    b = select_feature_area("rotate", rng=random.Random(7))
    assert a is b
    picks = {
        select_feature_area("rotate", rng=random.Random(s)).name
        for s in range(20)
    }
    assert len(picks) > 1
