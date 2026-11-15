"""Shared fixtures for engine tests."""

from pathlib import Path

import numpy as np
import pytest
from numpy.typing import NDArray

from piscope_engine.digits.store import DigitStore

from engine_support import FIXTURES, make_store, text_to_digits


@pytest.fixture(scope="session")
def reference_10k() -> NDArray[np.uint8]:
    """First 10,000 decimals of pi from a published source."""
    text = (FIXTURES / "pi_first_10000_decimals.txt").read_text(encoding="ascii").strip()
    assert len(text) == 10_000
    return text_to_digits(text)


@pytest.fixture
def synthetic_digits() -> NDArray[np.uint8]:
    """1,050 reproducible pseudo-random digits (not pi)."""
    return np.random.default_rng(7).integers(0, 10, size=1_050, dtype=np.uint8)


@pytest.fixture
def synthetic_store(tmp_path: Path, synthetic_digits: NDArray[np.uint8]) -> DigitStore:
    """Synthetic dataset split into chunks of 100 digits (10 full chunks + 1 partial)."""
    return make_store(tmp_path / "data", synthetic_digits, chunk_size=100)


@pytest.fixture
def pi_store(tmp_path: Path, reference_10k: NDArray[np.uint8]) -> DigitStore:
    """First 10,000 published decimals of pi in chunks of 1,000."""
    return make_store(tmp_path / "pi", reference_10k, chunk_size=1_000)
