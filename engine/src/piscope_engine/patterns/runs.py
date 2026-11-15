"""Runs of repeated digits (e.g. ``999999``)."""

from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

type DigitArray = NDArray[np.uint8]


@dataclass(frozen=True, slots=True)
class DigitRun:
    """A maximal block of one repeated digit.

    Attributes:
        digit: The repeated digit.
        length: Number of repetitions.
        position: 1-based position of the first digit of the run.
    """

    digit: int
    length: int
    position: int


@dataclass(frozen=True, slots=True)
class RunLengthRow:
    """How many maximal runs of one length were seen, against a random model.

    Attributes:
        length: Run length.
        observed: Number of maximal runs of exactly this length.
        expected: Number expected for independent uniform digits,
            approximately ``n * 0.9**2 * 0.1**(length - 1)`` (edge effects ignored).
    """

    length: int
    observed: int
    expected: float


def find_runs(digits: DigitArray, first_position: int = 1) -> list[DigitRun]:
    """Split a sequence into its maximal runs of repeated digits, in order.

    Args:
        digits: Digit sequence.
        first_position: 1-based position of ``digits[0]`` in the dataset.
    """
    if digits.size == 0:
        return []
    boundaries = np.flatnonzero(digits[1:] != digits[:-1]) + 1
    starts = np.concatenate(([0], boundaries))
    lengths = np.diff(np.concatenate((starts, [digits.size])))
    return [
        DigitRun(digit=int(digits[start]), length=int(length), position=int(start) + first_position)
        for start, length in zip(starts.tolist(), lengths.tolist(), strict=True)
    ]


def longest_runs(digits: DigitArray, top: int = 10, first_position: int = 1) -> list[DigitRun]:
    """Return the ``top`` longest runs, longest first, earliest first among ties."""
    if top < 1:
        raise ValueError("top must be >= 1")
    if digits.size == 0:
        return []
    boundaries = np.flatnonzero(digits[1:] != digits[:-1]) + 1
    starts = np.concatenate(([0], boundaries))
    lengths = np.diff(np.concatenate((starts, [digits.size])))
    order = np.lexsort((starts, -lengths))[:top]
    return [
        DigitRun(
            digit=int(digits[starts[index]]),
            length=int(lengths[index]),
            position=int(starts[index]) + first_position,
        )
        for index in order.tolist()
    ]


def run_length_distribution(digits: DigitArray) -> list[RunLengthRow]:
    """Count maximal runs by length and give the count expected for random digits."""
    if digits.size == 0:
        return []
    boundaries = np.flatnonzero(digits[1:] != digits[:-1]) + 1
    starts = np.concatenate(([0], boundaries))
    lengths = np.diff(np.concatenate((starts, [digits.size])))
    observed = np.bincount(lengths)
    size = int(digits.size)
    return [
        RunLengthRow(
            length=length,
            observed=int(observed[length]),
            expected=size * 0.81 * 0.1 ** (length - 1),
        )
        for length in range(1, observed.size)
    ]
