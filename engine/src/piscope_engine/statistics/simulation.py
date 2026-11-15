"""Reproducible simulated random digit sequences."""

from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

type DigitArray = NDArray[np.uint8]

BIT_GENERATOR = "PCG64"


@dataclass(frozen=True, slots=True)
class RandomSource:
    """Everything needed to regenerate a simulated sequence.

    Attributes:
        seed: Seed given to ``numpy.random.SeedSequence``.
        bit_generator: NumPy bit generator name.
        numpy_version: NumPy version that produced the digits. NumPy does not guarantee
            identical streams across versions for ``Generator`` methods.
        method: How digits are drawn from the generator.
    """

    seed: int
    bit_generator: str
    numpy_version: str
    method: str


def describe_source(seed: int) -> RandomSource:
    """Return the reproducibility record for a seed."""
    return RandomSource(
        seed=seed,
        bit_generator=BIT_GENERATOR,
        numpy_version=np.__version__,
        method="Generator(PCG64(SeedSequence(seed).spawn(k)[i])).integers(0, 10, dtype=uint8)",
    )


def random_digit_sequences(length: int, seed: int, count: int = 1) -> list[DigitArray]:
    """Generate ``count`` independent pseudo-random digit sequences.

    Each sequence uses its own child of ``SeedSequence(seed)``, so sequence ``i`` is the
    same whatever ``count`` is requested.

    Args:
        length: Digits per sequence.
        seed: Non-negative integer seed.
        count: Number of sequences.

    Raises:
        ValueError: If ``length`` or ``count`` is below 1 or ``seed`` is negative.
    """
    if length < 1 or count < 1:
        raise ValueError("length and count must be >= 1")
    if seed < 0:
        raise ValueError("seed must be >= 0")
    children = np.random.SeedSequence(seed).spawn(count)
    return [
        np.random.Generator(np.random.PCG64(child)).integers(0, 10, size=length, dtype=np.uint8)
        for child in children
    ]
