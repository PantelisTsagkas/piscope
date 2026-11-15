import json
from pathlib import Path

import numpy as np
import pytest
from numpy.typing import NDArray

from piscope_engine.digits.manifest import MANIFEST_FILENAME
from piscope_engine.digits.store import DigitStore, digits_to_text
from piscope_engine.errors import (
    DatasetIntegrityError,
    DatasetNotFoundError,
    PositionOutOfRangeError,
)

from engine_support import make_store


def test_dataset_shape(synthetic_store: DigitStore) -> None:
    assert synthetic_store.total_digits == 1_050
    assert synthetic_store.chunk_size == 100
    assert synthetic_store.chunk_count == 11
    assert synthetic_store.manifest.has_partial_chunk
    assert synthetic_store.manifest.chunks[-1].digit_count == 50


def test_position_one_is_first_decimal_of_pi(pi_store: DigitStore) -> None:
    # pi = 3.14159..., so position 1 is 1 (not the integer digit 3).
    assert pi_store.get_digit(1) == 1
    assert pi_store.get_text(1, 10) == "1415926535"


def test_get_digit_matches_source_everywhere(
    synthetic_store: DigitStore, synthetic_digits: NDArray[np.uint8]
) -> None:
    for position in range(1, synthetic_store.total_digits + 1):
        assert synthetic_store.get_digit(position) == synthetic_digits[position - 1]


@pytest.mark.parametrize(
    ("start", "count"),
    [
        (1, 1),
        (1, 100),
        (100, 2),  # last digit of chunk 0 and first of chunk 1
        (101, 100),  # exactly chunk 1
        (95, 310),  # spans four chunks
        (1, 1_050),  # everything, including the partial chunk
        (1_050, 1),  # last digit
        (500, 0),  # empty
    ],
)
def test_get_range_across_chunk_boundaries(
    synthetic_store: DigitStore, synthetic_digits: NDArray[np.uint8], start: int, count: int
) -> None:
    result = synthetic_store.get_range(start, count)
    assert result.dtype == np.uint8
    np.testing.assert_array_equal(result, synthetic_digits[start - 1 : start - 1 + count])


@pytest.mark.parametrize(("start", "count"), [(0, 1), (-5, 2), (1_051, 1), (1_050, 2), (1, 1_051)])
def test_out_of_range_requests_are_rejected(
    synthetic_store: DigitStore, start: int, count: int
) -> None:
    with pytest.raises(PositionOutOfRangeError):
        synthetic_store.get_range(start, count)


def test_out_of_range_digit_is_rejected(synthetic_store: DigitStore) -> None:
    with pytest.raises(PositionOutOfRangeError):
        synthetic_store.get_digit(0)
    with pytest.raises(PositionOutOfRangeError):
        synthetic_store.get_digit(1_051)


def test_negative_count_is_rejected(synthetic_store: DigitStore) -> None:
    with pytest.raises(ValueError, match="count"):
        synthetic_store.get_range(1, -1)


def test_iter_blocks_reassembles_range(
    synthetic_store: DigitStore, synthetic_digits: NDArray[np.uint8]
) -> None:
    blocks = list(synthetic_store.iter_blocks(51, 900, block_size=64))
    assert [first for first, _ in blocks][:3] == [51, 115, 179]
    joined = np.concatenate([digits for _, digits in blocks])
    np.testing.assert_array_equal(joined, synthetic_digits[50:950])


def test_chunk_cache_is_bounded(tmp_path: Path, synthetic_digits: NDArray[np.uint8]) -> None:
    store = make_store(tmp_path / "d", synthetic_digits, chunk_size=100)
    bounded = DigitStore(store.data_dir, max_open_chunks=2)
    np.testing.assert_array_equal(bounded.get_range(1, 1_050), synthetic_digits)
    assert len(bounded._open_chunks) <= 2


def test_chunk_view_is_read_only(synthetic_store: DigitStore) -> None:
    view = synthetic_store.chunk_view(0)
    with pytest.raises(ValueError, match="read-only"):
        view[0] = 5


def test_digits_to_text() -> None:
    assert digits_to_text(np.array([3, 1, 4, 0, 9], dtype=np.uint8)) == "31409"


def test_missing_dataset(tmp_path: Path) -> None:
    with pytest.raises(DatasetNotFoundError):
        DigitStore(tmp_path)


def test_missing_chunk_file_is_detected(synthetic_store: DigitStore) -> None:
    (synthetic_store.data_dir / "chunk-000003.bin").unlink()
    with pytest.raises(DatasetIntegrityError, match="missing"):
        DigitStore(synthetic_store.data_dir)


def test_truncated_chunk_file_is_detected(synthetic_store: DigitStore) -> None:
    path = synthetic_store.data_dir / "chunk-000002.bin"
    path.write_bytes(path.read_bytes()[:-1])
    with pytest.raises(DatasetIntegrityError, match="bytes"):
        DigitStore(synthetic_store.data_dir)


def test_checksums_pass_on_clean_dataset(synthetic_store: DigitStore) -> None:
    synthetic_store.verify_checksums()


def test_corrupted_digit_fails_checksum(synthetic_store: DigitStore) -> None:
    path = synthetic_store.data_dir / "chunk-000004.bin"
    content = bytearray(path.read_bytes())
    content[10] = (content[10] + 1) % 10
    path.write_bytes(bytes(content))
    reopened = DigitStore(synthetic_store.data_dir)  # size still matches
    with pytest.raises(DatasetIntegrityError, match="checksum mismatch"):
        reopened.verify_checksums()


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("total_digits", 2_000, "total_digits"),
        ("format_version", 99, "unsupported"),
        ("base", 16, "base-10"),
    ],
)
def test_inconsistent_manifest_is_rejected(
    synthetic_store: DigitStore, field: str, value: int, message: str
) -> None:
    path = synthetic_store.data_dir / MANIFEST_FILENAME
    raw = json.loads(path.read_text())
    raw[field] = value
    path.write_text(json.dumps(raw))
    with pytest.raises(DatasetIntegrityError, match=message):
        DigitStore(synthetic_store.data_dir)


def test_partial_chunk_must_be_flagged(synthetic_store: DigitStore) -> None:
    path = synthetic_store.data_dir / MANIFEST_FILENAME
    raw = json.loads(path.read_text())
    raw["chunks"][-1]["complete"] = True  # 50 of 100 digits is not complete
    path.write_text(json.dumps(raw))
    with pytest.raises(DatasetIntegrityError, match="complete"):
        DigitStore(synthetic_store.data_dir)


def test_malformed_manifest_is_rejected(synthetic_store: DigitStore) -> None:
    (synthetic_store.data_dir / MANIFEST_FILENAME).write_text("{not json")
    with pytest.raises(DatasetIntegrityError, match="malformed"):
        DigitStore(synthetic_store.data_dir)
