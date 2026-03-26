import time
from substrateinterface import SubstrateInterface, Keypair

VALIDATOR_ADDRESS = "5HGqKDGFnEevt8rvr7YBwV6MCg4hBxzFQf4Mo6ASHLEtKFtb"
MINER_ADDRESS = "5ED2D3nYwe8ihvJCh7qZPDYjCUzZ9NKKYqdV68J8B4DdrFAw"

def fund(dest, amount_tao):
    # Fresh connection every time
    substrate = SubstrateInterface(url="ws://127.0.0.1:9945")
    alice = Keypair.create_from_uri("//Alice")
    
    amount_rao = amount_tao * 1_000_000_000
    call = substrate.compose_call(
        call_module="Balances",
        call_function="transfer_keep_alive",
        call_params={"dest": dest, "value": amount_rao}
    )
    extrinsic = substrate.create_signed_extrinsic(call=call, keypair=alice)
    receipt = substrate.submit_extrinsic(extrinsic, wait_for_inclusion=False)
    print(f"✅ Transaction submitted for {dest}")
    substrate.close()
    time.sleep(5)

fund(VALIDATOR_ADDRESS, 1000)
fund(MINER_ADDRESS, 1000)

# Verify balances with fresh connection
print("\nVerifying balances...")
substrate = SubstrateInterface(url="ws://127.0.0.1:9944")
for name, addr in [("Validator", VALIDATOR_ADDRESS), ("Miner", MINER_ADDRESS)]:
    result = substrate.query("System", "Account", [addr])
    balance = result["data"]["free"].value / 1_000_000_000
    print(f"{name}: {balance} TAO")
substrate.close()