def efficiency(
    exec_time: float,
    soft_budget: float,
    hard_timeout: float,
    probing: bool = False,
    floor: float = 0.1,
    probing_penalty: float = 0.1,
) -> float:
    if exec_time <= soft_budget:
        base = 1.0
    elif exec_time >= hard_timeout:
        base = floor
    else:
        frac = (exec_time - soft_budget) / (hard_timeout - soft_budget)
        base = 1.0 - frac * (1.0 - floor)
    if probing:
        base *= probing_penalty
    return max(0.0, min(1.0, base))
