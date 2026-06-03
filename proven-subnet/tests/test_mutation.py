"""Mutation engine, oracle admission, and blunt killer tests."""

from verification.mutation import (
    admit,
    blunt_killer_mutant,
    generate_mutants,
)
from verification.selector_manifest import build_selector_manifest

_REFERENCE = {
    "index.html": """
    <html>
      <body>
        <section data-feature-area="homepage">
          <h1 id="hero-heading">Willify Music</h1>
          <a id="sign-up" href="register.html">Sign Up</a>
          <button id="read-more-button">Read More</button>
        </section>
      </body>
    </html>
    """,
    "app.js": "if (ready === true) { window.loaded = true; }",
}


def _homepage_oracle(tree: dict[str, str]) -> bool:
    html = "\n".join(tree.values()).lower()
    return "willify music" in html and "read more" in html and "register.html" in html


def test_generate_mutants_is_seed_reproducible_and_changes_source():
    first = generate_mutants(_REFERENCE, "homepage", seed="epoch-1", n=4)
    second = generate_mutants(_REFERENCE, "homepage", seed="epoch-1", n=4)

    assert [m.mutant_id for m in first] == [m.mutant_id for m in second]
    assert len(first) == 4
    assert all(m.files != _REFERENCE for m in first)
    assert {m.feature_area for m in first} == {"homepage"}


def test_oracle_admission_keeps_only_killable_mutants():
    candidates = generate_mutants(_REFERENCE, "homepage", seed="epoch-2", n=8)
    admitted = admit(candidates, _homepage_oracle, _REFERENCE)

    assert admitted
    assert all(_homepage_oracle(mutant.files) is False for mutant in admitted)


def test_oracle_admission_drops_everything_when_reference_fails():
    candidates = generate_mutants(_REFERENCE, "homepage", seed="epoch-2", n=3)

    assert admit(candidates, lambda tree: False, _REFERENCE) == []


def test_blunt_killer_blanks_feature_area():
    mutant = blunt_killer_mutant(_REFERENCE, "homepage")
    html = mutant.files["index.html"]

    assert mutant.operator == "blunt_killer"
    assert "data-blanked" in html
    assert "Read More" not in html
    assert "Sign Up" not in html


def test_selector_manifest_builds_feature_scoped_entries_and_can_disable():
    html = _REFERENCE["index.html"]
    manifest = build_selector_manifest(html, "homepage")

    assert manifest["feature_area"] == "homepage"
    assert manifest["selectors"]["read_more_button"] == "#read-more-button"
    assert manifest["selectors"]["sign_up"] == "#sign-up"
    assert build_selector_manifest(html, "homepage", enabled=False) == {
        "feature_area": "homepage",
        "selectors": {},
        "entries": [],
    }
