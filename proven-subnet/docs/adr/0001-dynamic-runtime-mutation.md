# ADR-0001: Dynamic runtime mutation with a Golden Oracle

## Status
Accepted.

## Context
A single static, hand-authored mutant is trivially gameable: a miner can
hardcode the assertions that kill it. The proposal calls for 20+ dynamically
generated faults so the "kill" logic cannot be precomputed.

## Decision
Generate mutants at runtime each epoch from the fixed Reference app source via a
seeded Mutation Engine (`verification/mutation.py`). Admit a candidate only if a
private Golden Oracle Suite passes on the reference and fails on the candidate
(`verification/oracle.py`), so equivalent/unkillable mutants never inflate
`N_mut`. All miners in an epoch are scored against the identical admitted set.

## Consequences
- Hardcoding specific kills is infeasible; thoroughness (higher `K_i/N_mut`) pays.
- `N_mut` and the kill ceiling are honest, so scores are comparable across miners.
- The validator must serve many app variants per epoch — see ADR on serving in
  the README; the stdlib overlay server keeps this cheap (only mutated files are
  materialised; the ~80 MB asset bundle is shared).
- Mutation operators are paired 1:1 with oracle assertions so admission is
  deterministic for the bootstrapping Willify feature areas.
