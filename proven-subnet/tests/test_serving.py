"""Tests for verification.serving — local static + overlay serving."""

import urllib.error
import urllib.request

from verification.serving import serve_app, serve_directory


def _get(url):
    with urllib.request.urlopen(url, timeout=5) as resp:
        return resp.status, resp.read().decode("utf-8")


def test_serve_directory_serves_files(tmp_path):
    (tmp_path / "src" / "html").mkdir(parents=True)
    (tmp_path / "src" / "html" / "index.html").write_text(
        "<h1>hello</h1>", encoding="utf-8"
    )

    with serve_directory(tmp_path) as base:
        status, body = _get(f"{base}/src/html/index.html")

    assert status == 200
    assert "hello" in body


def test_serve_directory_tears_down(tmp_path):
    (tmp_path / "index.html").write_text("ok", encoding="utf-8")

    with serve_directory(tmp_path) as base:
        captured = base
        assert _get(f"{base}/index.html")[0] == 200

    try:
        urllib.request.urlopen(f"{captured}/index.html", timeout=1)
        refused = False
    except (OSError, urllib.error.URLError):
        refused = True
    assert refused


def test_serve_app_overlays_mutated_file(tmp_path):
    ref = tmp_path / "ref"
    (ref / "src" / "html").mkdir(parents=True)
    (ref / "src" / "html" / "index.html").write_text(
        "<h1>original</h1>", encoding="utf-8"
    )
    (ref / "assets").mkdir()
    (ref / "assets" / "logo.txt").write_text("LOGO", encoding="utf-8")

    overlay = {"src/html/index.html": "<h1>mutated</h1>"}
    with serve_app(ref, overlay) as base:
        idx_status, idx_body = _get(f"{base}/src/html/index.html")
        asset_status, asset_body = _get(f"{base}/assets/logo.txt")

    assert idx_status == 200
    assert "mutated" in idx_body
    assert "original" not in idx_body
    # Untouched files fall back to the (shared) reference tree.
    assert asset_status == 200
    assert asset_body == "LOGO"


def test_serve_app_without_overlay_serves_reference(tmp_path):
    ref = tmp_path / "ref"
    ref.mkdir()
    (ref / "index.html").write_text("base", encoding="utf-8")

    with serve_app(ref) as base:
        status, body = _get(f"{base}/index.html")

    assert status == 200
    assert body == "base"
