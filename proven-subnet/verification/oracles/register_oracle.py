"""Golden Oracle Suite — Willify register feature area.

Run by the Oracle admission filter against the reference (must PASS) and each
candidate mutant (must FAIL). Each assertion pairs with a mutation operator in
``verification/feature_areas.py``.
"""

import os

from playwright.sync_api import Page, expect

TARGET_URL = os.environ.get("TARGET_URL", "http://localhost:8080")


def test_willify_register_oracle(page: Page):
    page.goto(f"{TARGET_URL}/src/html/register.html")

    expect(page).to_have_title("Willify | Register")

    form = page.locator("#register-form")
    expect(form).to_have_count(1)
    expect(form.locator("h1")).to_have_text("Register Here!")

    expect(page.locator("#TxtName")).to_have_count(1)
    expect(page.locator("#TxtEmail")).to_have_count(1)
    expect(page.locator("#TxtPassword")).to_have_attribute("type", "password")
    expect(page.locator("#TxtAge")).to_have_attribute("type", "number")

    submit = page.locator("#submit-button")
    expect(submit).to_have_count(1)
    expect(submit).to_have_text("Submit")

    expect(page.locator("#male")).to_have_count(1)
