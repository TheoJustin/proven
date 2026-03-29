# Localnet Scripts

These scripts are for local development and local chain bring-up, not for a hardened VPS deployment.

## Script Index

- `01_pull_image.sh`: fetch the base localnet image if required
- `02_start_chain.sh`: start the local chain
- `03_create_wallets.sh`: create local disposable wallets
- `04_fund_wallets.sh`: fund local wallets on localnet
- `05_create_subnet.sh`: create the subnet on the local chain
- `06_register_and_stake.sh`: register miner and validator hotkeys and stake the validator
- `07_run_miner.sh`: launch the miner process
- `08_run_validator.sh`: launch the validator process
- `bootstrap_localnet.sh`: guided wrapper that runs the localnet flow in order

## Safety Notes

- Treat wallet creation here as disposable localnet-only automation.
- Do not reuse the generated names, keys, or assumptions for testnet or mainnet.
- For VPS deployments, create and manage keys on a secure machine first, then provision only the hotkey material you need on the node.
