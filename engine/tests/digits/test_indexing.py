import pytest

from piscope_engine.digits.indexing import (
    DEFAULT_CHUNK_SIZE,
    ChunkAddress,
    address_to_position,
    chunk_count_for,
    chunk_filename,
    chunk_first_position,
    position_to_address,
)


def test_default_chunk_size_is_one_million() -> None:
    assert DEFAULT_CHUNK_SIZE == 1_000_000


@pytest.mark.parametrize(
    ("position", "chunk_index", "offset"),
    [
        (1, 0, 0),
        (2, 0, 1),
        (1_000_000, 0, 999_999),
        (1_000_001, 1, 0),
        (2_000_000, 1, 999_999),
        (2_000_001, 2, 0),
        (1_000_000_000, 999, 999_999),
    ],
)
def test_position_to_address(position: int, chunk_index: int, offset: int) -> None:
    assert position_to_address(position) == ChunkAddress(chunk_index, offset)


@pytest.mark.parametrize("chunk_size", [1, 7, 100, 1_000_000])
def test_round_trip(chunk_size: int) -> None:
    for position in [1, 2, chunk_size, chunk_size + 1, 3 * chunk_size, 10 * chunk_size + 5]:
        address = position_to_address(position, chunk_size)
        assert 0 <= address.offset < chunk_size
        assert address_to_position(address, chunk_size) == position


@pytest.mark.parametrize("position", [0, -1])
def test_position_below_one_is_rejected(position: int) -> None:
    with pytest.raises(ValueError, match="position must be >= 1"):
        position_to_address(position)


def test_invalid_chunk_size_is_rejected() -> None:
    with pytest.raises(ValueError, match="chunk_size"):
        position_to_address(1, chunk_size=0)


@pytest.mark.parametrize("address", [ChunkAddress(-1, 0), ChunkAddress(0, -1), ChunkAddress(0, 10)])
def test_invalid_address_is_rejected(address: ChunkAddress) -> None:
    with pytest.raises(ValueError, match="must be"):
        address_to_position(address, chunk_size=10)


def test_chunk_first_position() -> None:
    assert chunk_first_position(0) == 1
    assert chunk_first_position(1) == 1_000_001
    assert chunk_first_position(3, chunk_size=10) == 31


@pytest.mark.parametrize(
    ("total", "expected"), [(0, 0), (1, 1), (999_999, 1), (1_000_000, 1), (1_000_001, 2)]
)
def test_chunk_count_for(total: int, expected: int) -> None:
    assert chunk_count_for(total) == expected


def test_chunk_filename() -> None:
    assert chunk_filename(0) == "chunk-000000.bin"
    assert chunk_filename(999) == "chunk-000999.bin"
    with pytest.raises(ValueError, match="chunk_index"):
        chunk_filename(-1)
