# The MIT License (MIT)
# Copyright © 2023 Yuma Rao
# TODO(developer): Set your name
# Copyright © 2023 <your name>

# Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated
# documentation files (the “Software”), to deal in the Software without restriction, including without limitation
# the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software,
# and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in all copies or substantial portions of
# the Software.

# THE SOFTWARE IS PROVIDED “AS IS”, WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO
# THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL
# THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
# OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
# DEALINGS IN THE SOFTWARE.


import contextlib
import os
import secrets
import time
import tempfile
import subprocess

import torch
import bittensor as bt

from verification.efficiency import efficiency
from verification.feature_areas import (
    load_reference_files,
    select_feature_area,
)
from verification.mutation import blunt_killer, generate_mutants
from verification.oracle import admit
from verification.plagiarism import FirstSubmitterRegistry, duplicate_submitters
from verification.probing import crawls_dom_despite_manifest
from verification.scoring import compute_score
from verification.selector_manifest import build_manifest, playwright_crawl
from verification.serving import serve_app
from verification.static_gate import analyze

# Import your custom protocol
from template.protocol import E2ETestingSynapse

# import base validator class which takes care of most of the boilerplate
from template.base.validator import BaseValidatorNeuron


# Path to the clean Reference app source tree (served at REFERENCE_URL and used
# as the substrate the Mutation Engine mutates).
_REFERENCE_ROOT = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "docker",
    "reference",
)


