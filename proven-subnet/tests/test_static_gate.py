"""Tests for verification.static_gate — NUL-2 + NUL-5."""

import pathlib
import sys
import textwrap

from verification.static_gate import analyze

# Deterministic ruff path: same venv as this test runner.
RUFF = str(pathlib.Path(sys.executable).with_name("ruff"))

# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

_CLEAN_SCRIPT = textwrap.dedent(
    """
    import os
    from playwright.sync_api import Page, expect

    TARGET_URL = os.environ.get("TARGET_URL", "http://localhost:8080")

    def test_homepage(page: Page):
        page.goto(TARGET_URL)
        heading = page.locator("h1")
        expect(heading).to_be_visible()
    """
).strip()


# ---------------------------------------------------------------------------
# cycle 1: clean script passes
# ---------------------------------------------------------------------------

def test_clean_script_passes():
    result = analyze(_CLEAN_SCRIPT)
    assert result.passed is True
    assert result.reasons == ()


# ---------------------------------------------------------------------------
# cycle 2: banned import — subprocess
# ---------------------------------------------------------------------------

def test_banned_import_subprocess():
    script = textwrap.dedent(
        """
        import subprocess
        from playwright.sync_api import Page, expect

        def test_x(page: Page):
            expect(page.locator("h1")).to_be_visible()
        """
    ).strip()
    result = analyze(script)
    assert result.passed is False
    assert any("subprocess" in r for r in result.reasons)


# ---------------------------------------------------------------------------
# cycle 3: banned import — from socket import socket
# ---------------------------------------------------------------------------

def test_banned_import_socket():
    script = textwrap.dedent(
        """
        from socket import socket
        from playwright.sync_api import Page, expect

        def test_x(page: Page):
            expect(page.locator("h1")).to_be_visible()
        """
    ).strip()
    result = analyze(script)
    assert result.passed is False
    assert any("socket" in r for r in result.reasons)


# ---------------------------------------------------------------------------
# cycle 4: banned call — eval
# ---------------------------------------------------------------------------

def test_banned_call_eval():
    script = textwrap.dedent(
        """
        from playwright.sync_api import Page, expect

        def test_x(page: Page):
            eval("1")
            expect(page.locator("h1")).to_be_visible()
        """
    ).strip()
    result = analyze(script)
    assert result.passed is False
    assert any("eval" in r for r in result.reasons)


# ---------------------------------------------------------------------------
# cycle 5: banned dotted call — os.system
# ---------------------------------------------------------------------------

def test_banned_call_os_system():
    script = textwrap.dedent(
        """
        import os
        from playwright.sync_api import Page, expect

        def test_x(page: Page):
            os.system("ls")
            expect(page.locator("h1")).to_be_visible()
        """
    ).strip()
    result = analyze(script)
    assert result.passed is False
    assert any("os.system" in r for r in result.reasons)


# ---------------------------------------------------------------------------
# cycle 6: missing playwright import
# ---------------------------------------------------------------------------

def test_missing_playwright_import():
    script = textwrap.dedent(
        """
        import os

        TARGET_URL = os.environ.get("TARGET_URL", "http://localhost")

        def test_x(page):
            pass
        """
    ).strip()
    result = analyze(script)
    assert result.passed is False
    assert "must import playwright" in result.reasons


# ---------------------------------------------------------------------------
# cycle 7: syntax error → exactly one reason, no crash
# ---------------------------------------------------------------------------

def test_syntax_error_short_circuits():
    result = analyze("def test(:")
    assert result.passed is False
    assert len(result.reasons) == 1
    assert result.reasons[0].startswith("syntax error:")


# ---------------------------------------------------------------------------
# cycle 8: multiple violations → all reasons collected
# ---------------------------------------------------------------------------

def test_multiple_violations_all_collected():
    script = textwrap.dedent(
        """
        import subprocess
        from playwright.sync_api import Page, expect

        def test_x(page: Page):
            eval("bad")
            expect(page.locator("h1")).to_be_visible()
        """
    ).strip()
    result = analyze(script)
    assert result.passed is False
    reason_text = " ".join(result.reasons)
    assert "subprocess" in reason_text
    assert "eval" in reason_text


# ---------------------------------------------------------------------------
# cycle 9: allowed os.* call does not false-positive
# ---------------------------------------------------------------------------

def test_allowed_os_call_does_not_false_positive():
    """os.environ.get is an allowed os.* call; the prefix matcher must not flag it."""
    script = textwrap.dedent(
        """
        import os
        from playwright.sync_api import Page, expect

        TARGET_URL = os.environ.get("TARGET_URL", "http://localhost:8080")

        def test_homepage(page: Page):
            page.goto(TARGET_URL)
            expect(page.locator("h1")).to_be_visible()
        """
    ).strip()
    result = analyze(script)
    assert result.passed is True


# ---------------------------------------------------------------------------
# NUL-5 ruff E9,F lint integration
# ---------------------------------------------------------------------------


def test_undefined_name_rejected():
    """Script with undefined name (F821) must be rejected with exactly one lint reason."""
    script = textwrap.dedent(
        """
        from playwright.sync_api import Page, expect

        def test_x(page: Page):
            undefined_helper()
            expect(page.locator("h1")).to_be_visible()
        """
    ).strip()
    result = analyze(script, ruff_executable=RUFF)
    assert result.passed is False
    lint_reasons = [r for r in result.reasons if r.startswith("lint:")]
    assert len(lint_reasons) == 1
    assert "F821" in lint_reasons[0]


def test_unused_import_rejected():
    """Script importing an allowed-but-unused module (F401) must be rejected with exactly one lint reason."""
    script = textwrap.dedent(
        """
        import re
        from playwright.sync_api import Page, expect

        def test_x(page: Page):
            expect(page.locator("h1")).to_be_visible()
        """
    ).strip()
    result = analyze(script, ruff_executable=RUFF)
    assert result.passed is False
    lint_reasons = [r for r in result.reasons if r.startswith("lint:")]
    assert len(lint_reasons) == 1
    assert "F401" in lint_reasons[0]


def test_style_only_does_not_reject():
    """Cosmetic style issues (long lines, non-snake-case) must not cause rejection.

    E9,F rules do not flag style — only correctness — so a script with only
    style violations should pass. The fixture contains a line clearly over 88
    characters to ensure E501 would fire if selected, proving E9,F selection
    does NOT include style rules.
    """
    # This comment is intentionally very long to exceed ruff's E501 limit of 88 characters and trigger E501 if style rules were active.
    script = textwrap.dedent(
        """
        from playwright.sync_api import Page, expect

        def test_x(page: Page):
            # This comment line is intentionally very long to exceed the 88-character E501 limit enforced by ruff style rules.
            expect(page.locator("h1")).to_be_visible()
        """
    ).strip()
    result = analyze(script, ruff_executable=RUFF)
    assert result.passed is True
    assert not any("lint" in r for r in result.reasons)


def test_clean_script_passes_with_ruff():
    """The existing clean fixture must still pass when ruff is explicitly provided."""
    result = analyze(_CLEAN_SCRIPT, ruff_executable=RUFF)
    assert result.passed is True
    assert result.reasons == ()
