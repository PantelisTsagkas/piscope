from pathlib import Path
from typing import Any

import numpy as np
import pytest
from numpy.typing import NDArray

from piscope_engine.digits.store import DigitStore
from piscope_engine.digits.writer import write_dataset
from piscope_engine.errors import DatasetIntegrityError

from engine_support import SYNTHETIC_GENERATOR, SYNTHETIC_VERIFICATION


def _write(data_dir: Path, blocks: list[NDArray[np.uint8]], chunk_size: int = 100) -> None:
    write_dataset(
        data_dir,
        blocks,
        generator=SYNTHETIC_GENERATOR,
        verifications=SYNTHETIC_VERIFICATION,
        chunk_size=chunk_size,
    )


def test_blocks_of_any_size_are_rechunked(
    tmp_path: Path, synthetic_digits: NDArray[np.uint8]
) -> None:
    blocks = [synthetic_digits[:33], synthetic_digits[33:420], synthetic_digits[420:]]
    _write(tmp_path, blocks)
    store = DigitStore(tmp_path)
    assert [chunk.digit_count for chunk in store.manifest.chunks] == [100] * 10 + [50]
    np.testing.assert_array_equal(store.get_range(1, 1_050), synthetic_digits)


def test_expansion_keeps_validated_chunks_untouched(
    tmp_path: Path, synthetic_digits: NDArray[np.uint8]
) -> None:
    _write(tmp_path, [synthetic_digits[:350]])
    before = DigitStore(tmp_path).manifest
    stamps = {c.filename: (tmp_path / c.filename).stat().st_mtime_ns for c in before.chunks}

    _write(tmp_path, [synthetic_digits])
    store = DigitStore(tmp_path)

    assert store.total_digits == 1_050
    assert store.manifest.created_at == before.created_at
    for chunk in before.chunks[:3]:  # the three complete chunks are not rewritten
        assert (tmp_path / chunk.filename).stat().st_mtime_ns == stamps[chunk.filename]
        assert store.manifest.chunks[chunk.index].sha256 == chunk.sha256
    assert store.manifest.chunks[3].complete  # previously partial chunk is now full
    np.testing.assert_array_equal(store.get_range(1, 1_050), synthetic_digits)
    store.verify_checksums()


def test_expansion_with_different_digits_is_refused(
    tmp_path: Path, synthetic_digits: NDArray[np.uint8]
) -> None:
    _write(tmp_path, [synthetic_digits[:300]])
    tampered = synthetic_digits.copy()
    tampered[150] = (tampered[150] + 1) % 10
    with pytest.raises(DatasetIntegrityError, match="disagree"):
        _write(tmp_path, [tampered])
    assert DigitStore(tmp_path).total_digits == 300


def test_expansion_checks_partial_chunk_prefix(
    tmp_path: Path, synthetic_digits: NDArray[np.uint8]
) -> None:
    _write(tmp_path, [synthetic_digits[:250]])
    tampered = synthetic_digits.copy()
    tampered[220] = (tampered[220] + 1) % 10
    with pytest.raises(DatasetIntegrityError, match="disagree"):
        _write(tmp_path, [tampered])


def test_expansion_detects_corrupt_stored_chunk(
    tmp_path: Path, synthetic_digits: NDArray[np.uint8]
) -> None:
    _write(tmp_path, [synthetic_digits[:300]])
    path = tmp_path / "chunk-000001.bin"
    content = bytearray(path.read_bytes())
    content[0] = (content[0] + 1) % 10
    path.write_bytes(bytes(content))
    with pytest.raises(DatasetIntegrityError, match="fails its checksum"):
        _write(tmp_path, [synthetic_digits])


def test_shrinking_is_refused(tmp_path: Path, synthetic_digits: NDArray[np.uint8]) -> None:
    _write(tmp_path, [synthetic_digits])
    with pytest.raises(DatasetIntegrityError):
        _write(tmp_path, [synthetic_digits[:500]])
    assert DigitStore(tmp_path).total_digits == 1_050


def test_chunk_size_cannot_change(tmp_path: Path, synthetic_digits: NDArray[np.uint8]) -> None:
    _write(tmp_path, [synthetic_digits])
    with pytest.raises(DatasetIntegrityError, match="chunk_size"):
        _write(tmp_path, [synthetic_digits], chunk_size=200)


def test_non_digit_values_are_rejected(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="0-9"):
        _write(tmp_path, [np.array([1, 2, 10], dtype=np.uint8)])
    wrong_dtype: Any = [np.array([1, 2, 3], dtype=np.int64)]
    with pytest.raises(ValueError, match="uint8"):
        _write(tmp_path, wrong_dtype)


def test_empty_stream_is_rejected(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="empty"):
        _write(tmp_path, [])


def test_no_temp_files_left_behind(tmp_path: Path, synthetic_digits: NDArray[np.uint8]) -> None:
    _write(tmp_path, [synthetic_digits])
    assert not list(tmp_path.glob("*.tmp"))


def test_failed_expansion_leaves_dataset_readable(
    tmp_path: Path, synthetic_digits: NDArray[np.uint8]
) -> None:
    _write(tmp_path, [synthetic_digits[:250]])  # chunk 2 is partial (50 digits)
    bad_later_block = np.array([1, 2, 77], dtype=np.uint8)
    with pytest.raises(ValueError, match="0-9"):
        _write(tmp_path, [synthetic_digits[:400], bad_later_block])
    store = DigitStore(tmp_path)  # must still open: the partial chunk was not replaced
    assert store.total_digits == 250
    store.verify_checksums()
    np.testing.assert_array_equal(store.get_range(1, 250), synthetic_digits[:250])
    assert not list(tmp_path.glob("*.tmp"))
