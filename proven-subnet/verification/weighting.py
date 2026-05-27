import numpy as np


def to_weights(scores, p: float = 4.0) -> np.ndarray:
    s = np.clip(np.asarray(scores, dtype=float), 0, None)
    powered = s ** p
    total = powered.sum()
    if total <= 0:
        return np.zeros_like(s)
    return powered / total
