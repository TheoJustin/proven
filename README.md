# [cite_start]Proven: The Decentralized Verification Layer [cite: 1]

[cite_start]**A Subnet Proposal for Spec-Driven Software Assurance** [cite: 2]

[cite_start]By: Theo Justin Amantha & Christopher Hardy Gunawan [cite: 3, 5]

## Overview
[cite_start]As AI-generated code floods the software ecosystem, the bottleneck in development has shifted from creation to verification[cite: 6]. [cite_start]Proven is a Bittensor Subnet designed to automate high-assurance software testing[cite: 7]. [cite_start]Unlike existing coding subnets that focus on synthesis, Proven focuses on analysis[cite: 8].

[cite_start]We are building a decentralized marketplace where miners act as adversarial QA engineers, generating exhaustive end-to-end (E2E) test suites based on public specifications[cite: 9]. 

## Architecture & How it Works
[cite_start]Proven provides the economic layer for "Audit-as-a-Service," enabling trustless verification of software without exposing private source code[cite: 11].

* [cite_start]**The Synthetic Spec Engine:** Validators utilize a local, open-weight LLM to dynamically generate novel, logically sound specifications and stories on the fly[cite: 167].
* [cite_start]**Execution Sandboxing:** Validators maintain a pool of pre-warmed Docker containers based on the official `mcr.microsoft.com/playwright:v1.40.0` image[cite: 54, 55, 56, 57, 58]. [cite_start]The execution container and the mutated target application are placed on an isolated Docker bridge network communicating via internal DNS[cite: 73, 74]. 
* [cite_start]**Proof of Intelligence:** The network validates via Black-Box Mutation Testing, a rigorous method where test suites are scored on their ability to detect deliberately injected faults in live applications[cite: 10].

## Network Participants

### [cite_start]Miners (Software Detectives) [cite: 35]
[cite_start]Miners must optimize for zero false positives, high kill ratios, and low latency[cite: 41]. Their pipeline involves:
* [cite_start]**Spec Analysis:** Decomposing the input Spec into a "Requirement Tree"[cite: 36].
* [cite_start]**Strategy Generation:** Using heuristics (Boundary Value Analysis, Equivalence Partitioning) to plan UI/API test cases[cite: 37].
* [cite_start]**Code Synthesis:** Writing self-contained executable Python Playwright automation scripts[cite: 38, 59].

### [cite_start]Validators (The Verification Funnel) [cite: 62]
[cite_start]Running multiple E2E browser tests against live mutated apps is computationally expensive[cite: 63]. [cite_start]To prevent overload, validators use a multi-stage funnel[cite: 64]:
* [cite_start]**Stage 1: The Static Gate:** The submitted test suite is linted to ensure it parses correctly and has zero syntax errors[cite: 65, 66].
* [cite_start]**Stage 2: The Reference Gate:** The Playwright suite is run against the Reference Implementation[cite: 67]. [cite_start]It must pass 100% of the tests (no false positives)[cite: 68].
* [cite_start]**Stage 3: Mutation Testing:** The Validator spins up 20+ mutated application containers[cite: 70]. [cite_start] This ensures expensive compute is only spent on viable QA candidates[cite: 71].

## Scoring Mechanism
[cite_start]The scoring function dictates TAO emissions and is calculated as follows[cite: 85, 145]:

[cite_start]$S_{i}=P_{clean}\times(\alpha\cdot\frac{K_{i}}{N_{mut}})\times E_{i}$ [cite: 87]

* [cite_start]$P_{clean}$: Binary Switch (1 if tests pass the Reference Implementation, 0 otherwise)[cite: 89].
* [cite_start]$K_{i}$: Number of Mutants killed by Miner i via successful test failure[cite: 90].
* [cite_start]$N_{mut}$: Total Mutants generated[cite: 91].
* [cite_start]$E_{i}$: Efficiency decay based on Playwright execution time[cite: 92].

## [cite_start]Go-To-Market Strategy [cite: 125]
* [cite_start]**Phase 1 (Months 1-3):** Bootstrapping via "Dual Mining" scripts allowing idle network GPU/CPU time to be routed toward Proven E2E test generation[cite: 126, 128].
* [cite_start]**Phase 2 (Months 4-6):** Partnering with Web3 DeFi protocols and SaaS startups[cite: 129, 130]. [cite_start]Releasing a GitHub Action `Proven-E2E-check` for seamless CI/CD integration[cite: 131].
* [cite_start]**Phase 3 (Months 6+):** Enterprise expansion by launching a fiat-facing API for Web2 companies[cite: 132, 133].