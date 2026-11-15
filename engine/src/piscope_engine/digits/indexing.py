"""Conversions between public digit positions and physical chunk addresses.

Public positions are 1-based: position 1 is the first digit after the decimal point.
Chunk indices and local offsets are 0-based and never leave the storage layer.
"""

from dataclasses import dataclass

DEFAULT_CHUNK_SIZE = 1_000_000


@dataclass(frozen=True, slots=True)
class ChunkAddress:
    """Physical location of one digit.

    Attributes:
        chunk_index: 0-based index of the chunk file.
        offset: 0-based byte offset inside that chunk.
    """

    chunk_index: int
    offset: int


def _require_chunk_size(chunk_size: int) -> None:
    if chunk_size < 1:
        raise ValueError(f"chunk_size must be >= 1, got {chunk_size}")


def position_to_address(position: int, chunk_size: int = DEFAULT_CHUNK_SIZE) -> ChunkAddress:
    """Convert a 1-based digit position to its chunk index and local offset.

    Args:
        position: 1-based decimal position (1 is the first digit after the point).
        chunk_size: Number of digits per chunk.

    Returns:
        The chunk address holding that digit.

    Raises:
        ValueError: If ``position`` or ``chunk_size`` is below 1.
    """
    _require_chunk_size(chunk_size)
    if position < 1:
        raise ValueError(f"position must be >= 1, got {position}")
    chunk_index, offset = divmod(position - 1, chunk_size)
    return ChunkAddress(chunk_index=chunk_index, offset=offset)


def address_to_position(address: ChunkAddress, chunk_size: int = DEFAULT_CHUNK_SIZE) -> int:
    """Convert a chunk address back to its 1-based digit position.

    Raises:
        ValueError: If the address is negative or its offset does not fit in a chunk.
    """
    _require_chunk_size(chunk_size)
    if address.chunk_index < 0:
        raise ValueError(f"chunk_index must be >= 0, got {address.chunk_index}")
    if not 0 <= address.offset < chunk_size:
        raise ValueError(f"offset must be in [0, {chunk_size}), got {address.offset}")
    return address.chunk_index * chunk_size + address.offset + 1


def chunk_first_position(chunk_index: int, chunk_size: int = DEFAULT_CHUNK_SIZE) -> int:
    """Return the 1-based position of the first digit stored in a chunk."""
    return address_to_position(ChunkAddress(chunk_index, 0), chunk_size)


def chunk_count_for(total_digits: int, chunk_size: int = DEFAULT_CHUNK_SIZE) -> int:
    """Return how many chunks are needed to hold ``total_digits`` digits."""
    _require_chunk_size(chunk_size)
    if total_digits < 0:
        raise ValueError(f"total_digits must be >= 0, got {total_digits}")
    return -(-total_digits // chunk_size)


def chunk_filename(chunk_index: int) -> str:
    """Return the file name used for a chunk, e.g. ``chunk-000003.bin``."""
    if chunk_index < 0:
        raise ValueError(f"chunk_index must be >= 0, got {chunk_index}")
    return f"chunk-{chunk_index:06d}.bin"
