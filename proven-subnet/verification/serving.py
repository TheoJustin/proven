"""Local static serving for reference/mutant app trees (stdlib only).

The validator serves the clean Reference app and each dynamically generated
Mutant app over HTTP so Playwright can drive them. Mutants differ from the
reference by only a handful of small files (typically just ``index.html``),
while the asset bundle is large (~80 MB), so copying the whole tree per mutant
would be wasteful. Instead :func:`serve_app` uses a tiny *overlay* directory
holding only the mutated files and falls back to the shared reference tree for
everything else.

Kept behind this small interface on purpose: a Docker/nginx container pool can
replace it later without changing the validator funnel.
"""

from __future__ import annotations

import contextlib
import os
import tempfile
import threading
from collections.abc import Iterator, Mapping
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


def _make_handler(overlay_root: str, base_root: str):
    """Build a request handler that serves *overlay_root* then *base_root*."""

    class _OverlayHandler(SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=overlay_root, **kwargs)

        def log_message(self, *args, **kwargs):  # silence per-request logging
            pass

        def translate_path(self, path: str) -> str:
            fs_path = super().translate_path(path)  # resolved under overlay
            if os.path.exists(fs_path):
                return fs_path
            rel = os.path.relpath(fs_path, overlay_root)
            return os.path.join(base_root, rel)

    return _OverlayHandler


@contextlib.contextmanager
def _run_server(handler) -> Iterator[str]:
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        host, port = server.server_address[:2]
        yield f"http://{host}:{port}"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


@contextlib.contextmanager
def serve_directory(root) -> Iterator[str]:
    """Serve *root* over HTTP on an ephemeral localhost port.

    Yields the base URL (e.g. ``http://127.0.0.1:54123``). The background server
    is shut down when the context exits.
    """
    root = str(Path(root).resolve())
    with _run_server(_make_handler(root, root)) as url:
        yield url


@contextlib.contextmanager
def serve_app(
    reference_root, files: Mapping[str, str] | None = None
) -> Iterator[str]:
    """Serve the reference tree with *files* overlaid on top.

    *files* maps POSIX-style relative paths (e.g. ``"src/html/index.html"``) to
    mutated text content. Those paths are served from a small temp overlay; all
    other requests fall back to *reference_root*. Yields the base URL.
    """
    reference_root = str(Path(reference_root).resolve())
    with tempfile.TemporaryDirectory(prefix="proven-overlay-") as overlay:
        for relpath, content in (files or {}).items():
            target = Path(overlay) / Path(relpath)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")
        handler = _make_handler(str(Path(overlay).resolve()), reference_root)
        with _run_server(handler) as url:
            yield url
