# Proven Documentation

This directory contains the working docs for the Proven subnet.

## Setup Guides

- [`setup/localnet.md`](./setup/localnet.md): run the subnet against a local chain
- [`setup/testnet.md`](./setup/testnet.md): register and run on Bittensor testnet
- [`setup/mainnet.md`](./setup/mainnet.md): mainnet-oriented flow and cautions

## Tutorials

- [`tutorials/streaming/README.md`](./tutorials/streaming/README.md): upstream streaming tutorial kept with its example files

## Project Docs

- [`project/subnet-spec.md`](./project/subnet-spec.md): the Proven subnet spec
- [`project/roadmap.md`](./project/roadmap.md): current roadmap and workstreams
- [`CONTEXT.md`](./CONTEXT.md): glossary for the Verification Funnel

## Architecture Decisions

- [`adr/0001-dynamic-runtime-mutation.md`](./adr/0001-dynamic-runtime-mutation.md): dynamic mutants + Golden Oracle
- [`adr/0002-per-validator-seeding.md`](./adr/0002-per-validator-seeding.md): independent per-epoch seeding
- [`adr/0003-selector-manifest-crawl.md`](./adr/0003-selector-manifest-crawl.md): feature-flagged manifest crawl
- [`adr/0004-steep-smooth-weighting.md`](./adr/0004-steep-smooth-weighting.md): steep-but-smooth weighting

## Try It

- [`../scripts/dry_run_funnel.py`](../scripts/dry_run_funnel.py): run the full funnel locally (no chain) and print `S_i`

## Related Directories

- [`../running-scripts/README.md`](../running-scripts/README.md): localnet helper scripts
- [`../docker/README.md`](../docker/README.md): reference and mutant fixture apps
