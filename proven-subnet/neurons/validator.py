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


import os
import time
import tempfile
import subprocess

import torch
import bittensor as bt

from verification.efficiency import efficiency
from verification.plagiarism import FirstSubmitterRegistry, duplicate_submitters
from verification.scoring import compute_score
from verification.static_gate import analyze

# Import your custom protocol
from template.protocol import E2ETestingSynapse

# import base validator class which takes care of most of the boilerplate
from template.base.validator import BaseValidatorNeuron


class Validator(BaseValidatorNeuron):
    """
    The Proven Validator Neuron.
    Broadcasts specifications to miners, collects their Playwright scripts, 
    and executes them against the Reference and Mutated Docker containers.
    """

    def __init__(self, config=None):
        super(Validator, self).__init__(config=config)
        bt.logging.info("load_state()")
        self.load_state()

    REFERENCE_URL = "http://localhost:8080"
    MUTANT_URL = "http://localhost:8081"
    PYTEST_TIMEOUT_SECONDS = 60.0
    EFFICIENCY_SOFT_BUDGET_SECONDS = 10.0

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

    def evaluate_miner(
        self,
        script_content: str,
        submitter_id: str | None = None,
        duplicate_submitter_ids: set[str] | None = None,
    ) -> float:
        """Executes the Verification Funnel and returns a graded score."""
        if not script_content:
            return 0.0

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
                f"❌ Duplicate within-epoch submission from {submitter_id}. Score: 0"
            )
            return 0.0

        if submitter_id is not None:
            try:
                is_duplicate = self._ensure_plagiarism_registry().register(
                    submitter_id, script_content, time.time()
                )
            except ValueError as exc:
                bt.logging.warning(
                    f"❌ Submission from {submitter_id} could not be fingerprinted: {exc}"
                )
                return 0.0
            if is_duplicate:
                bt.logging.warning(
                    f"❌ Cross-epoch duplicate submission from {submitter_id}. Score: 0"
                )
                return 0.0

        # Save the string from the miner to a temporary Python file only after
        # the static gate passes, so rejected submissions never reach pytest.
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(script_content)
            script_path = f.name

        try:
            bt.logging.trace("--- Stage 2: Reference Gate (Clean App) ---")
            env = {**os.environ, "TARGET_URL": self.REFERENCE_URL}
            start_time = time.perf_counter()
            res_clean = subprocess.run(
                ["pytest", script_path, "--tb=short", "--browser", "chromium"],
                env=env,
                capture_output=True,
                text=True,
                timeout=self.PYTEST_TIMEOUT_SECONDS,
            )
            clean_exec_time = time.perf_counter() - start_time
            p_clean = 1 if res_clean.returncode == 0 else 0

            if not p_clean:
                bt.logging.warning(
                    "❌ Miner failed Reference Gate (False Positive). Score: 0"
                )
                return 0.0

            bt.logging.trace("--- Stage 3: Mutant Horde (Mutated App) ---")
            env_mutant = {**os.environ, "TARGET_URL": self.MUTANT_URL}
            res_mutant = subprocess.run(
                ["pytest", script_path, "--tb=short", "--browser", "chromium"],
                env=env_mutant,
                capture_output=True,
                text=True,
                timeout=self.PYTEST_TIMEOUT_SECONDS,
            )

            # Current funnel has one mutant fixture.  A non-zero pytest return
            # code means the miner assertions killed that mutant.
            kills = 1 if res_mutant.returncode != 0 else 0
            n_mut = 1
            e_i = efficiency(
                clean_exec_time,
                self.EFFICIENCY_SOFT_BUDGET_SECONDS,
                self.PYTEST_TIMEOUT_SECONDS,
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

    async def forward(self):
        """
        The main Validator loop.
        1. Generates the task.
        2. Queries the miners.
        3. Evaluates their code.
        4. Updates their scores.
        """
        bt.logging.info(f"🚀 Starting Validation Epoch. Querying miners...")

        # 1. Create the Task 
        synapse = E2ETestingSynapse(
            spec_type="user_story",
            requirement_content="Check Willify homepage for Read More button, heading, and register link.",
            target_url="http://localhost:8080"  # base URL only, miner appends /src/html/index.html
        )

        # 2. Query the Miners
        # self.dendrite broadcasts the Synapse to all registered miners
        responses = await self.dendrite(
            axons=self.metagraph.axons,
            synapse=synapse,
            deserialize=False,
            timeout=15,
        )

        # 3. Evaluate the Responses
        rewards = torch.zeros(len(responses))
        submitter_ids = [
            str(hotkey) for hotkey in self.metagraph.hotkeys[: len(responses)]
        ]
        scripts: list[str] = []
        for response in responses:
            script_content = ""
            if response is not None and hasattr(response, "playwright_script"):
                script_content = response.playwright_script or ""
            scripts.append(script_content)

        duplicate_ids = duplicate_submitters(zip(submitter_ids, scripts))

        for i, (submitter_id, script_content) in enumerate(
            zip(submitter_ids, scripts)
        ):
            bt.logging.info(f"Evaluating Miner {i} ({submitter_id})...")
            score = self.evaluate_miner(script_content, submitter_id, duplicate_ids)
            rewards[i] = score

        bt.logging.info(f"🏆 Epoch Scores: {rewards}")

        # 4. Update the scores on the network
        miner_uids = torch.tensor(list(range(len(self.metagraph.axons))), dtype=torch.long)
        self.update_scores(rewards, miner_uids)


if __name__ == "__main__":
    with Validator() as validator:
        while True:
            bt.logging.info(f"Validator running... {time.time()}")
            time.sleep(10) # Wait 10 seconds between epochs