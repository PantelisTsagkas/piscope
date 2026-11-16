"""Chunk boundaries on real digits of pi at the production chunk size.

The other tests cross boundaries with small synthetic chunks. This one generates three
full 1,000,000 digit chunks, by expanding a one-chunk dataset, and compares the store and
the search against a flat scan of the concatenated chunk files.
"""

from pathlib import Path

import numpy as np
import pytest
from numpy.typing import NDArray

from piscope_engine.digits.build import build_dataset
from piscope_engine.digits.store import DigitStore, digits_to_text
from piscope_engine.search.sequence import search_sequence
from piscope_engine.statistics.frequency import count_digits

from engine_support import REFERENCE_FIRST_MILLION_SHA256

pytestmark = pytest.mark.slow

CHUNK = 1_000_000
TOTAL = 3 * CHUNK
BOUNDARIES = (CHUNK, 2 * CHUNK)


@pytest.fixture(scope="module")
def data_dir(tmp_path_factory: pytest.TempPathFactory) -> Path:
    path = tmp_path_factory.mktemp("real-chunks")
    build_dataset(path, CHUNK)
    first_chunk = path / "chunk-000000.bin"
    written_at = first_chunk.stat().st_mtime_ns
    manifest = build_dataset(path, TOTAL)
    # Expansion must recognise the stored chunk by checksum and leave the file alone.
    assert first_chunk.stat().st_mtime_ns == written_at
    assert manifest.chunks[0].sha256 == REFERENCE_FIRST_MILLION_SHA256
    return path


@pytest.fixture(scope="module")
def store(data_dir: Path) -> DigitStore:
    opened = DigitStore(data_dir)
    opened.verify_checksums()
    return opened


@pytest.fixture(scope="module")
def flat(data_dir: Path) -> bytes:
    """Every chunk file concatenated, read without the store. Byte values are 0-9."""
    return b"".join(path.read_bytes() for path in sorted(data_dir.glob("chunk-*.bin")))


def flat_positions(flat: bytes, pattern: str) -> list[int]:
    """1-based positions of every occurrence, overlaps included, by a plain scan."""
    needle = bytes(int(char) for char in pattern)
    found: list[int] = []
    index = flat.find(needle)
    while index != -1:
        found.append(index + 1)
        index = flat.find(needle, index + 1)
    return found


def test_dataset_shape(store: DigitStore, flat: bytes) -> None:
    assert store.total_digits == TOTAL == len(flat)
    assert store.chunk_count == 3
    assert all(chunk.complete for chunk in store.manifest.chunks)


@pytest.mark.parametrize("boundary", BOUNDARIES)
@pytest.mark.parametrize("length", [2, 7, 12])
def test_sequence_straddling_a_boundary_is_found_once_there(
    store: DigitStore, flat: bytes, boundary: int, length: int
) -> None:
    # Every split of the pattern across the two chunks: 1 digit before, 2 before, ...
    for before in range(1, length):
        start = boundary - before + 1
        pattern = "".join(str(digit) for digit in flat[start - 1 : start - 1 + length])
        result = search_sequence(store, pattern)
        positions = result.positions.tolist()
        assert positions == flat_positions(flat, pattern)
        assert positions.count(start) == 1
        assert result.total_count == len(positions)


@pytest.mark.parametrize("pattern", ["314159", "999999", "00", "1234567", "88888888"])
def test_search_matches_flat_scan(store: DigitStore, flat: bytes, pattern: str) -> None:
    result = search_sequence(store, pattern)
    assert not result.positions_truncated
    assert result.positions.tolist() == flat_positions(flat, pattern)


@pytest.mark.parametrize("boundary", BOUNDARIES)
def test_range_reads_across_a_boundary(store: DigitStore, flat: bytes, boundary: int) -> None:
    for start, count in [(boundary, 1), (boundary, 2), (boundary - 49, 100), (boundary + 1, 10)]:
        expected: NDArray[np.uint8] = np.frombuffer(flat[start - 1 : start - 1 + count], np.uint8)
        np.testing.assert_array_equal(store.get_range(start, count), expected)
        assert store.get_text(start, count) == digits_to_text(expected)
    assert store.get_digit(boundary) == flat[boundary - 1]
    assert store.get_digit(boundary + 1) == flat[boundary]


def test_counts_over_a_range_spanning_all_chunks(store: DigitStore, flat: bytes) -> None:
    start, count = CHUNK - 123_456, CHUNK + 400_000
    window = np.frombuffer(flat[start - 1 : start - 1 + count], np.uint8)
    np.testing.assert_array_equal(
        count_digits(store, start, count), np.bincount(window, minlength=10)
    )
