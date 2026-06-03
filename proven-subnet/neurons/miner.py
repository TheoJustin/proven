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



import time
import typing
import bittensor as bt

# Import your custom protocol
from template.protocol import E2ETestingSynapse
from template.ai import AzurePlaywrightGenerator, build_fallback_script

# import base miner class which takes care of most of the boilerplate
from template.base.miner import BaseMinerNeuron


class Miner(BaseMinerNeuron):
    """
    The Proven Miner Neuron. 
    Listens for E2ETestingSynapse challenges from Validators and returns Playwright test scripts.
    """

    def __init__(self, config=None):
        super(Miner, self).__init__(config=config)
        self.test_generator = AzurePlaywrightGenerator.from_env()
        if self.test_generator is None:
            bt.logging.info("Azure OpenAI generation is not configured; using fallback test script.")
        else:
            bt.logging.info(
                "Azure OpenAI generation enabled "
                f"(deployment={self.test_generator.config.deployment}, "
                f"api_version={self.test_generator.config.api_version})."
            )

    async def forward(
        self, synapse: E2ETestingSynapse
    ) -> E2ETestingSynapse:
        """
        Processes the incoming E2ETestingSynapse.
        This is where the miner generates the Playwright script to satisfy the specification.
        """
        bt.logging.info(f"🎯 Received testing specification: {synapse.spec_type}")
        bt.logging.info(f"🔗 Target Validator URL: {synapse.target_url}")

        if self.test_generator is None:
            script_content = build_fallback_script(
                synapse.target_url,
                getattr(synapse, "selector_manifest", None),
            )
        else:
            try:
                script_content = self.test_generator.generate_script(
                    spec_type=synapse.spec_type,
                    requirement_content=synapse.requirement_content,
                    target_url=synapse.target_url,
                    selector_manifest=getattr(synapse, "selector_manifest", None),
                )
                bt.logging.success("✅ AI-generated Playwright script attached to Synapse.")
            except Exception as exc:
                bt.logging.warning(
                    "AI generation failed; using deterministic fallback "
                    f"({exc.__class__.__name__})."
                )
                script_content = build_fallback_script(
                    synapse.target_url,
                    getattr(synapse, "selector_manifest", None),
                )

        # Attach the raw Python string to the synapse output
        synapse.playwright_script = script_content.strip()
        
        bt.logging.success("✅ Playwright script synthesized and attached to Synapse.")
        
        return synapse

    async def blacklist(self, synapse: E2ETestingSynapse) -> typing.Tuple[bool, str]:
        if synapse.dendrite is None or synapse.dendrite.hotkey is None:
            bt.logging.warning("Received a request without a dendrite or hotkey.")
            return True, "Missing dendrite or hotkey"

        # ✅ Check existence FIRST
        if synapse.dendrite.hotkey not in self.metagraph.hotkeys:
            if not self.config.blacklist.allow_non_registered:
                bt.logging.trace(f"Blacklisting un-registered hotkey {synapse.dendrite.hotkey}")
                return True, "Unrecognized hotkey"

        # ✅ THEN look up the uid safely
        uid = self.metagraph.hotkeys.index(synapse.dendrite.hotkey)

        if self.config.blacklist.force_validator_permit:
            if not self.metagraph.validator_permit[uid]:
                bt.logging.warning(f"Blacklisting non-validator hotkey {synapse.dendrite.hotkey}")
                return True, "Non-validator hotkey"

        bt.logging.trace(f"Not Blacklisting recognized hotkey {synapse.dendrite.hotkey}")
        return False, "Hotkey recognized!"

    async def priority(self, synapse: E2ETestingSynapse) -> float:
        """
        Determines the priority order of requests based on Validator stake.
        """
        if synapse.dendrite is None or synapse.dendrite.hotkey is None:
            bt.logging.warning("Received a request without a dendrite or hotkey.")
            return 0.0

        caller_uid = self.metagraph.hotkeys.index(synapse.dendrite.hotkey) 
        priority = float(self.metagraph.S[caller_uid]) 
        bt.logging.trace(f"Prioritizing {synapse.dendrite.hotkey} with value: {priority}")
        return priority


if __name__ == "__main__":
    with Miner() as miner:
        while True:
            bt.logging.info(f"Miner running... {time.time()}")
            time.sleep(5)
