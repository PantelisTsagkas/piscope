"""Single-digit frequency analysis."""

from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

from piscope_engine.digits.store import DigitStore

type CountArray = NDArray[np.int64]


@dataclass(frozen=True, slots=True)
class DigitFrequency:
    """Frequency of one digit within an analysed range.

    Attributes:
        digit: The digit, 0-9.
        count: Observed number of occurrences.
        relative_frequency: ``count / sample_size``.
        expected_count: Count expected under a uniform model, ``sample_size / 10``.
        deviation: ``count - expected_count``.
        standardized_deviation: Deviation divided by the binomial standard deviation
            ``sqrt(n * 0.1 * 0.9)``; roughly a z-score for this digit taken alone.
    """

    digit: int
    count: int
    relative_frequency: float
    expected_count: float
    deviation: float
    standardized_deviation: float


@dataclass(frozen=True, slots=True)
class FrequencyAnalysis:
    """Digit frequencies for a range of positions.

    Attributes:
        range_start: First analysed position (1-based, inclusive).
        range_end: Last analysed position (inclusive).
        sample_size: Number of digits analysed.
        digits: One entry per digit 0-9, in order.
        most_frequent: Digits sharing the highest count.
        least_frequent: Digits sharing the lowest count.
    """

    range_start: int
    range_end: int
    sample_size: int
    digits: list[DigitFrequency]
    most_frequent: list[int]
    least_frequent: list[int]

    @property
    def counts(self) -> CountArray:
        """Observed counts for digits 0-9 as an array."""
        return np.array([entry.count for entry in self.digits], dtype=np.int64)


def count_digits(store: DigitStore, start: int, count: int) -> CountArray:
    """Count how often each digit 0-9 occurs in a range, streaming chunk by chunk.

    Raises:
        PositionOutOfRangeError: If the range is outside the dataset.
    """
    totals = np.zeros(10, dtype=np.int64)
    for _, block in store.iter_blocks(start, count):
        totals += np.bincount(block, minlength=10)
    return totals


def summarize_counts(counts: CountArray, range_start: int) -> FrequencyAnalysis:
    """Build a :class:`FrequencyAnalysis` from ten digit counts.

    Raises:
        ValueError: If ``counts`` does not have exactly ten non-negative entries or
            sums to zero.
    """
    if counts.shape != (10,) or int(counts.min()) < 0:
        raise ValueError("counts must hold ten non-negative values")
    sample_size = int(counts.sum())
    if sample_size == 0:
        raise ValueError("cannot analyse an empty range")
    expected = sample_size / 10
    spread = (sample_size * 0.1 * 0.9) ** 0.5
    entries = [
        DigitFrequency(
            digit=digit,
            count=int(counts[digit]),
            relative_frequency=int(counts[digit]) / sample_size,
            expected_count=expected,
            deviation=int(counts[digit]) - expected,
            standardized_deviation=(int(counts[digit]) - expected) / spread,
        )
        for digit in range(10)
    ]
    highest = int(counts.max())
    lowest = int(counts.min())
    return FrequencyAnalysis(
        range_start=range_start,
        range_end=range_start + sample_size - 1,
        sample_size=sample_size,
        digits=entries,
        most_frequent=[digit for digit in range(10) if counts[digit] == highest],
        least_frequent=[digit for digit in range(10) if counts[digit] == lowest],
    )


def analyze_frequency(store: DigitStore, start: int, count: int) -> FrequencyAnalysis:
    """Count digits in ``count`` positions from ``start`` and summarise them.

    Raises:
        PositionOutOfRangeError: If the range is outside the dataset.
        ValueError: If ``count`` is zero.
    """
    return summarize_counts(count_digits(store, start, count), start)
