"""Helpers shared by API tests."""

from pathlib import Path

import numpy as np
from numpy.typing import NDArray

from piscope_engine.digits.manifest import VerificationRecord
from piscope_engine.digits.writer import write_dataset

ENGINE_FIXTURES = Path(__file__).parents[2] / "engine" / "tests" / "fixtures"


def load_reference_text() -> str:
    """First 10,000 published decimals of pi as a string."""
    return (ENGINE_FIXTURES / "pi_first_10000_decimals.txt").read_text(encoding="ascii").strip()


def text_to_digits(text: str) -> NDArray[np.uint8]:
    """Convert a string of ASCII digits to stored digit values."""
    return (np.frombuffer(text.encode("ascii"), dtype=np.uint8) - ord("0")).astype(np.uint8)


def write_test_dataset(data_dir: Path, text: str, chunk_size: int) -> None:
    """Store a digit string as a dataset."""
    write_dataset(
        data_dir,
        [text_to_digits(text)],
        generator={"algorithm": "published-fixture"},
        verifications=[
            VerificationRecord(method="fixture", digits_compared=len(text), detail="test fixture")
        ],
        chunk_size=chunk_size,
    )


def naive_positions(text: str, pattern: str, start: int = 1, end: int | None = None) -> list[int]:
    """Oracle: 1-based start positions of matches lying fully inside [start, end]."""
    last = len(text) if end is None else end
    return [
        position
        for position in range(start, last - len(pattern) + 2)
        if text[position - 1 : position - 1 + len(pattern)] == pattern
    ]
