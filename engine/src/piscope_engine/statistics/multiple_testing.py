"""Multiple-testing corrections for families of p-values."""

from typing import Literal

import numpy as np

type Correction = Literal["holm", "bonferroni"]


def adjust_p_values(p_values: list[float], method: Correction = "holm") -> list[float]:
    """Adjust p-values to control the family-wise error rate.

    Args:
        p_values: Raw p-values of one family of tests.
        method: ``bonferroni`` multiplies every p-value by the number of tests.
            ``holm`` (Holm-Bonferroni step-down) is uniformly at least as powerful and
            valid under any dependence between the tests.

    Returns:
        Adjusted p-values in the original order, each capped at 1.

    Raises:
        ValueError: If a p-value is outside [0, 1] or the method is unknown.
    """
    if any(not 0.0 <= value <= 1.0 for value in p_values):
        raise ValueError("p-values must lie in [0, 1]")
    count = len(p_values)
    if count == 0:
        return []
    if method == "bonferroni":
        return [min(1.0, value * count) for value in p_values]
    if method == "holm":
        order = np.argsort(p_values, kind="stable")
        adjusted = [0.0] * count
        running_maximum = 0.0
        for rank, index in enumerate(order.tolist()):
            candidate = min(1.0, p_values[index] * (count - rank))
            running_maximum = max(running_maximum, candidate)
            adjusted[index] = running_maximum
        return adjusted
    raise ValueError(f"unknown correction method: {method}")
