"""Selector Manifest generation and probing red-flag tests — NUL-18."""

import importlib.util
import pathlib
import sys
import textwrap

import pytest

_GENERATOR_PATH = (
    pathlib.Path(__file__).resolve().parents[1]
    / "template"
    / "ai"
    / "playwright_generator.py"
)
_SPEC = importlib.util.spec_from_file_location(
    "playwright_generator", _GENERATOR_PATH
)
playwright_generator = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = playwright_generator
assert _SPEC.loader is not None
_SPEC.loader.exec_module(playwright_generator)

_user_prompt = playwright_generator._user_prompt
build_fallback_script = playwright_generator.build_fallback_script
validate_playwright_script = playwright_generator.validate_playwright_script
from verification.efficiency import efficiency  # noqa: E402
from verification.probing import crawls_dom_despite_manifest  # noqa: E402
from verification.feature_areas import WILLIFY_HOMEPAGE  # noqa: E402
from verification.selector_manifest import build_manifest  # noqa: E402


_SELECTOR_MANIFEST = {
    "selectors": {
        "read_more_button": "[data-testid='read-more']",
        "homepage_heading": "[data-testid='hero-heading']",
        "register_link": "[data-testid='register-link']",
    }
}


def test_fallback_uses_selector_manifest_without_dom_probing():
    script = build_fallback_script(
        "http://validator.example",
        selector_manifest=_SELECTOR_MANIFEST,
    )

    assert "page.locator(\"[data-testid='read-more']\")" in script
    assert "page.locator(\"[data-testid='hero-heading']\")" in script
    assert "page.locator(\"[data-testid='register-link']\")" in script
    assert "#read-more-button" not in script
    assert "#sign-up" not in script
    assert "query_selector" not in script
    assert "evaluate(" not in script
    validate_playwright_script(script)


def test_generator_prompt_includes_manifest_and_forbids_selector_discovery():
    prompt = _user_prompt(
        spec_type="user_story",
        requirement_content="Check Willify homepage core controls.",
        target_url="http://localhost:8080",
        selector_manifest=_SELECTOR_MANIFEST,
    )

    assert "Selector Manifest:" in prompt
    assert "read_more_button: [data-testid='read-more']" in prompt
    assert "homepage_heading: [data-testid='hero-heading']" in prompt
    assert "register_link: [data-testid='register-link']" in prompt
    assert "use the provided selectors exactly" in prompt
    assert "Do not discover selectors by crawling the" in prompt


@pytest.mark.parametrize(
    "script",
    [
        """
        import os
        from playwright.sync_api import Page, expect
        def test_x(page: Page):
            page.query_selector_all("button")
        """,
        """
        import os
        from playwright.sync_api import Page, expect
        def test_x(page: Page):
            page.evaluate("() => document.querySelectorAll('button').length")
        """,
        """
        import os
        from playwright.sync_api import Page, expect
        def test_x(page: Page):
            for item in page.locator("button").all():
                expect(item).to_be_visible()
        """,
    ],
)
def test_probing_heuristic_flags_dom_crawls_when_manifest_present(script):
    assert crawls_dom_despite_manifest(
        textwrap.dedent(script), _SELECTOR_MANIFEST
    )


def test_probing_heuristic_allows_direct_manifest_locators():
    script = build_fallback_script(
        "http://localhost:8080",
        selector_manifest=_SELECTOR_MANIFEST,
    )

    assert not crawls_dom_despite_manifest(script, _SELECTOR_MANIFEST)


def test_probing_red_flag_feeds_e_i_penalty_only_with_manifest():
    script = textwrap.dedent(
        """
        import os
        from playwright.sync_api import Page, expect
        def test_x(page: Page):
            buttons = page.query_selector_all("button")
            assert buttons is not None
        """
    )

    probing = crawls_dom_despite_manifest(script, _SELECTOR_MANIFEST)
    assert probing is True
    assert efficiency(0.0, 5.0, 60.0, probing=probing) == pytest.approx(0.1)
    assert crawls_dom_despite_manifest(script, None) is False


# ---------------------------------------------------------------------------
# build_manifest — static catalogue manifest + optional crawl enrichment
# ---------------------------------------------------------------------------


def _fake_crawl(observed):
    return lambda area, url: observed


def test_build_manifest_empty_when_crawl_disabled():
    # Private-audit mode (ADR-0003): no DOM read, no selectors broadcast.
    manifest = build_manifest(WILLIFY_HOMEPAGE, "http://ref", crawl=False)
    assert manifest["feature_area"] == "willify_homepage"
    assert manifest["elements"] == []


def test_build_manifest_enriches_from_crawl():
    observed = {
        "read_more_button": {
            "accessible_name": "Read More Now",
            "state": {"visible": True},
        }
    }
    manifest = build_manifest(
        WILLIFY_HOMEPAGE,
        "http://ref",
        crawl=True,
        run_crawl=_fake_crawl(observed),
    )
    button = next(
        e for e in manifest["elements"] if e["name"] == "read_more_button"
    )
    assert button["accessible_name"] == "Read More Now"
    # Untouched elements keep their catalogue values.
    heading = next(
        e for e in manifest["elements"] if e["name"] == "homepage_heading"
    )
    assert heading["accessible_name"] == "Where Music Meets Comfort"


def test_build_manifest_falls_back_when_crawl_raises():
    def boom(area, url):
        raise RuntimeError("crawl failed")

    manifest = build_manifest(
        WILLIFY_HOMEPAGE, "http://ref", crawl=True, run_crawl=boom
    )
    assert manifest == WILLIFY_HOMEPAGE.manifest()


def test_fallback_consumes_structured_catalogue_manifest():
    manifest = WILLIFY_HOMEPAGE.manifest()
    script = build_fallback_script("http://ref", selector_manifest=manifest)

    assert "page.locator('#read-more-button')" in script
    assert "page.locator('h3')" in script
    assert "page.locator('#sign-up')" in script
    validate_playwright_script(script)
