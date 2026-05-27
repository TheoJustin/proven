"""Pure, framework-independent verification modules for the Proven validator.

Modules here must not import bittensor/torch/playwright at module load, so they
stay unit-testable in isolation. The bittensor-coupled neuron code imports from
this package; this package never imports from `template`/`neurons`.
"""
