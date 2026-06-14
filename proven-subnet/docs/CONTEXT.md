# Proven Glossary (CONTEXT.md)

Shared terminology for the Verification Funnel. Referenced by the PRD and ADRs.

- **Feature Area** — a single, named slice of the Reference app a miner is asked
  to test exhaustively in an epoch (e.g. `willify_homepage`). Defined in
  `verification/feature_areas.py`.
- **Selector Manifest** — behaviour-first hints broadcast to miners so they test
  behaviour instead of mining selectors: a list of elements, each with
  `selector`, `role`, `accessible_name`, `attributes`, and `state`. Built by
  `verification/selector_manifest.py`.
- **Static Gate** — Stage 1. Cheap AST + ruff (E9,F) screen that rejects
  malformed, banned-call, and happy-path/tautology scripts before any container
  runs. `verification/static_gate.py`.
- **Reference Gate** — Stage 2. The script is run against the clean Reference
  app; it must pass 100% (`P_clean = 1`) or it scores 0 (false-positive guard).
- **Tautology Trap / Blunt Killer** — a mutant with the Feature Area's elements
  blanked. Run after the Reference Gate: a script that still *passes* asserts
  nothing real ("happy-path ghost") and is forced to `P_clean = 0`.
- **Mutant Horde** — Stage 3. The admitted mutants the miner's script is run
  against; a "kill" is a test failure on a mutant.
- **Mutation Engine** — seeded, deterministic fault injector that produces
  mutants from the Reference source. `verification/mutation.py`.
- **Operator** — one declarative mutation (rename/remove attribute, swap text,
  rewrite href, remove element) applied to a known anchor.
- **Golden Oracle Suite** — the validator's private, exhaustive ground-truth
  test for a Feature Area. `verification/oracles/`.
- **Oracle Admission** — keep a candidate mutant only if the oracle passes on the
  reference and fails on the candidate. `verification/oracle.py`.
- **Equivalent Mutant** — a mutation that does not change observable behaviour;
  the oracle still passes, so it is dropped (never counted in `N_mut`).
- **Scoring** — `S_i = P_clean × (α · K_i / N_mut) × E_i`.
  - `P_clean` — 1 if the script passes the Reference Gate (and the Trap), else 0.
  - `K_i` — mutants killed by miner *i*; `N_mut` — admitted mutants this epoch.
  - `E_i` — efficiency in [0,1]: 1.0 within a soft time budget, decaying toward a
    floor at the hard timeout; a hard penalty applies when DOM probing is
    detected. `verification/efficiency.py`.
  - `α` — scoring coefficient, fixed at 1.0 and **cosmetic**; it is NOT
    `neuron.moving_average_alpha`.
- **Weight transform** — `to_weights` applies a steep-but-smooth map (`S_i^4`)
  before the existing EMA so the best miner dominates without destabilising Yuma
  consensus. `verification/weighting.py`.
- **First-to-Chain** — exact-copy AST fingerprinting credits the first submitter;
  later duplicates score 0. `verification/plagiarism.py`.
- **Probing** — inspecting/crawling the DOM instead of using supplied selectors;
  a red flag once a manifest exists, penalised via `E_i`.
  `verification/probing.py`.
