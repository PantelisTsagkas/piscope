"""Digit concentration across consecutive windows of the sequence."""

from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

type DigitArray = NDArray[np.uint8]


@dataclass(frozen=True, slots=True)
class WindowAnalysis:
    """Digit counts in equal consecutive windows.

    Attributes:
        window_size: Digits per window.
        window_count: Number of complete windows analysed.
        first_position: 1-based position of the first analysed digit.
        counts: Array of shape ``(window_count, 10)``: count of each digit per window.
        standardized: Same shape: ``(count - n/10) / sqrt(n * 0.09)``, a per-cell z-score.
        expected_cells_beyond_two: Cells expected to have ``|z| > 2`` by chance alone,
            about 4.55% of all cells.
        cells_beyond_two: Cells that actually have ``|z| > 2``.
        cells_beyond_three: Cells that actually have ``|z| > 3``.
        max_abs_z: Largest absolute z-score.
    """

    window_size: int
    window_count: int
    first_position: int
    counts: NDArray[np.int64]
    standardized: NDArray[np.float64]
    expected_cells_beyond_two: float
    cells_beyond_two: int
    cells_beyond_three: int
    max_abs_z: float


def analyze_windows(
    digits: DigitArray, window_count: int, first_position: int = 1
) -> WindowAnalysis:
    """Split a sequence into ``window_count`` equal windows and count digits in each.

    Leftover digits at the end that do not fill a window are ignored.

    Raises:
        ValueError: If ``window_count`` is below 1 or exceeds the number of digits.
    """
    if window_count < 1:
        raise ValueError("window_count must be >= 1")
    window_size = int(digits.size) // window_count
    if window_size < 1:
        raise ValueError("more windows than digits")
    used = digits[: window_size * window_count].reshape(window_count, window_size)
    counts = np.zeros((window_count, 10), dtype=np.int64)
    for digit in range(10):
        counts[:, digit] = np.count_nonzero(used == digit, axis=1)
    spread = np.sqrt(window_size * 0.1 * 0.9)
    standardized = (counts - window_size / 10) / spread
    cells = window_count * 10
    return WindowAnalysis(
        window_size=window_size,
        window_count=window_count,
        first_position=first_position,
        counts=counts,
        standardized=standardized,
        expected_cells_beyond_two=cells * 0.0455,
        cells_beyond_two=int(np.count_nonzero(np.abs(standardized) > 2)),
        cells_beyond_three=int(np.count_nonzero(np.abs(standardized) > 3)),
        max_abs_z=float(np.abs(standardized).max()),
    )
