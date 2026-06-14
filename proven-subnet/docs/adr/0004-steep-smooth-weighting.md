# ADR-0004: Steep-but-smooth weighting (not literal winner-takes-all)

## Status
Accepted.

## Context
The proposal calls for a Winner-Takes-All or steeply tiered weighting before
Yuma Consensus to force continuous improvement. A literal winner-takes-all step
function is unstable near ties and can destabilise consensus.

## Decision
Apply a steep-but-smooth transform to per-epoch scores before the existing EMA:
`to_weights(s) = s^4 / Σ s^4` (`verification/weighting.py`), consumed by
`BaseValidatorNeuron.update_scores`. The scoring coefficient `α` in
`compute_score` is fixed at 1.0 and documented as cosmetic — distinct from
`neuron.moving_average_alpha`.

## Consequences
- The best miner receives the large majority of incentive without a hard cliff.
- Behaviour degrades gracefully near ties; consensus stays stable.
- The exponent `p` (default 4) is the single knob controlling steepness.
