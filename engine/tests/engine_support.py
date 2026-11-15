"""Helpers and constants shared by engine tests."""

from pathlib import Path

import numpy as np
from numpy.typing import NDArray

from piscope_engine.digits.manifest import VerificationRecord
from piscope_engine.digits.store import DigitStore
from piscope_engine.digits.writer import write_dataset

FIXTURES = Path(__file__).parent / "fixtures"

# Derived from a published digit file, not from this project's generator.
# See tests/fixtures/README.md for provenance.
REFERENCE_FIRST_MILLION_SHA256 = "344b0f42bd832f29a22d6b829af80e325c4fac22d88a1efb5e21b7a3632c1086"

SYNTHETIC_GENERATOR: dict[str, str | int] = {"algorithm": "synthetic-test-data", "seed": 7}
SYNTHETIC_VERIFICATION = [
    VerificationRecord(method="none", digits_compared=0, detail="synthetic test data")
]


def text_to_digits(text: str) -> NDArray[np.uint8]:
    """Convert a string of ASCII digits to stored digit values."""
    return (np.frombuffer(text.encode("ascii"), dtype=np.uint8) - ord("0")).astype(np.uint8)


def make_store(data_dir: Path, digits: NDArray[np.uint8], chunk_size: int) -> DigitStore:
    """Write digits as a dataset and open it."""
    write_dataset(
        data_dir,
        [digits],
        generator=SYNTHETIC_GENERATOR,
        verifications=SYNTHETIC_VERIFICATION,
        chunk_size=chunk_size,
    )
    return DigitStore(data_dir)
