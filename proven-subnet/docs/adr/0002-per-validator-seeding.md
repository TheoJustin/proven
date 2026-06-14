# ADR-0002: Independent per-validator, per-epoch seeding

## Status
Accepted.

## Context
If the Spec and Mutant set were predictable or shared, miners could precompute
kills and validators could collude by pre-sharing answers.

## Decision
Each validator picks its Feature Area and generates its Mutant set from a secret
seed chosen independently each epoch. In the current implementation the seed is
`secrets.randbits(32)` drawn per `forward()` (`neurons/validator.py`); the same
seed drives `generate_mutants` so the per-epoch set is internally consistent
(all miners face the identical set) while being unpredictable across epochs.

## Consequences
- Miners cannot precompute which mutants will appear.
- Collusion via pre-shared answers is infeasible.
- Mutant sets are not reproducible across epochs by design; reproduce a specific
  set for debugging by passing a fixed seed to `generate_mutants` directly.
