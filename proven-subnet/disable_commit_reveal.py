import os
from substrateinterface import SubstrateInterface, Keypair

NETWORK = os.environ.get("NETWORK", "ws://127.0.0.1:9945")
NETUID = int(os.environ.get("NETUID", "2"))

substrate = SubstrateInterface(url=NETWORK)
alice = Keypair.create_from_uri("//Alice")

call = substrate.compose_call(
    call_module="AdminUtils",
    call_function="sudo_set_commit_reveal_weights_enabled",
    call_params={"netuid": NETUID, "enabled": False}
)

# This needs sudo wrapper since it's an admin function
sudo_call = substrate.compose_call(
    call_module="Sudo",
    call_function="sudo",
    call_params={"call": call}
)

extrinsic = substrate.create_signed_extrinsic(call=sudo_call, keypair=alice)
receipt = substrate.submit_extrinsic(extrinsic, wait_for_inclusion=True)
print(f"✅ Commit-reveal disabled: {receipt.is_success}")