"""Tests for verification.plagiarism — NUL-9."""

import textwrap

from verification.plagiarism import fingerprint, duplicate_submitters

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

_SCRIPT_A = textwrap.dedent(
    """
    from playwright.sync_api import Page

    def test_login(page: Page):
        page.goto("https://example.com/login")
        page.fill("#username", "alice")
        page.fill("#password", "secret")
        page.click("button[type='submit']")
        assert page.url == "https://example.com/dashboard"
    """
).strip()

# Same logic as _SCRIPT_A but with added blank lines and comments.
_SCRIPT_A_REFORMATTED = textwrap.dedent(
    """
    # Login test for example.com
    from playwright.sync_api import Page


    def test_login(page: Page):
        # navigate to login page
        page.goto("https://example.com/login")

        page.fill("#username", "alice")
        page.fill("#password", "secret")
        page.click("button[type='submit']")
        assert page.url == "https://example.com/dashboard"
    """
).strip()

# Same as _SCRIPT_A but with a variable renamed: page -> p.
_SCRIPT_A_RENAMED = textwrap.dedent(
    """
    from playwright.sync_api import Page

    def test_login(p: Page):
        p.goto("https://example.com/login")
        p.fill("#username", "alice")
        p.fill("#password", "secret")
        p.click("button[type='submit']")
        assert p.url == "https://example.com/dashboard"
    """
).strip()

# Same as _SCRIPT_A but with a different literal.
_SCRIPT_A_DIFF_LITERAL = textwrap.dedent(
    """
    from playwright.sync_api import Page

    def test_login(page: Page):
        page.goto("https://example.com/login")
        page.fill("#username", "bob")
        page.fill("#password", "secret")
        page.click("button[type='submit']")
        assert page.url == "https://example.com/dashboard"
    """
).strip()

# A structurally different script testing the same feature.
_SCRIPT_B = textwrap.dedent(
    """
    from playwright.sync_api import Page, expect

    def test_login_flow(page: Page):
        page.goto("https://example.com/signin")
        page.locator("input[name='user']").fill("alice")
        page.locator("input[name='pass']").fill("secret")
        page.locator("form").evaluate("f => f.submit()")
        expect(page).to_have_url("https://example.com/home")
    """
).strip()

_BAD_SCRIPT = "def f(:"


# ---------------------------------------------------------------------------
# fingerprint() — Behavior 1: reformatting-insensitive
# ---------------------------------------------------------------------------

def test_fingerprint_same_for_reformatted_script():
    """Blank lines and comments do not change the fingerprint."""
    assert fingerprint(_SCRIPT_A) == fingerprint(_SCRIPT_A_REFORMATTED)


# ---------------------------------------------------------------------------
# fingerprint() — Behavior 2: identifier-sensitive (strict policy)
# ---------------------------------------------------------------------------

def test_fingerprint_differs_for_renamed_identifier():
    """Renaming a variable produces a different fingerprint (strict policy)."""
    assert fingerprint(_SCRIPT_A) != fingerprint(_SCRIPT_A_RENAMED)


# ---------------------------------------------------------------------------
# fingerprint() — Behavior 3: literal-sensitive
# ---------------------------------------------------------------------------

def test_fingerprint_differs_for_changed_literal():
    """Changing a string literal produces a different fingerprint."""
    assert fingerprint(_SCRIPT_A) != fingerprint(_SCRIPT_A_DIFF_LITERAL)


# ---------------------------------------------------------------------------
# fingerprint() — Behavior 4: SyntaxError raises ValueError
# ---------------------------------------------------------------------------

def test_fingerprint_raises_value_error_on_syntax_error():
    """Unparseable script raises ValueError."""
    import pytest
    with pytest.raises(ValueError):
        fingerprint(_BAD_SCRIPT)


# ---------------------------------------------------------------------------
# duplicate_submitters() — Behavior 5: basic case
# ---------------------------------------------------------------------------

def test_duplicate_submitters_basic_case():
    """Alice and Bob submit the same script; Carol submits differently.
    Alice (lex-smallest) keeps credit; Bob is the duplicate."""
    submissions = [
        ("alice", _SCRIPT_A),
        ("bob", _SCRIPT_A),
        ("carol", _SCRIPT_B),
    ]
    assert duplicate_submitters(submissions) == {"bob"}


# ---------------------------------------------------------------------------
# duplicate_submitters() — Behavior 6: deterministic regardless of order
# ---------------------------------------------------------------------------

def test_duplicate_submitters_deterministic_regardless_of_order():
    """Shuffling input does not change which ids are flagged as duplicates."""
    submissions_ordered = [
        ("alice", _SCRIPT_A),
        ("bob", _SCRIPT_A),
        ("carol", _SCRIPT_B),
    ]
    submissions_reversed = [
        ("carol", _SCRIPT_B),
        ("bob", _SCRIPT_A),
        ("alice", _SCRIPT_A),
    ]
    assert (
        duplicate_submitters(submissions_ordered)
        == duplicate_submitters(submissions_reversed)
        == {"bob"}
    )


# ---------------------------------------------------------------------------
# duplicate_submitters() — Behavior 7: empty set when all distinct
# ---------------------------------------------------------------------------

def test_duplicate_submitters_empty_when_all_distinct():
    """No duplicates when every submission has a unique fingerprint."""
    submissions = [
        ("alice", _SCRIPT_A),
        ("bob", _SCRIPT_B),
    ]
    assert duplicate_submitters(submissions) == set()


# ---------------------------------------------------------------------------
# duplicate_submitters() — Behavior 8: honest convergence not flagged
# ---------------------------------------------------------------------------

def test_duplicate_submitters_honest_convergence_not_flagged():
    """Two structurally different scripts for the same feature are NOT flagged."""
    submissions = [
        ("miner1", _SCRIPT_A),
        ("miner2", _SCRIPT_B),
    ]
    assert duplicate_submitters(submissions) == set()


# ---------------------------------------------------------------------------
# duplicate_submitters() — Behavior 9: unparseable script is skipped
# ---------------------------------------------------------------------------

def test_duplicate_submitters_skips_unparseable_script():
    """A script that doesn't parse is silently skipped (not deduped, no exception)."""
    submissions = [
        ("miner1", _SCRIPT_A),
        ("bad_miner", _BAD_SCRIPT),
    ]
    # bad_miner's script can't be parsed → skipped; miner1 is unique → empty
    assert duplicate_submitters(submissions) == set()
