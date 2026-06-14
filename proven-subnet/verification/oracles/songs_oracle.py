"""Golden Oracle Suite — Willify songs feature area.

Run by the Oracle admission filter against the reference (must PASS) and each
candidate mutant (must FAIL). Each assertion pairs with a mutation operator in
``verification/feature_areas.py``.
"""

import os

from playwright.sync_api import Page, expect

TARGET_URL = os.environ.get("TARGET_URL", "http://localhost:8080")


def test_willify_songs_oracle(page: Page):
    page.goto(f"{TARGET_URL}/src/html/songs.html")

    expect(page).to_have_title("Willify | Songs")
    expect(page.locator(".hero-section h1")).to_have_text("Songs to Play")
    expect(page.locator(".hero-section h3")).to_have_text(
        "Top Recommended Songs for You!"
    )
    expect(page.locator("#read-more-button")).to_be_visible()
    expect(page.locator("#read-more-section")).to_have_count(1)
    expect(page.locator("#rnb-text")).to_have_count(1)
    expect(page.locator("#pop-text")).to_have_count(1)
    expect(page.locator("#kpop-text")).to_have_count(1)
    expect(page.get_by_text("Tip Toe", exact=True)).to_have_count(1)
