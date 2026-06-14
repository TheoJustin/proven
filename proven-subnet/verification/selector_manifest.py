"""Selector Manifest builder (ADR-0003).

The validator broadcasts a behaviour-first Selector Manifest so miners test
behaviour instead of mining selectors (DOM crawling then becomes a pure red flag
penalised via E_i). The manifest's source of truth is the Feature Area catalogue;
when enabled, a live crawl of the Reference app enriches each element with the
role / accessible name / attributes / state actually observed in the DOM.

The crawl is feature-flagged so it can be disabled for a future private-audit
mode (no proprietary DOM is broadcast). ``run_crawl`` is injected so this module
stays unit-testable; the real Playwright crawl (:func:`playwright_crawl`) imports
Playwright lazily, keeping the module import-safe in CI.
"""

from __future__ import annotations

_ENRICHABLE_KEYS = ("role", "accessible_name", "attributes", "state")


def build_manifest(area, reference_url, *, crawl=True, run_crawl=None):
    """Return the Selector Manifest for *area*.

    When ``crawl`` is disabled the manifest is empty (private-audit mode,
    ADR-0003): no DOM is read and no selectors are broadcast. When enabled, each
    catalogue element is enriched with the crawler's observed values; if no
    crawler is supplied or the crawl raises, the static catalogue manifest is
    used as a safe fallback.
    """
    if not crawl:
        return {"feature_area": area.name, "elements": []}

    base = area.manifest()
    if run_crawl is None:
        return base

    try:
        observed = run_crawl(area, reference_url) or {}
    except Exception:
        return base

    elements = []
    for element in base["elements"]:
        seen = observed.get(element["name"])
        if not seen:
            elements.append(element)
            continue
        merged = dict(element)
        for key in _ENRICHABLE_KEYS:
            if seen.get(key):
                merged[key] = seen[key]
        elements.append(merged)
    return {"feature_area": base["feature_area"], "elements": elements}


def playwright_crawl(area, reference_url):
    """Observe each manifest selector on the live Reference app.

    Returns ``{element_name: {role, accessible_name, attributes, state}}``.
    Imports Playwright lazily so importing this module never pulls Playwright.
    """
    from playwright.sync_api import sync_playwright

    observed = {}
    url = f"{reference_url}{area.target_path}"
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        try:
            page = browser.new_page()
            page.goto(url)
            for entry in area.selectors:
                locator = page.locator(entry.selector)
                if locator.count() == 0:
                    continue
                first = locator.first
                attributes = {}
                for key in entry.attributes or {}:
                    value = first.get_attribute(key)
                    if value is not None:
                        attributes[key] = value
                observed[entry.name] = {
                    "role": first.get_attribute("role") or entry.role,
                    "accessible_name": (
                        (first.text_content() or "").strip()
                        or entry.accessible_name
                    ),
                    "attributes": attributes,
                    "state": {"visible": first.is_visible()},
                }
        finally:
            browser.close()
    return observed
