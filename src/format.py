def usd(v: float) -> str:
    """3 significant figures with a K/M/B suffix; whole dollars from $1 to $999."""
    sign, v = ("-" if v < 0 else ""), abs(v)
    if v < 1:
        return f"{sign}${v:.3g}"
    rounded = float(f"{v:.3g}")
    for div, suffix in ((1e9, "B"), (1e6, "M"), (1e3, "K")):
        if rounded >= div:
            return f"{sign}${rounded / div:.3g}{suffix}"
    return f"{sign}${v:.0f}"
