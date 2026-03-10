# Proven: The Decentralized Verification Layer

## A Bittensor Subnet for Spec-Driven Software Assurance

**By:** Theo Justin Amantha, Christopher Hardy Gunawan, Roderich Cavine Chow

---

# Overview

As AI-generated code floods the software ecosystem, the bottleneck in development has shifted from **creation to verification**.

**Proven** is a **Bittensor Subnet designed to automate high-assurance software testing.**
Unlike existing coding subnets that focus on **code synthesis**, Proven focuses on **analysis and verification**.

We are building a **decentralized marketplace for software verification** where:

* **Miners act as adversarial QA engineers**
* They generate **end-to-end (E2E) test suites**
* Tests are derived from **public specifications**

The goal is to create **trustless software verification at scale**.

---

# Architecture

Proven provides the economic layer for **Audit-as-a-Service**, enabling verification of software **without exposing private source code**.

## Core Components

### Synthetic Spec Engine

Validators utilize a **local open-weight LLM** to dynamically generate:

* novel specifications
* user stories
* edge-case scenarios

This ensures miners cannot memorize test patterns.

---

### Execution Sandboxing

Validators maintain a pool of **pre-warmed Docker containers** using the Playwright image:

```
mcr.microsoft.com/playwright:v1.40.0
```

Execution environment design:

```
+----------------------+
|  Validator Node      |
|                      |
|  Spec Generation     |
|        │             |
|        ▼             |
|  Test Execution      |
|        │             |
+--------│-------------+
         │
         ▼
+----------------------+
| Docker Network       |
|                      |
| Test Container       |
| (Playwright)         |
|                      |
| Mutated Target App   |
+----------------------+
```

The **test container and mutated application** communicate via an **isolated Docker bridge network** using internal DNS.

---

### Proof of Intelligence

The network verifies miner quality through **Black-Box Mutation Testing**.

Validators intentionally **inject faults into applications**, then evaluate how well miner-generated tests detect them.

The better the tests detect failures, the higher the miner score.

---

# Network Participants

## Miners (Software Detectives)

Miners generate automated E2E test suites.

Optimization goals:

* zero false positives
* high mutation kill ratio
* low execution latency

### Miner Pipeline

1. **Spec Analysis**

   Decompose the specification into a **Requirement Tree**

2. **Strategy Generation**

   Apply testing heuristics:

   * Boundary Value Analysis
   * Equivalence Partitioning
   * Negative testing
   * Edge-case discovery

3. **Code Synthesis**

   Generate **self-contained Playwright Python scripts**

Example test structure:

```
from playwright.sync_api import sync_playwright

def test_login():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()

        page.goto("http://app/login")
        page.fill("#username", "test")
        page.fill("#password", "password")
        page.click("#submit")

        assert page.locator("#dashboard").is_visible()

        browser.close()
```

---

## Validators (The Verification Funnel)

Running browser tests against multiple mutated apps is **computationally expensive**.

To manage resources, validators apply a **multi-stage filtering funnel**.

### Stage 1 — Static Gate

The submitted test suite is checked for:

* syntax errors
* parsing errors
* invalid dependencies

---

### Stage 2 — Reference Gate

The Playwright suite runs against the **reference implementation**.

Requirements:

* **100% tests must pass**
* ensures **no false positives**

---

### Stage 3 — Mutation Testing

Validators spawn **20+ mutated application containers**.

Example mutations include:

* logic inversion
* boundary removal
* API response changes
* validation bypass

Tests are evaluated based on **how many mutants they detect**.

---

# Scoring Mechanism

Miner rewards (TAO emissions) follow the scoring formula:

```
S_i = P_clean × (α × (K_i / N_mut)) × E_i
```

### Variables

| Variable | Description                                                           |
| -------- | --------------------------------------------------------------------- |
| P_clean  | Binary switch (1 if tests pass reference implementation, 0 otherwise) |
| K_i      | Number of mutants killed by miner i                                   |
| N_mut    | Total number of generated mutants                                     |
| E_i      | Efficiency factor based on execution latency                          |

This scoring ensures:

* correct tests
* high detection power
* fast execution

---

# Go-To-Market Strategy

## Phase 1 — Network Bootstrapping (Months 1–3)

Launch **Dual Mining** scripts allowing idle compute from other networks to generate Proven test suites.

Goal:

* bootstrap miner participation
* build initial training data

---

## Phase 2 — Web3 & SaaS Adoption (Months 4–6)

Partnerships with:

* DeFi protocols
* SaaS startups
* Web3 security teams

Release a GitHub CI tool:

```
Proven-E2E-check
```

Developers can add:

```
- uses: proven-network/e2e-check
```

to automatically verify their applications.

---

## Phase 3 — Enterprise Expansion (6+ Months)

Launch a **fiat-based API service** allowing Web2 companies to access Proven verification.

Target customers:

* fintech platforms
* enterprise SaaS
* large development teams

---

# Vision

Proven transforms software verification into a **decentralized intelligence market**.

Instead of trusting a single QA provider, developers gain:

* distributed adversarial testing
* trustless verification
* scalable security auditing

---

# Repository Structure

```
proven/
│
├── miners/
│   ├── test_generation/
│   └── playwright_templates/
│
├── validators/
│   ├── spec_engine/
│   ├── mutation_engine/
│   └── execution_runner/
│
├── docker/
│   └── sandbox_environment/
│
├── scoring/
│   └── tao_rewards.py
│
└── docs/
    └── subnet_spec.md
```

---

# License

MIT License

---

# Authors

Theo Justin Amantha
Christopher Hardy Gunawan
Roderich Cavine Chow

---

# Built For

Bittensor Subnet Ideathon
