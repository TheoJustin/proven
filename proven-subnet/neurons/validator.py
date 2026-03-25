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
import typing
import tempfile
import subprocess
import torch
import bittensor as bt

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

    def evaluate_miner(self, script_content: str) -> float:
        """
        Executes the 3-Stage Verification Funnel from the Proven proposal.
        """
        if not script_content:
            return 0.0

        # Save the string from the miner to a temporary Python file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(script_content)
            script_path = f.name

        try:
            bt.logging.trace("--- Stage 1: Static Gate ---")
            subprocess.run(["python", "-m", "py_compile", script_path], check=True, capture_output=True)

            bt.logging.trace("--- Stage 2: Reference Gate (Clean App) ---")
            # Run against the clean Willify container on port 8080
            env = {**os.environ, "TARGET_URL": "http://localhost:8080"}
            res_clean = subprocess.run(
                ["pytest", script_path, "--tb=short", "--browser", "chromium"], 
                env=env, capture_output=True, text=True, timeout=60
            )
            
            if res_clean.returncode != 0:
                bt.logging.warning("❌ Miner failed Reference Gate (False Positive). Score: 0")
                return 0.0

            bt.logging.trace("--- Stage 3: Mutant Horde (Mutated App) ---")
            # Run against the mutated Willify container on port 8081
            env_mutant = {**os.environ, "TARGET_URL": "http://localhost:8081"}
            res_mutant = subprocess.run(
                ["pytest", script_path, "--tb=short"], 
                env=env_mutant, capture_output=True, text=True, timeout=60
            )

            # In Pytest, a non-zero return code means assertions failed (The mutant was killed!)
            if res_mutant.returncode != 0:
                bt.logging.success("✅ Miner caught the bug! Mutant Killed. Score: 1.0")
                return 1.0
            else:
                bt.logging.warning("❌ Miner missed the bug! Mutant Survived. Score: 0.0")
                return 0.0

        except subprocess.CalledProcessError:
            bt.logging.warning("❌ Linting Failed: Syntax errors found in miner script.")
            return 0.0
        except subprocess.TimeoutExpired:
            bt.logging.warning("❌ Miner script timed out.")
            return 0.0
        finally:
            # Clean up the temporary file
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

        for i, response in enumerate(responses):
            bt.logging.info(f"Evaluating Miner {i}...")
            # Guard against None (timeout) or missing script
            script_content = ""
            if response is not None and hasattr(response, "playwright_script"):
                script_content = response.playwright_script or ""
            score = self.evaluate_miner(script_content)
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