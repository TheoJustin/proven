# Proven Roadmap

This document tracks the work needed to move Proven from a local prototype toward a stable subnet deployment.

## Current Baseline

The repo already contains:

- a miner entrypoint that returns Playwright-style Python tests
- a validator entrypoint that runs those tests against reference and mutant fixtures
- Docker fixtures for a clean app and a mutant app
- localnet helper scripts and setup docs

## Near-Term Priorities

### Subnet Specification

- [ ] Finalize the written subnet specification
- [ ] Define the miner request and response contract
- [ ] Define validator scoring inputs and outputs
- [ ] Capture architecture in [`subnet-spec.md`](./subnet-spec.md)

### Validator Maturity

- [ ] Replace hardcoded tasks with generated challenge inputs
- [ ] Expand beyond a single mutant fixture
- [ ] Add stronger timeout, sandbox, and dependency controls
- [ ] Make scoring transparent and reproducible

### Miner Maturity

- [ ] Replace the hardcoded response with actual generation logic
- [ ] Add strategy selection for edge cases and negative tests
- [ ] Optimize for latency and deterministic outputs

## Deployment Workstreams

### Localnet

- [ ] Keep the local bootstrap flow working end-to-end
- [ ] Add smoke tests for reference and mutant fixture availability
- [ ] Document common failure modes

### Testnet

- [ ] Register the subnet and required wallets
- [ ] Bring up a validator with isolated hotkey handling
- [ ] Bring up one or more miners
- [ ] Verify weight-setting and permit behavior

### Mainnet Readiness

- [ ] Harden key management and VPS procedures
- [ ] Replace local-only assumptions in the validator
- [ ] Add monitoring, logging, and restart supervision
- [ ] Audit bundled assets, dependencies, and licensing

## Tooling And Docs

- [ ] Improve operator docs for coldkey and hotkey separation
- [ ] Add VPS deployment automation
- [ ] Add a contributor-facing architecture guide
- [ ] Add a lightweight smoke-test command for fixture validation

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
