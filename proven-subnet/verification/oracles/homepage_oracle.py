"""Golden Oracle Suite — Willify homepage feature area.

Validator-private, exhaustive ground-truth test. Run by the Oracle admission
filter (``verification/oracle.py``) against the reference app (must PASS) and
each candidate mutant (must FAIL to be admitted). Every assertion here is paired
with a mutation operator in ``verification/feature_areas.py`` so no admitted
mutant is equivalent.

Not auto-collected by the unit test run (it lives outside ``tests/`` and has no
``test_*.py`` filename); it is executed explicitly via pytest-playwright.
"""

import os

from playwright.sync_api import Page, expect

TARGET_URL = os.environ.get("TARGET_URL", "http://localhost:8080")


def test_willify_homepage_oracle(page: Page):
    page.goto(f"{TARGET_URL}/src/html/index.html")

    # Document + hero copy.
    expect(page).to_have_title("Willify | Home")
    expect(page.locator(".hero-section h1")).to_have_text("Willify")
    expect(page.locator("h3")).to_have_text("Where Music Meets Comfort")

    # Read More button — a visible hero control.
    read_more = page.locator("#read-more-button")
    expect(read_more).to_be_visible()
    expect(read_more).to_have_text("Read More")

    # Structural anchors that drive on-page behaviour.
    expect(page.locator("#read-more-section")).to_have_count(1)
    expect(page.locator("#read-more-section .heading-one")).to_have_text(
        "Why Choose Willify?"
    )
    expect(page.locator("#mobile-menu")).to_have_count(1)
    expect(page.locator("#home-page")).to_have_count(1)

    # Register link — text and destination.
    register = page.locator("#sign-up")
    expect(register).to_have_count(1)
    expect(register).to_have_text("Register")
    expect(register).to_have_attribute("href", "register.html")
