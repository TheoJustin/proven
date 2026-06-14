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

Each epoch the validator runs the Verification Funnel:

1. Build a behaviour-first **Selector Manifest** for a Feature Area (homepage)
   and broadcast the spec to miners.
2. Dynamically generate a seeded **Mutant Horde** + a **Blunt Killer** from the
   clean Reference app (`localhost:8080`), and **admit** only mutants the private
   Golden Oracle Suite can kill (drops equivalent mutants).
3. For each miner script: **Static Gate** → **Reference Gate** (must pass the
   clean app) → **Tautology Trap** (a script that still passes with the feature
   area blanked is a happy-path ghost → `P_clean = 0`) → **Mutant Horde** (count
   kills `K_i`).
4. Score `S_i = P_clean × (α · K_i / N_mut) × E_i`, apply the steep-but-smooth
   weight transform, and update on-chain weights.

Mutants are generated and served dynamically (stdlib HTTP, per epoch), so the
old static `docker/mutant` fixture on `localhost:8081` is no longer required by
the funnel; it is kept only as a hand-authored reference example. See
[`docs/CONTEXT.md`](./docs/CONTEXT.md) for terminology and `docs/adr/` for the
design decisions. Run [`scripts/dry_run_funnel.py`](./scripts/dry_run_funnel.py)
to exercise the whole funnel locally without a chain.

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

3. Configure AI generation for the miner if you want live test synthesis.

   The miner reads Azure OpenAI settings from environment variables. Keep the
   key out of source control.

   PowerShell:

   ```powershell
   $env:AZURE_OPENAI_TARGET_URI="https://<resource>.cognitiveservices.azure.com/openai/deployments/<deployment>/chat/completions?api-version=2025-01-01-preview"
   $env:AZURE_OPENAI_API_KEY="<rotated-api-key>"
   ```

   Bash:

   ```bash
   export AZURE_OPENAI_TARGET_URI="https://<resource>.cognitiveservices.azure.com/openai/deployments/<deployment>/chat/completions?api-version=2025-01-01-preview"
   export AZURE_OPENAI_API_KEY="<rotated-api-key>"
   ```

   You can also configure the pieces separately:

   ```bash
   export AZURE_OPENAI_ENDPOINT="https://<resource>.cognitiveservices.azure.com/"
   export AZURE_OPENAI_DEPLOYMENT="<deployment>"
   export AZURE_OPENAI_API_VERSION="2025-01-01-preview"
   export AZURE_OPENAI_API_KEY="<rotated-api-key>"
   ```

   Optional controls:

   ```bash
   export AZURE_OPENAI_TEMPERATURE="0.2"
   export AZURE_OPENAI_MAX_COMPLETION_TOKENS="4096"
   ```

   If these variables are missing or the AI call fails, the miner falls back to
   the deterministic Willify prototype test.

4. Build and run the local fixture apps:

   ```bash
   docker build -t proven-reference ./docker/reference
   docker build -t proven-mutant ./docker/mutant
   docker run -d --name proven-reference -p 127.0.0.1:8080:80 proven-reference
   docker run -d --name proven-mutant -p 127.0.0.1:8081:80 proven-mutant
   ```

5. Follow the environment-specific setup guide:

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
pip install openai
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

## Production Readiness

Proven is a **testnet-ready prototype**, not yet safe for mainnet. The scoring
mechanism is complete and unit-tested, and the chain scaffolding is the standard
Bittensor template, but several load-bearing production requirements are not yet
built (most are documented follow-ons in the proposal/roadmap).

**Solid today**

- Verification Funnel logic — Static Gate, `S_i = P_clean × (α·K_i/N_mut) × E_i`,
  efficiency, plagiarism, weighting — pure, deterministic, CI-tested.
- Anti-gaming — Tautology Trap, dynamic seeded mutants, Golden Oracle admission,
  AST plagiarism, DOM-probing penalty.
- Standard registration / metagraph sync / Yuma-safe `set_weights`.

**Mainnet blockers**

1. **Untrusted code execution is not sandboxed (critical).** The validator runs
   miner-submitted Python via `pytest` directly on the host, gated only by an AST
   Static Gate + a 60s timeout — no container isolation, egress control, or
   CPU/memory limits. The Static Gate is not a security boundary (e.g. a Playwright
   script can still navigate to arbitrary URLs). Mainnet needs the proposal's
   sandbox: ephemeral per-run containers on an isolated bridge network, no external
   egress, resource limits, and the hotkey kept out of the execution environment.
2. **Validator consensus stability is unproven.** Independent per-validator seeding
   (ADR-0002) means validators score miners on different tasks/mutants each epoch.
   The design assumes honest validators converge on similar *relative* rankings via
   the EMA, but per-epoch variance (small catalogue, modest `N_mut`, noisy localhost
   `E_i` timing) needs an empirical testnet phase measuring validator weight
   correlation (vtrust) before mainnet.
3. **Single fixed app → overfitting.** Only Willify (4 feature areas, a finite
   operator set). Miners will eventually memorise killable mutants. The Synthetic
   Spec Engine (LLM-generated specs/apps) is the intended fix and is not built.
4. **Scale / compute cost.** The Mutant Horde runs chromium sequentially per miner
   (`reference + blunt killer + N` runs each); no parallelism or caching. Needs
   batching/concurrency to be viable at full miner counts.
5. **Operational hardening.** No supervision (tmux only), monitoring, metrics, or
   state backups.

`min_compute.yml` is a rough reference only — the validator does **not** require a
GPU, and the bundled miner uses a hosted LLM API (GPU needed only if you self-host
a model).

## License

This repository is licensed under the MIT License. See [`LICENSE`](./LICENSE).
