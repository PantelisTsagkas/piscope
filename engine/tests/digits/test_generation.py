import hashlib
from pathlib import Path

import numpy as np
import pytest
from numpy.typing import NDArray

from piscope_engine.digits import generation
from piscope_engine.digits.build import (
    build_dataset,
    first_mismatch,
    iter_digits_from_text,
    verify_against_text,
)
from piscope_engine.digits.generation import chudnovsky_digits, gauss_legendre_digits
from piscope_engine.digits.store import DigitStore
from piscope_engine.errors import GenerationError, VerificationError

from engine_support import FIXTURES, REFERENCE_FIRST_MILLION_SHA256

REFERENCE_FILE = FIXTURES / "pi_first_10000_decimals.txt"


def test_chudnovsky_matches_published_digits(reference_10k: NDArray[np.uint8]) -> None:
    np.testing.assert_array_equal(chudnovsky_digits(10_000), reference_10k)


def test_gauss_legendre_matches_published_digits(reference_10k: NDArray[np.uint8]) -> None:
    np.testing.assert_array_equal(gauss_legendre_digits(10_000), reference_10k)


@pytest.mark.parametrize("digits", [1, 2, 13, 14, 15, 100, 777, 4_321])
def test_every_prefix_length_is_truncated_not_rounded(
    digits: int, reference_10k: NDArray[np.uint8]
) -> None:
    # e.g. 3 decimals must be 141 (truncated), not 142 (rounded from 3.14159).
    np.testing.assert_array_equal(chudnovsky_digits(digits), reference_10k[:digits])
    np.testing.assert_array_equal(gauss_legendre_digits(digits), reference_10k[:digits])


@pytest.mark.parametrize("guard", [16, 32, 100])
def test_result_does_not_depend_on_guard_digits(
    guard: int, reference_10k: NDArray[np.uint8]
) -> None:
    np.testing.assert_array_equal(chudnovsky_digits(2_000, guard), reference_10k[:2_000])


def test_first_million_matches_published_checksum() -> None:
    digits = chudnovsky_digits(1_000_000)
    assert digits.dtype == np.uint8
    assert digits.size == 1_000_000
    assert hashlib.sha256(digits.tobytes()).hexdigest() == REFERENCE_FIRST_MILLION_SHA256


@pytest.mark.parametrize("digits", [0, -1])
def test_invalid_digit_count(digits: int) -> None:
    with pytest.raises(ValueError, match="digits must be"):
        chudnovsky_digits(digits)
    with pytest.raises(ValueError, match="digits must be"):
        gauss_legendre_digits(digits)


def test_too_few_guard_digits_rejected() -> None:
    with pytest.raises(ValueError, match="guard_digits"):
        chudnovsky_digits(10, guard_digits=2)


def test_ambiguous_guard_digits_are_rejected() -> None:
    class FakeInteger:
        def __init__(self, text: str) -> None:
            self.text = text

        def digits(self, base: int) -> str:
            assert base == 10
            return self.text

    # A value whose guard digits are all 9 could round up into the kept digits.
    scaled = FakeInteger("314159" + "9" * 20)
    with pytest.raises(GenerationError, match="ambiguous"):
        generation._scaled_pi_to_digits(scaled, 5, 20)
    with pytest.raises(GenerationError, match="shape"):
        generation._scaled_pi_to_digits(FakeInteger("27182" + "5" * 20), 5, 20)


def test_first_mismatch() -> None:
    left = np.array([1, 4, 1, 5], dtype=np.uint8)
    assert first_mismatch(left, left.copy()) is None
    assert first_mismatch(left, np.array([1, 4, 2, 5], dtype=np.uint8)) == 3


def test_build_dataset_records_provenance(tmp_path: Path) -> None:
    manifest = build_dataset(
        tmp_path,
        2_500,
        chunk_size=1_000,
        reference_file=REFERENCE_FILE,
        reference_source="test fixture",
    )
    assert manifest.total_digits == 2_500
    assert manifest.generator["algorithm"] == "chudnovsky-binary-splitting"
    assert [v.method for v in manifest.verifications] == ["gauss-legendre", "published-reference"]
    assert manifest.verifications[0].digits_compared == 2_500
    assert manifest.verifications[1].digits_compared == 2_500
    assert manifest.has_partial_chunk
    assert DigitStore(tmp_path).get_text(1, 15) == "141592653589793"


def test_build_dataset_expands_incrementally(
    tmp_path: Path, reference_10k: NDArray[np.uint8]
) -> None:
    build_dataset(tmp_path, 2_000, chunk_size=1_000)
    first_chunk = tmp_path / "chunk-000000.bin"
    stamp = first_chunk.stat().st_mtime_ns
    build_dataset(tmp_path, 5_000, chunk_size=1_000)
    store = DigitStore(tmp_path)
    assert store.total_digits == 5_000
    assert first_chunk.stat().st_mtime_ns == stamp
    np.testing.assert_array_equal(store.get_range(1, 5_000), reference_10k[:5_000])


def test_build_refuses_when_algorithms_disagree(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def wrong(digits: int, guard_digits: int = 64) -> NDArray[np.uint8]:
        result = gauss_legendre_digits(digits, guard_digits)
        result[41] = (result[41] + 1) % 10
        return result

    monkeypatch.setattr("piscope_engine.digits.build.gauss_legendre_digits", wrong)
    with pytest.raises(VerificationError, match="position 42"):
        build_dataset(tmp_path, 500)
    assert not list(tmp_path.iterdir())


def test_reference_mismatch_is_reported(tmp_path: Path, reference_10k: NDArray[np.uint8]) -> None:
    wrong = reference_10k[:200].copy()
    wrong[99] = (wrong[99] + 1) % 10
    with pytest.raises(VerificationError, match="position 100"):
        verify_against_text(wrong, REFERENCE_FILE, "fixture")


def test_text_reader_accepts_prefix_and_whitespace(tmp_path: Path) -> None:
    path = tmp_path / "pi.txt"
    path.write_text("3.14159 26535\n89793\n")
    digits = np.concatenate(list(iter_digits_from_text(path)))
    assert "".join(str(d) for d in digits) == "141592653589793"


def test_text_reader_rejects_garbage(tmp_path: Path) -> None:
    path = tmp_path / "pi.txt"
    path.write_text("3.1415x9")
    with pytest.raises(VerificationError, match="non-digit"):
        list(iter_digits_from_text(path))
