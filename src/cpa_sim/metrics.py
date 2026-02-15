# contains math for end-to-end metrics and analysis of per-stage metrics
# used for building objective functions to optimize for
# eg: pulse shape change (end to end), cost of components (per stage accumulation)


def placeholder_metric(x, y):
    """Example metric—replace or remove."""
    return abs(x - y)
