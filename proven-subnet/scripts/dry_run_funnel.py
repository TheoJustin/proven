"""End-to-end dry run of the Proven Verification Funnel (no chain, no Docker).

Serves the clean Reference app and dynamically generated mutants with the stdlib
server, then exercises the funnel exactly as the validator does (Golden Oracle
admission, Reference Gate, Tautology Trap, Mutant Horde) and prints
P_clean, K_i / N_mut, E_i and the final score S_i.

Requires pytest-playwright + a chromium browser:

    pip install pytest-playwright playwright
    playwright install chromium          # add --with-deps on a fresh host

On a host where the bundled browser is unavailable, point the run at a system
chromium instead:

    PROVEN_CHROMIUM_EXECUTABLE=/usr/bin/chromium-browser \\
    PROVEN_CHROMIUM_NO_SANDBOX=1 python scripts/dry_run_funnel.py
"""

import contextlib
import importlib.util
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def _load_build_fallback_script():
    """Load the miner fallback builder without importing the bittensor-coupled
    ``template`` package (its ``__init__`` imports bittensor)."""
    path = ROOT / "template" / "ai" / "playwright_generator.py"
    spec = importlib.util.spec_from_file_location("playwright_generator", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module  # dataclass needs the module registered
    spec.loader.exec_module(module)
    return module.build_fallback_script

from verification.efficiency import efficiency  # noqa: E402
from verification.feature_areas import (  # noqa: E402
    WILLIFY_HOMEPAGE,
    load_reference_files,
)
from verification.mutation import (  # noqa: E402
    blunt_killer,
    generate_mutants,
)
from verification.oracle import admit  # noqa: E402
from verification.scoring import compute_score  # noqa: E402
from verification.selector_manifest import build_manifest  # noqa: E402
from verification.serving import serve_app, serve_directory  # noqa: E402

REFERENCE_ROOT = ROOT / "docker" / "reference"
SOFT_BUDGET = 10.0
HARD_TIMEOUT = 60.0

# A conftest that lets pytest-playwright use a system chromium when the bundled
# browser is unavailable. No-op unless PROVEN_CHROMIUM_EXECUTABLE is set.
_CONFTEST = """
import os
import pytest


@pytest.fixture(scope="session")
def browser_type_launch_args(browser_type_launch_args):
    args = dict(browser_type_launch_args)
    exe = os.environ.get("PROVEN_CHROMIUM_EXECUTABLE")
    if exe:
        args["executable_path"] = exe
    if os.environ.get("PROVEN_CHROMIUM_NO_SANDBOX") == "1":
        args["args"] = [*args.get("args", []), "--no-sandbox"]
    return args
"""


def main():
    build_fallback_script = _load_build_fallback_script()

    area = WILLIFY_HOMEPAGE
    reference_files = load_reference_files(area, REFERENCE_ROOT)
    candidates = generate_mutants(
        reference_files, area.operators, seed=1234, n=6
    )
    bk = blunt_killer(reference_files, area.blunt_operators)

    with tempfile.TemporaryDirectory(
        prefix="proven-dryrun-"
    ) as work, contextlib.ExitStack() as stack:
        work = Path(work)
        (work / "conftest.py").write_text(_CONFTEST, encoding="utf-8")
        oracle_local = work / "oracle_suite.py"
        oracle_local.write_text(
            Path(area.oracle_suite).read_text(encoding="utf-8"),
            encoding="utf-8",
        )

        def run_pytest(path, target_url):
            env = {**os.environ, "TARGET_URL": target_url}
            return subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "pytest",
                    str(path),
                    "--tb=line",
                    "--browser",
                    "chromium",
                ],
                cwd=str(work),
                env=env,
                capture_output=True,
                text=True,
                timeout=HARD_TIMEOUT,
            )

        def run_oracle(url):
            return run_pytest(oracle_local, url).returncode == 0

        reference_url = stack.enter_context(serve_directory(REFERENCE_ROOT))
        manifest = build_manifest(area, reference_url, crawl=False)
        served = [
            (m, stack.enter_context(serve_app(REFERENCE_ROOT, m.files)))
            for m in candidates
        ]
        bk_url = stack.enter_context(serve_app(REFERENCE_ROOT, bk.files))

        print(f"Reference served at {reference_url}")
        print(
            "Golden Oracle on reference:",
            "PASS" if run_oracle(reference_url) else "FAIL",
        )

        admitted = admit(served, run_oracle, reference_url)
        mutant_urls = [url for _m, url in admitted]
        n_mut = len(mutant_urls)
        print(
            f"Admitted {n_mut}/{len(served)} mutants: "
            + ", ".join(m.name for m, _ in admitted)
        )

        miner_path = work / "miner_script.py"
        miner_path.write_text(
            build_fallback_script(reference_url, selector_manifest=manifest),
            encoding="utf-8",
        )

        start = time.perf_counter()
        p_clean = 1 if run_pytest(miner_path, reference_url).returncode == 0 else 0
        ref_time = time.perf_counter() - start
        print(f"Reference Gate: {'PASS' if p_clean else 'FAIL'} ({ref_time:.2f}s)")

        trapped = run_pytest(miner_path, bk_url).returncode == 0
        print(
            "Tautology Trap: "
            + (
                "GHOST -> P_clean=0"
                if trapped
                else "genuine test (fails on blunt killer, as expected)"
            )
        )
        if p_clean and trapped:
            p_clean = 0

        kills = sum(
            1
            for url in mutant_urls
            if run_pytest(miner_path, url).returncode != 0
        )
        e_i = efficiency(ref_time, SOFT_BUDGET, HARD_TIMEOUT)
        score = compute_score(p_clean, kills, n_mut, e_i)
        print(
            f"\nP_clean={p_clean}  K_i/N_mut={kills}/{n_mut}  "
            f"E_i={e_i:.3f}  =>  S_i={score:.4f}"
        )


if __name__ == "__main__":
    main()
