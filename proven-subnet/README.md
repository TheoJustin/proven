# Proven Subnet

Proven is a Bittensor subnet prototype for spec-driven software verification. In the current implementation, miners return Playwright-style Python tests from a verification task, and validators evaluate those tests against a clean app and a mutant app.

## What The Repo Contains

- `neurons/`: miner and validator entrypoints
- `template/`: shared subnet base classes, protocol definitions, and config helpers
- `docker/reference/`: clean web-app fixture served by Nginx
- `docker/mutant/`: intentionally changed web-app fixture served by Nginx
- `running-scripts/`: localnet bootstrap scripts and helper commands
- `docs/`: setup guides, tutorials, and project planning docs
- `tests/`: Python tests for the subnet template scaffolding
- `verify/`: message-signing and verification helpers

## Current Validator Flow

The validator currently performs a simple three-step loop:

1. Ask miners for a Playwright-style Python test script.
2. Run the script against the clean fixture app on `localhost:8080`.
3. Run the same script against the mutant fixture app on `localhost:8081`.

If the script passes on the clean app and fails on the mutant app, the miner receives a positive score.

## Quick Start

1. Create a Python environment and install the subnet package:

   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -U pip
   pip install -e .
   ```

2. Install the validator's browser-test dependencies:

   ```bash
   pip install pytest-playwright playwright
   playwright install --with-deps chromium
   ```

3. Build and run the local fixture apps:

   ```bash
   docker build -t proven-reference ./docker/reference
   docker build -t proven-mutant ./docker/mutant
   docker run -d --name proven-reference -p 127.0.0.1:8080:80 proven-reference
   docker run -d --name proven-mutant -p 127.0.0.1:8081:80 proven-mutant
   ```

4. Follow the environment-specific setup guide:

   - Localnet: [`docs/setup/localnet.md`](./docs/setup/localnet.md)
   - Testnet: [`docs/setup/testnet.md`](./docs/setup/testnet.md)
   - Mainnet: [`docs/setup/mainnet.md`](./docs/setup/mainnet.md)

## VPS Setup

Use this flow on a fresh Ubuntu VPS.

### 1. Install base packages

```bash
sudo apt update
sudo apt install -y git curl tmux jq docker.io python3 python3-venv python3-pip build-essential

curl https://sh.rustup.rs -sSf | sh -s -- -y
source "$HOME/.cargo/env"

sudo systemctl enable --now docker
sudo usermod -aG docker $USER
newgrp docker
```

### 2. Clone the repo

```bash
git clone https://github.com/TheoJustin/proven-todo.git
cd proven-todo/proven-subnet
```

### 3. Create the Python environment

```bash
python3 -m venv .venv
source .venv/bin/activate

pip install -U pip setuptools wheel
pip install "bittensor[torch]"
pip install -e .
pip install pytest-playwright playwright
playwright install --with-deps chromium
```

### 4. Import only the wallet material you need

Do not import the coldkey private key onto the VPS. Only provision `coldkeypub` and the hotkey required for that machine.

Validator VPS:

```bash
source .venv/bin/activate
btcli wallet regen-coldkeypub --wallet-name <WALLET_NAME> --ss58-address <COLDKEY_SS58>
btcli wallet regen-hotkey --wallet-name <WALLET_NAME> --hotkey <VALIDATOR_HOTKEY> --mnemonic "<validator hotkey words>" --use-password
```

Miner VPS:

```bash
source .venv/bin/activate
btcli wallet regen-coldkeypub --wallet-name <WALLET_NAME> --ss58-address <COLDKEY_SS58>
btcli wallet regen-hotkey --wallet-name <WALLET_NAME> --hotkey <MINER_HOTKEY> --mnemonic "<miner hotkey words>" --use-password
```

### 5. If this is the validator host, start the local fixture apps

```bash
cd ~/proven-todo/proven-subnet

docker build -t proven-reference ./docker/reference
docker build -t proven-mutant ./docker/mutant

