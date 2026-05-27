def compute_score(p_clean, kills: int, n_mut: int, e_i: float, alpha: float = 1.0) -> float:
    if not p_clean:
        return 0.0
    if n_mut <= 0:
        return 0.0
    return float(p_clean) * alpha * (kills / n_mut) * e_i
