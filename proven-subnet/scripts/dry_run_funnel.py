"""End-to-end dry run of the Proven Verification Funnel (no chain, no Docker).

Serves the clean Reference app and dynamically generated mutants with the stdlib
server, then exercises the funnel exactly as the validator does (Golden Oracle
admission, Reference Gate, Tautology Trap, Mutant Horde) for one or all Feature
Areas, printing P_clean, K_i / N_mut, E_i and the final score S_i.

The "miner" here is a generic, manifest-driven smoke test built from the
broadcast Selector Manifest, so it works across every Feature Area.

Requires pytest-playwright + a chromium browser:

    pip install pytest-playwright playwright
    playwright install chromium          # add --with-deps on a fresh host

On a host where the bundled browser is unavailable, point the run at a system
chromium instead:

    PROVEN_CHROMIUM_EXECUTABLE=/usr/bin/chromium-browser \\
    PROVEN_CHROMIUM_NO_SANDBOX=1 python scripts/dry_run_funnel.py [area|all]
"""

import contextlib
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from verification.efficiency import efficiency  # noqa: E402
from verification.feature_areas import (  # noqa: E402
    FEATURE_AREAS,
    load_reference_files,
)
from verification.mutation import (  # noqa: E402
    blunt_killer,
    generate_mutants,
)
from verification.oracle import admit  # noqa: E402
from verification.scoring import compute_score  # noqa: E402
from verification.serving import serve_app, serve_directory  # noqa: E402

REFERENCE_ROOT = ROOT / "docker" / "reference"
SOFT_BUDGET = 10.0
HARD_TIMEOUT = 60.0
MUTANTS_PER_AREA = 4

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


def _smoke_script(target_url, area):
    """Build a generic genuine test from the area's Selector Manifest."""
    lines = [
        "import os",
        "from playwright.sync_api import Page, expect",
        "",
        f"TARGET_URL = os.environ.get('TARGET_URL', {target_url!r})",
        "",
        "",
        "def test_smoke(page: Page):",
        f"    page.goto(f'{{TARGET_URL}}{area.target_path}')",
    ]
    for el in area.manifest()["elements"]:
        lines.append(f"    loc = page.locator({el['selector']!r})")
        lines.append("    expect(loc).to_have_count(1)")
        if el.get("state", {}).get("visible"):
            lines.append("    expect(loc.first).to_be_visible()")
        if el.get("accessible_name"):
            lines.append(
                f"    expect(loc.first).to_contain_text("
                f"{el['accessible_name']!r})"
            )
        for key, value in (el.get("attributes") or {}).items():
            lines.append(
                f"    expect(loc.first).to_have_attribute("
                f"{key!r}, {value!r})"
            )
    return "\n".join(lines) + "\n"


def run_area(area, n=MUTANTS_PER_AREA):
    reference_files = load_reference_files(area, REFERENCE_ROOT)
    candidates = generate_mutants(
        reference_files, area.operators, seed=1234, n=n
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
        served = [
            (m, stack.enter_context(serve_app(REFERENCE_ROOT, m.files)))
            for m in candidates
        ]
        bk_url = stack.enter_context(serve_app(REFERENCE_ROOT, bk.files))

        print(f"== {area.name} ({area.target_path}) ==")
        print(
            "  Golden Oracle on reference:",
            "PASS" if run_oracle(reference_url) else "FAIL",
        )

        admitted = admit(served, run_oracle, reference_url)
        mutant_urls = [url for _m, url in admitted]
        n_mut = len(mutant_urls)
        print(
            f"  admitted {n_mut}/{len(served)}: "
            + ", ".join(m.name for m, _ in admitted)
        )

        miner = work / "miner_script.py"
        miner.write_text(
            _smoke_script(reference_url, area), encoding="utf-8"
        )

        start = time.perf_counter()
        p_clean = 1 if run_pytest(miner, reference_url).returncode == 0 else 0
        ref_time = time.perf_counter() - start
        trapped = run_pytest(miner, bk_url).returncode == 0
        if p_clean and trapped:
            p_clean = 0

        kills = sum(
            1
            for url in mutant_urls
            if run_pytest(miner, url).returncode != 0
        )
        e_i = efficiency(ref_time, SOFT_BUDGET, HARD_TIMEOUT)
        score = compute_score(p_clean, kills, n_mut, e_i)
        print(
            f"  P_clean={p_clean}  K_i/N_mut={kills}/{n_mut}  "
            f"E_i={e_i:.3f}  =>  S_i={score:.4f}\n"
        )
        return score


def main():
    arg = sys.argv[1] if len(sys.argv) > 1 else "all"
    if arg == "all":
        areas = list(FEATURE_AREAS.values())
    else:
        areas = [FEATURE_AREAS[arg]]
    for area in areas:
        run_area(area)


if __name__ == "__main__":
    main()
