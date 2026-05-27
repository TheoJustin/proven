def compute_score(
    p_clean, kills: int, n_mut: int, e_i: float, alpha: float = 1.0
) -> float:
    """Return miner score: alpha * (kills/n_mut) * e_i, gated by p_clean.

    alpha is the scoring coefficient (default 1.0); it is NOT neuron.moving_average_alpha.
    p_clean is a binary gate — any truthy value passes through unchanged; 0/False returns 0.0.
    """
    if not p_clean:
        return 0.0
    if n_mut <= 0:
        return 0.0
    return alpha * (kills / n_mut) * e_i
