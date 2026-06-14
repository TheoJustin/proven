# Proven Subnet Specification

Spec-driven software verification on Bittensor. Miners act as adversarial QA
engineers; validators score test suites by Black-Box Mutation Testing. See
[`CONTEXT.md`](../CONTEXT.md) for terminology and [`../adr/`](../adr) for design
decisions.

## Problem Statement

The cost of generating code has collapsed; the cost of trusting it has not.
Proven creates a decentralized market where miners are paid to produce E2E test
suites that catch real defects, scored on their ability to kill deliberately
injected faults — without exposing private source (tests are written against
specifications, not code).

## Miner Interface

- **Input** (`E2ETestingSynapse`): `spec_type`, `requirement_content`,
  `target_url`, `feature_area`, and a structured `selector_manifest`
  (`elements: [{selector, role, accessible_name, attributes, state}]`).
- **Output**: `playwright_script` — a single self-contained pytest-playwright
  file reading `TARGET_URL` from the environment.
- **Runtime constraints**: must import Playwright; no subprocess/sockets/eval/
  filesystem/destructive-OS; use supplied selectors (DOM crawling is penalised).
- **Failure handling**: missing/invalid scripts score 0; the AI miner falls back
  to a deterministic script when generation is unavailable.

## Validator Responsibilities

- **Task generation**: pick a Feature Area; build the Selector Manifest (live
  crawl is feature-flagged, ADR-0003); broadcast the spec.
- **Mutant generation**: seeded per epoch (ADR-0002); admit only oracle-killable
  mutants (ADR-0001); all miners face the identical set.
- **Scoring/normalization**: `S_i = P_clean × (α·K_i/N_mut) × E_i`, then the
  steep-but-smooth weight transform (ADR-0004) feeding the EMA.
- **Weight-setting**: via `BaseValidatorNeuron.set_weights` on the existing
  cadence.

## Execution Environment

- Reference app: Docker/nginx fixture on `127.0.0.1:8080`.
- Mutants + Blunt Killer: served per epoch via stdlib HTTP on ephemeral
  localhost ports (overlay server shares the reference asset bundle; only mutated
  files are materialised).
- Miner scripts and the Golden Oracle Suite run via `pytest --browser chromium`
  with a per-run `TARGET_URL`. Hard timeout per run; `E_i` measured on the
  Reference Gate run.

## Scoring Model

- **Clean-pass requirement**: `P_clean = 0` if the script fails the Reference
  Gate (false positive) or passes the Tautology Trap (happy-path ghost).
- **Mutant detection**: `K_i` = admitted mutants the script fails on; `N_mut` =
  admitted mutants.
- **Latency**: `E_i = 1.0` within a soft budget, decaying to a floor at the hard
  timeout; hard multiplicative penalty when DOM probing is detected.
- **Anti-gaming**: Static Gate (tautologies/banned calls), Tautology Trap
  (ghosts), dynamic seeded mutants (hardcoding), Oracle admission (equivalent
  mutants), First-to-Chain AST fingerprinting (plagiarism), probing penalty.

## Security Model

- Coldkey private material never on miner/validator VPS; miners and validators
  use separate hotkeys.
- Reference/mutant ports bound to localhost.
- Miner code runs through the Static Gate before execution; full sandbox/network
  isolation is a documented follow-on (not yet implemented).

## Operations

- Localnet: [`setup/localnet.md`](../setup/localnet.md); helper scripts in
  [`../../running-scripts/`](../../running-scripts).
- Testnet/Mainnet: [`setup/testnet.md`](../setup/testnet.md),
  [`setup/mainnet.md`](../setup/mainnet.md).
- Local funnel smoke test (no chain):
  [`../../scripts/dry_run_funnel.py`](../../scripts/dry_run_funnel.py).
- CI runs the pure `verification/` modules + funnel integration test
  (`.github/workflows/verification.yml`).

## Open Questions

- How many Feature Areas / mutants per epoch in production, and how to tune
  difficulty to network performance?
- When to introduce the Synthetic Spec Engine (LLM-generated specs/apps) and the
  hardened sandbox (isolated Docker bridge network)?
- Minimum validator hardware once the browser horde scales beyond one area.
