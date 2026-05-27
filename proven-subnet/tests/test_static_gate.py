"""Tests for verification.static_gate — NUL-2."""

import textwrap

from verification.static_gate import analyze

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
