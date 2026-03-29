# Proven Subnet Specification

This document is a project-owned template for writing the actual Proven subnet spec. It is intentionally lightweight so the repo has a single place to capture the current design.

## Problem Statement

Describe the verification problem the subnet solves and why a decentralized market is useful.

## Miner Interface

- Input synapse fields
- Expected output format
- Runtime constraints
- Failure handling

## Validator Responsibilities

- Task generation
- Execution environment
- Scoring and normalization
- Weight-setting cadence

## Execution Environment

- Docker fixtures or sandbox images
- Playwright and browser dependencies
- Port usage and network boundaries
- Timeout and resource limits

## Scoring Model

- Clean-pass requirement
- Mutant detection criteria
- Latency penalties or bonuses
- Anti-gaming and abuse resistance

## Security Model

- Key-handling assumptions
- Coldkey vs hotkey boundaries
- VPS/network exposure rules
- Data retention and logging policy

## Operations

- Localnet workflow
- Testnet rollout plan
- Mainnet readiness checklist
- Monitoring and incident response

## Open Questions

- What should become dynamic vs hardcoded?
- How many fixture apps and mutants should exist in production?
- What minimum validator hardware is required?
