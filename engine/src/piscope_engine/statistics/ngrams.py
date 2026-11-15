"""N-gram (digit sequence of fixed length) counting."""

from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

type DigitArray = NDArray[np.uint8]
type CountArray = NDArray[np.int64]

MAX_NGRAM_LENGTH = 7


@dataclass(frozen=True, slots=True)
class NgramSummary:
    """Descriptive summary of n-gram counts.

    Attributes:
        length: The n in n-gram.
        overlapping: Whether windows overlap (step 1) or are disjoint (step n).
        windows: Number of n-grams counted.
        possible: Number of distinct n-grams that exist, ``10**length``.
        observed_distinct: How many of them occur at least once.
        expected_count: ``windows / possible``.
        counts: Count for every n-gram; index ``k`` is the n-gram whose digits spell
            ``k`` zero-padded to ``length`` digits.
    """

    length: int
    overlapping: bool
    windows: int
    possible: int
    observed_distinct: int
    expected_count: float
    counts: CountArray


def ngram_label(value: int, length: int) -> str:
    """Return the digits of an n-gram index, e.g. ``ngram_label(7, 3) == "007"``."""
    return f"{value:0{length}d}"


def count_ngrams(digits: DigitArray, length: int, overlapping: bool = True) -> CountArray:
    """Count every n-gram of the given length.

    Args:
        digits: Digit sequence.
        length: N-gram length, 1 to 7.
        overlapping: True counts a window at every position (``len - length + 1``
            windows). False cuts the sequence into disjoint blocks and ignores any
            leftover digits at the end.

    Returns:
        An array of ``10**length`` counts indexed by the n-gram's numeric value.

    Raises:
        ValueError: If ``length`` is outside 1 to 7.
    """
    if not 1 <= length <= MAX_NGRAM_LENGTH:
        raise ValueError(f"n-gram length must be between 1 and {MAX_NGRAM_LENGTH}")
    possible = 10**length
    windows = digits.size - length + 1
    if windows <= 0:
        return np.zeros(possible, dtype=np.int64)
    values = np.zeros(windows, dtype=np.int64)
    for offset in range(length):
        values *= 10
        values += digits[offset : offset + windows]
    if not overlapping:
        values = values[::length]
    return np.bincount(values, minlength=possible).astype(np.int64)


def summarize_ngrams(digits: DigitArray, length: int, overlapping: bool = True) -> NgramSummary:
    """Count n-grams and describe the result.

    Raises:
        ValueError: If ``length`` is invalid or the sequence is shorter than ``length``.
    """
    counts = count_ngrams(digits, length, overlapping)
    windows = int(counts.sum())
    if windows == 0:
        raise ValueError(f"need at least {length} digits to count {length}-grams")
    possible = 10**length
    return NgramSummary(
        length=length,
        overlapping=overlapping,
        windows=windows,
        possible=possible,
        observed_distinct=int(np.count_nonzero(counts)),
        expected_count=windows / possible,
        counts=counts,
    )
