"""Golden Oracle Suite — Willify About Us feature area.

Run by the Oracle admission filter against the reference (must PASS) and each
candidate mutant (must FAIL). Each assertion pairs with a mutation operator in
``verification/feature_areas.py``.
"""

import os

from playwright.sync_api import Page, expect

TARGET_URL = os.environ.get("TARGET_URL", "http://localhost:8080")


def test_willify_about_oracle(page: Page):
    page.goto(f"{TARGET_URL}/src/html/about-us.html")

    expect(page).to_have_title("Willify | About Us")
    expect(page.locator(".hero-section h1")).to_have_text("Who We Are?")
    expect(page.locator(".hero-section h3")).to_have_text(
        "Get to Know Willify"
    )
    expect(page.locator("#read-more-button")).to_be_visible()

    section = page.locator("#read-more-section")
    expect(section).to_have_count(1)
    expect(section.locator(".biography-left h1")).to_have_text(
        "What is Willify?"
    )

    expect(page.locator("#uvp-one h1")).to_have_text("Seamless")
    expect(page.locator("#uvp-one")).to_have_count(1)
    expect(page.locator("#history-one h1")).to_have_text("2006")
    expect(page.locator("#history-one")).to_have_count(1)
