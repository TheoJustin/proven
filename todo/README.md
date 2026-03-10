## TODO: Deploy Proven Subnet to Bittensor Testnet

Before launching Proven on the Bittensor testnet, the following milestones need to be completed.

### 1. Subnet Specification Finalization

* [ ] Finalize subnet whitepaper and technical specification
* [ ] Define miner input/output interface format
* [ ] Define validator challenge generation protocol
* [ ] Finalize scoring function parameters (α, efficiency decay, mutation counts)
* [ ] Document full architecture in `/docs/subnet_spec.md`

### 2. Core Validator Implementation

* [ ] Implement **Synthetic Spec Engine**
* [ ] Implement **Requirement Tree generator**
* [ ] Implement **Mutation Engine**
* [ ] Implement **Execution Runner** using Playwright containers
* [ ] Implement **Docker sandbox networking isolation**
* [ ] Implement **validator scoring pipeline**
* [ ] Implement **TAO reward emission logic**

### 3. Miner Framework

* [ ] Implement **Spec parser**
* [ ] Implement **test strategy generator**
* [ ] Implement **Playwright test generator**
* [ ] Optimize miner latency and parallel test generation
* [ ] Implement submission protocol to validator

### 4. Mutation Testing Infrastructure

* [ ] Build mutation library for common application faults
* [ ] Implement automatic mutant container generation
* [ ] Implement mutation orchestration (20+ mutated instances per run)
* [ ] Implement mutant kill detection logic
* [ ] Benchmark mutation runtime performance

### 5. Docker Execution Environment

* [ ] Create base Docker image using Playwright runtime
* [ ] Implement container pool pre-warming
* [ ] Implement container lifecycle management
* [ ] Implement execution timeout safeguards
* [ ] Implement network isolation between test runner and mutated apps

### 6. Subnet Integration

* [ ] Implement Bittensor subnet class
* [ ] Implement miner registration logic
* [ ] Implement validator registration logic
* [ ] Implement scoring weight updates
* [ ] Implement metagraph integration

### 7. Local Simulation Environment

* [ ] Create local subnet simulation environment
* [ ] Simulate miners submitting test suites
* [ ] Simulate validator mutation evaluation
* [ ] Stress test validator pipeline
* [ ] Benchmark scoring fairness

### 8. Testnet Deployment

* [ ] Register subnet on Bittensor testnet
* [ ] Deploy validator nodes
* [ ] Launch initial miner nodes
* [ ] Validate scoring pipeline
* [ ] Monitor validator compute load
* [ ] Tune mutation counts and scoring weights

### 9. Observability & Monitoring

* [ ] Implement logging for miner submissions
* [ ] Implement validator performance metrics
* [ ] Implement mutation kill analytics
* [ ] Implement network dashboards
* [ ] Set up alerting for validator failures

### 10. Developer Tooling

* [ ] Create **Proven CLI**
* [ ] Create **GitHub Action: Proven-E2E-check**
* [ ] Provide miner SDK
* [ ] Provide validator setup scripts
* [ ] Write full documentation

### 11. Security Hardening

* [ ] Sandbox validation for miner scripts
* [ ] Prevent malicious test execution
* [ ] Implement container resource limits
* [ ] Add validator DoS protection
* [ ] Perform adversarial testing

### 12. Testnet Validation Phase

* [ ] Run subnet with early miners
* [ ] Evaluate scoring behavior
* [ ] Evaluate mutation difficulty
* [ ] Optimize validator cost
* [ ] Collect miner feedback

### 13. Preparation for Mainnet Proposal

* [ ] Finalize subnet tokenomics
* [ ] Prepare subnet proposal submission
* [ ] Create technical documentation
* [ ] Create validator onboarding guide
* [ ] Submit subnet for Bittensor governance vote
