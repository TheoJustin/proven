# Proven: Local Subnet Setup Guide

This guide walks you through setting up a local Bittensor subnet for Proven, allowing you to develop and test without spending real TAO.

---

## Overview

You will:

1. Clone the subnet template (boilerplate)
2. Run a local Subtensor blockchain
3. Create wallets
4. Create your subnet
5. Register miner & validator
6. Run nodes
7. Integrate Proven logic

---

## Prerequisites

- Python 3.10+
- Docker
- Rust & Cargo
- Bittensor CLI (btcli)

---

## 1. Clone Subnet Template

    git clone https://github.com/opentensor/bittensor-subnet-template.git
    cd bittensor-subnet-template

Install dependencies:

    pip install -r requirements.txt

Key directories:

    /neurons/miner.py
    /neurons/validator.py
    /subnet/

---

## 2. Run Local Subtensor (Blockchain)

Build and start a local node:

    cargo build --release
    ./target/release/subtensor --dev

Expected endpoint:

    ws://127.0.0.1:9945

Verify connection:

    btcli status

---

## 3. Create Wallets

Create coldkey:

    btcli w new_coldkey

Create hotkey:

    btcli w new_hotkey

Verify wallets:

    btcli w list

---

## 4. Create Proven Subnet

    btcli subnet create

After success:

- You will receive a netuid (usually 1 for local development)

Verify:

    btcli subnet list

---

## 5. Register Miner & Validator

Register miner:

    btcli subnet register --netuid 1

Register validator:

    btcli subnet register --netuid 1

Verify registration:

    btcli metagraph --netuid 1

---

## 6. Run Nodes

Start miner:

    python neurons/miner.py

Start validator:

    python neurons/validator.py

### Expected Behavior

- Validator sends challenges  
- Miner receives tasks  
- Miner generates responses  
- Validator evaluates results and assigns scores  

---

## 7. Integrate Proven Logic

### Miner Responsibilities

- Parse incoming specification  
- Generate test strategy  
- Generate Playwright test cases  
- Submit results back to validator  

### Validator Responsibilities

- Generate synthetic specifications  
- Apply mutation testing  
- Execute tests inside Docker containers  
- Score miner outputs  

### System Flow

    Validator → Miner → Test Generation → Mutation → Score → Reward

---

## 8. Local Simulation & Debugging

- Run multiple miner instances  
- Measure generation latency  
- Stress test validator pipeline  
- Validate scoring fairness  
- Log errors and edge cases  

---

# TODO: Deploy Proven Subnet to Bittensor Testnet

## 1. Subnet Specification Finalization

- [ ] Finalize subnet whitepaper and technical specification  
- [ ] Define miner input/output interface format  
- [ ] Define validator challenge generation protocol  
- [ ] Finalize scoring function parameters  
- [ ] Document architecture in /docs/subnet_spec.md  

---

## 2. Core Validator Implementation

- [ ] Synthetic Spec Engine  
- [ ] Requirement Tree generator  
- [ ] Mutation Engine  
- [ ] Execution Runner (Playwright + Docker)  
- [ ] Scoring pipeline  
- [ ] TAO reward logic  

---

## 3. Miner Framework

- [ ] Spec parser  
- [ ] Test strategy generator  
- [ ] Playwright test generator  
- [ ] Latency optimization  
- [ ] Submission protocol  

---

## 4. Mutation Testing Infrastructure

- [ ] Mutation library  
- [ ] Mutant container generation  
- [ ] Mutation orchestration  
- [ ] Kill detection logic  
- [ ] Performance benchmarks  

---

## 5. Docker Execution Environment

- [ ] Base Playwright image  
- [ ] Container prewarming  
- [ ] Lifecycle management  
- [ ] Timeout safeguards  
- [ ] Network isolation  

---

## 6. Subnet Integration

- [ ] Subnet class implementation  
- [ ] Miner registration logic  
- [ ] Validator registration logic  
- [ ] Weight updates  
- [ ] Metagraph integration  

---

## 7. Local Simulation Environment

- [ ] Simulate miners  
- [ ] Simulate validator scoring  
- [ ] Stress test pipeline  
- [ ] Benchmark fairness  

---

## 8. Testnet Deployment

- [ ] Register subnet  
- [ ] Deploy validator nodes  
- [ ] Launch miner nodes  
- [ ] Validate scoring pipeline  
- [ ] Monitor compute load  
- [ ] Tune parameters  

---

## 9. Observability & Monitoring

- [ ] Logging  
- [ ] Performance metrics  
- [ ] Mutation analytics  
- [ ] Dashboards  
- [ ] Alerting  

---

## 10. Developer Tooling

- [ ] Proven CLI  
- [ ] GitHub Action (E2E check)  
- [ ] Miner SDK  
- [ ] Validator setup scripts  
- [ ] Documentation  

---

## 11. Security Hardening

- [ ] Sandbox execution for miner code  
- [ ] Prevent malicious test payloads  
- [ ] Container resource limits (CPU/memory)  
- [ ] Validator DoS protection  
- [ ] Adversarial testing  

---

## 12. Testnet Validation Phase

- [ ] Run subnet with early miners  
- [ ] Evaluate scoring behavior  
- [ ] Optimize mutation difficulty  
- [ ] Reduce validator compute cost  
- [ ] Collect miner feedback  

---

## 13. Mainnet Preparation

- [ ] Finalize tokenomics  
- [ ] Prepare subnet proposal  
- [ ] Complete technical documentation  
- [ ] Create validator onboarding guide  
- [ ] Submit for Bittensor governance vote  

---

## Notes

- Always validate locally before deploying to testnet  
- Validator compute cost is the primary bottleneck  
- Miner latency directly impacts competitiveness  
- Mutation testing depth must balance accuracy vs cost  

---