class Validator(BaseValidatorNeuron):
    """
    The Proven Validator Neuron.

    Each epoch it builds a behaviour-first Selector Manifest, dynamically
    generates and oracle-admits a fresh Mutant Horde from the Reference app,
    broadcasts a single Feature Area spec, and grades every miner's Playwright
    script through the Verification Funnel:

        Static Gate -> Reference Gate -> Tautology Trap -> Mutant Horde -> S_i

    where ``S_i = P_clean * (alpha * K_i / N_mut) * E_i``.
    """

    def __init__(self, config=None):
        super(Validator, self).__init__(config=config)
        bt.logging.info("load_state()")
        self.load_state()

    REFERENCE_URL = "http://localhost:8080"
    PYTEST_TIMEOUT_SECONDS = 60.0
    EFFICIENCY_SOFT_BUDGET_SECONDS = 10.0

    # --- plagiarism registry -------------------------------------------------

    def _plagiarism_registry_path(self) -> str:
        return os.path.join(
            self.config.neuron.full_path, "first_submitter_registry.json"
        )

    def _ensure_plagiarism_registry(self) -> FirstSubmitterRegistry:
        registry = getattr(self, "first_submitter_registry", None)
        if registry is None:
            registry = FirstSubmitterRegistry.load(
                self._plagiarism_registry_path()
            )
            self.first_submitter_registry = registry
        return registry

    # --- execution helpers ---------------------------------------------------

    def _run_script(self, script_path: str, target_url: str):
        """Run a pytest-playwright script against *target_url*."""
        env = {**os.environ, "TARGET_URL": target_url}
        return subprocess.run(
            ["pytest", script_path, "--tb=short", "--browser", "chromium"],
            env=env,
            capture_output=True,
            text=True,
            timeout=self.PYTEST_TIMEOUT_SECONDS,
        )

    def _timed_run(self, script_path: str, target_url: str):
        """Run a script and return ``(CompletedProcess, elapsed_seconds)``."""
        start_time = time.perf_counter()
        result = self._run_script(script_path, target_url)
        return result, time.perf_counter() - start_time

    def _run_oracle_suite(self, oracle_suite: str, target_url: str) -> bool:
        """Return True iff the Golden Oracle Suite passes against *target_url*."""
        env = {**os.environ, "TARGET_URL": target_url}
        result = subprocess.run(
            ["pytest", oracle_suite, "--tb=line", "--browser", "chromium"],
            env=env,
            capture_output=True,
            text=True,
            timeout=self.PYTEST_TIMEOUT_SECONDS,
        )
        return result.returncode == 0

    # --- verification funnel -------------------------------------------------

    def evaluate_miner(
        self,
        script_content: str,
        submitter_id: str | None = None,
        duplicate_submitter_ids: set[str] | None = None,
        selector_manifest=None,
        reference_url: str | None = None,
        blunt_killer_url: str | None = None,
        mutant_urls=None,
    ) -> float:
        """Run the Verification Funnel for one miner and return ``S_i``."""
        if not script_content:
            return 0.0

        reference_url = reference_url or self.REFERENCE_URL
        mutant_urls = list(mutant_urls or [])

        probing = crawls_dom_despite_manifest(script_content, selector_manifest)
        if probing:
            bt.logging.warning(
                "⚠️ Miner script probes/crawls the DOM despite a provided "
                "selector manifest; applying E_i probing penalty."
            )

        bt.logging.trace("--- Stage 1: Static Gate ---")
        gate_result = analyze(script_content)
        if not gate_result.passed:
            bt.logging.warning(
                "❌ Static Gate failed. Score: 0. Reasons: "
                + "; ".join(gate_result.reasons)
            )
            return 0.0

        if (
            submitter_id is not None
            and duplicate_submitter_ids is not None
            and submitter_id in duplicate_submitter_ids
        ):
            bt.logging.warning(
                f"❌ Duplicate within-epoch submission from {submitter_id}. "
                "Score: 0"
            )
            return 0.0

        if submitter_id is not None:
            try:
                is_duplicate = self._ensure_plagiarism_registry().register(
                    submitter_id, script_content, time.time()
                )
            except ValueError as exc:
                bt.logging.warning(
                    f"❌ Submission from {submitter_id} could not be "
                    f"fingerprinted: {exc}"
                )
                return 0.0
            if is_duplicate:
                bt.logging.warning(
                    f"❌ Cross-epoch duplicate submission from {submitter_id}. "
                    "Score: 0"
                )
                return 0.0

        # Persist the miner string to a temp file only after the cheap gates
        # pass, so rejected submissions never reach pytest.
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".py", delete=False
        ) as f:
            f.write(script_content)
            script_path = f.name

        try:
            bt.logging.trace("--- Stage 2: Reference Gate (Clean App) ---")
            res_clean, clean_exec_time = self._timed_run(
                script_path, reference_url
            )
            p_clean = 1 if res_clean.returncode == 0 else 0
            if not p_clean:
                bt.logging.warning(
                    "❌ Miner failed Reference Gate (False Positive). Score: 0"
                )
                return 0.0

            bt.logging.trace("--- Stage 3: Tautology Trap (Blunt Killer) ---")
            if blunt_killer_url is not None:
                res_trap = self._run_script(script_path, blunt_killer_url)
                if res_trap.returncode == 0:
                    bt.logging.warning(
                        "❌ Script passes with the feature area blanked "
                        "(happy-path ghost). P_clean = 0. Score: 0"
                    )
                    return 0.0

            bt.logging.trace("--- Stage 4: Mutant Horde (Mutated Apps) ---")
            kills = 0
            for url in mutant_urls:
                res_mutant = self._run_script(script_path, url)
                if res_mutant.returncode != 0:
                    kills += 1
            n_mut = len(mutant_urls)

            e_i = efficiency(
                clean_exec_time,
                self.EFFICIENCY_SOFT_BUDGET_SECONDS,
                self.PYTEST_TIMEOUT_SECONDS,
                probing=probing,
            )
            score = compute_score(p_clean, kills, n_mut, e_i)
            bt.logging.info(
                f"Verification score={score:.4f} "
                f"(p_clean={p_clean}, kills={kills}/{n_mut}, e_i={e_i:.4f}, "
                f"reference_time={clean_exec_time:.3f}s)"
            )
            return float(score)

        except subprocess.TimeoutExpired:
            bt.logging.warning("❌ Miner script timed out.")
            return 0.0
        finally:
            os.remove(script_path)

    # --- epoch loop ----------------------------------------------------------

    async def forward(self):
        """
        The main Validator loop.
        1. Build the task (Feature Area spec + Selector Manifest).
        2. Generate and oracle-admit the Mutant Horde + Blunt Killer.
        3. Query the miners.
        4. Score each through the Verification Funnel against the identical set.
        5. Update the on-chain weights.
        """
        bt.logging.info("🚀 Starting Validation Epoch. Querying miners...")

        area = select_feature_area(
            getattr(self.config.neuron, "feature_area", None)
        )
        bt.logging.info(f"📋 Feature area this epoch: {area.name}")
        reference_url = self.REFERENCE_URL
        crawl = not getattr(
            self.config.neuron, "disable_selector_manifest_crawl", False
        )
        mutants_per_epoch = int(
            getattr(self.config.neuron, "mutants_per_epoch", 12)
        )

        # 1. Selector Manifest (behaviour-first; crawl is feature-flagged).
        manifest = build_manifest(
            area,
            reference_url,
            crawl=crawl,
            run_crawl=playwright_crawl if crawl else None,
        )

        # 2. Dynamic, seeded Mutant Horde + Blunt Killer from the reference.
        reference_files = load_reference_files(area, _REFERENCE_ROOT)
        seed = secrets.randbits(32)  # secret per-epoch seed (ADR-0002)
        candidates = generate_mutants(
            reference_files, area.operators, seed, mutants_per_epoch
        )
        bk = blunt_killer(reference_files, area.blunt_operators)

        with contextlib.ExitStack() as stack:
            served = [
                (
                    mutant,
                    stack.enter_context(
                        serve_app(_REFERENCE_ROOT, mutant.files)
                    ),
                )
                for mutant in candidates
            ]
            blunt_killer_url = stack.enter_context(
                serve_app(_REFERENCE_ROOT, bk.files)
            )

            # Oracle admission: keep only genuinely killable mutants.
            try:
                admitted = admit(
                    served,
                    lambda url: self._run_oracle_suite(
                        area.oracle_suite, url
                    ),
                    reference_url,
                )
            except RuntimeError as exc:
                bt.logging.error(f"Oracle admission failed: {exc}")
                return

            mutant_urls = [url for _mutant, url in admitted]
            n_mut = len(mutant_urls)
            bt.logging.info(
                f"Admitted {n_mut}/{len(served)} mutants for "
                f"feature area '{area.name}'."
            )
            if n_mut == 0:
                bt.logging.warning(
                    "No admitted mutants this epoch; skipping scoring."
                )
                return

            # 3. Broadcast the task to all miners.
            synapse = E2ETestingSynapse(
                spec_type=area.spec_type,
                requirement_content=area.requirement_content,
                target_url=reference_url,
                feature_area=area.name,
                selector_manifest=manifest,
            )
            responses = await self.dendrite(
                axons=self.metagraph.axons,
                synapse=synapse,
                deserialize=False,
                timeout=15,
            )

            # 4. Score every miner against the identical admitted set.
            rewards = torch.zeros(len(responses))
            submitter_ids = [
                str(hotkey)
                for hotkey in self.metagraph.hotkeys[: len(responses)]
            ]
            scripts: list[str] = []
            for response in responses:
                script_content = ""
                if response is not None and hasattr(
                    response, "playwright_script"
                ):
                    script_content = response.playwright_script or ""
                scripts.append(script_content)

            duplicate_ids = duplicate_submitters(zip(submitter_ids, scripts))

            for i, (submitter_id, script_content) in enumerate(
                zip(submitter_ids, scripts)
            ):
                bt.logging.info(f"Evaluating Miner {i} ({submitter_id})...")
                rewards[i] = self.evaluate_miner(
                    script_content,
                    submitter_id,
                    duplicate_ids,
                    selector_manifest=manifest,
                    reference_url=reference_url,
                    blunt_killer_url=blunt_killer_url,
                    mutant_urls=mutant_urls,
                )

        bt.logging.info(f"🏆 Epoch Scores: {rewards}")

        # 5. Update the scores on the network.
        miner_uids = torch.tensor(
            list(range(len(self.metagraph.axons))), dtype=torch.long
        )
        self.update_scores(rewards, miner_uids)


if __name__ == "__main__":
    with Validator() as validator:
        while True:
            bt.logging.info(f"Validator running... {time.time()}")
            time.sleep(10)  # Wait 10 seconds between epochs
