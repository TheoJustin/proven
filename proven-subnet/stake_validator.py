import os
import bittensor as bt

NETWORK = os.environ.get("NETWORK", "ws://127.0.0.1:9945")
NETUID = int(os.environ.get("NETUID", "2"))
STAKE_PER_ROUND = int(os.environ.get("STAKE_PER_ROUND", "100"))

subtensor = bt.subtensor(network=NETWORK)
wallet = bt.wallet(name="test-validator", hotkey="default")

subtensor.add_stake(
    wallet=wallet,
    hotkey_ss58=wallet.hotkey.ss58_address,
    amount=bt.Balance.from_tao(STAKE_PER_ROUND)
)
print(f"✅ Staked {STAKE_PER_ROUND} TAO for validator")