docker run -d --restart unless-stopped --name proven-reference -p 127.0.0.1:8080:80 proven-reference
docker run -d --restart unless-stopped --name proven-mutant -p 127.0.0.1:8081:80 proven-mutant
```

Keep `8080` and `8081` private to the machine.

### 6. Open the axon port you need

Miner VPS:

```bash
sudo ufw allow 8091/tcp
```

Validator VPS:

```bash
sudo ufw allow 8092/tcp
```

## Run The Subnet

### Localnet

Start the miner:

```bash
python neurons/miner.py \
  --netuid 2 \
  --subtensor.network local \
  --wallet.name test-red-miner \
  --wallet.hotkey default \
  --axon.port 8091 \
  --logging.debug
```

Start the validator:

```bash
python neurons/validator.py \
  --netuid 2 \
  --subtensor.network local \
  --wallet.name test-validator \
  --wallet.hotkey default \
  --axon.port 8092 \
  --logging.debug
```

You can also use the helper scripts:

```bash
./running-scripts/07_run_miner.sh
./running-scripts/08_run_validator.sh
```

### Testnet

Start the miner:

```bash
python neurons/miner.py \
  --netuid <NETUID> \
  --subtensor.network test \
  --wallet.name <WALLET_NAME> \
  --wallet.hotkey <MINER_HOTKEY> \
  --axon.port 8091 \
  --axon.external_ip <VPS_PUBLIC_IP> \
  --axon.external_port 8091 \
  --logging.debug
```

Start the validator:

```bash
python neurons/validator.py \
  --netuid <NETUID> \
  --subtensor.network test \
  --wallet.name <WALLET_NAME> \
  --wallet.hotkey <VALIDATOR_HOTKEY> \
  --axon.port 8092 \
  --axon.external_ip <VPS_PUBLIC_IP> \
  --axon.external_port 8092 \
  --logging.debug
```

Before starting the validator, make sure the fixture apps are running locally on the validator host:

```bash
docker build -t proven-reference ./docker/reference
docker build -t proven-mutant ./docker/mutant
docker run -d --name proven-reference -p 127.0.0.1:8080:80 proven-reference
docker run -d --name proven-mutant -p 127.0.0.1:8081:80 proven-mutant
```

Run the miner inside `tmux`:

```bash
tmux new -d -s proven-miner 'python neurons/miner.py \
  --netuid <NETUID> \
  --subtensor.network test \
  --wallet.name <WALLET_NAME> \
  --wallet.hotkey <MINER_HOTKEY> \
  --axon.port 8091 \
  --axon.external_ip <VPS_PUBLIC_IP> \
  --axon.external_port 8091 \
  --logging.debug'
```

Run the validator inside `tmux`:

```bash
tmux new -d -s proven-validator 'python neurons/validator.py \
  --netuid <NETUID> \
  --subtensor.network test \
  --wallet.name <WALLET_NAME> \
  --wallet.hotkey <VALIDATOR_HOTKEY> \
  --axon.port 8092 \
  --axon.external_ip <VPS_PUBLIC_IP> \
  --axon.external_port 8092 \
  --logging.debug'
```

Check the running sessions:

```bash
tmux ls
docker ps
```

## Documentation

- Docs index: [`docs/README.md`](./docs/README.md)
- Localnet bootstrap scripts: [`running-scripts/README.md`](./running-scripts/README.md)
- Docker fixtures: [`docker/README.md`](./docker/README.md)
- Subnet spec template: [`docs/project/subnet-spec.md`](./docs/project/subnet-spec.md)
- Project roadmap: [`docs/project/roadmap.md`](./docs/project/roadmap.md)
- Minimum compute reference: [`min_compute.yml`](./min_compute.yml)

## Operational Notes

- The validator depends on local fixture apps and Playwright tooling that are not fully captured by `requirements.txt`.
- Miners and validators should use separate hotkeys.
- Coldkey private material should not live on a miner or validator VPS.
- Keep ports `8080` and `8081` private to the validator host unless you intentionally want them exposed.

## License

This repository is licensed under the MIT License. See [`LICENSE`](./LICENSE).
