"""Exact digit-sequence search over a chunked dataset.

Conventions:

* Positions are 1-based; a match is reported by the position of its first digit.
* Overlapping occurrences all count: ``000`` occurs twice in ``0000``.
* A search range ``[start, end]`` only reports matches that lie *entirely* inside it.

Algorithm: each chunk is scanned with CPython's ``bytes.find`` over a window that
extends ``len(pattern) - 1`` digits past the end of the chunk. A match is attributed to
the chunk in which it starts, so sequences that straddle a chunk boundary are found
exactly once. One-digit patterns use a NumPy comparison instead, which benchmarks
several times faster for that case (see ``engine/benchmarks/search_algorithms.py``).
"""

import time
from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

from piscope_engine.digits.store import DigitStore
from piscope_engine.errors import InvalidPatternError, PositionOutOfRangeError

DEFAULT_MAX_STORED_POSITIONS = 5_000_000

type PositionArray = NDArray[np.int64]


@dataclass(frozen=True, slots=True)
class SearchResult:
    """Outcome of one sequence search.

    Attributes:
        pattern: The digit sequence searched for.
        range_start: First position of the searched range (1-based, inclusive).
        range_end: Last position of the searched range (inclusive).
        total_count: Number of occurrences in the range, overlapping ones included.
        first_position: Position of the first occurrence, or None if there is none.
        positions: Start positions in ascending order. Holds every occurrence unless
            ``positions_truncated`` is True.
        positions_truncated: True when more occurrences exist than were stored.
        expected_count: Occurrences expected if every digit were independent and
            uniform: ``(range_length - len(pattern) + 1) / 10**len(pattern)``.
        elapsed_seconds: Wall-clock time spent scanning.
    """

    pattern: str
    range_start: int
    range_end: int
    total_count: int
    first_position: int | None
    positions: PositionArray
    positions_truncated: bool
    expected_count: float
    elapsed_seconds: float


def encode_pattern(pattern: str) -> bytes:
    """Convert a string of decimal digits to the stored byte encoding (values 0-9).

    Raises:
        InvalidPatternError: If the pattern is empty or has non-digit characters.
    """
    if not pattern:
        raise InvalidPatternError("search pattern is empty")
    if not (pattern.isascii() and pattern.isdigit()):
        raise InvalidPatternError("search pattern may only contain the digits 0-9")
    return bytes(ord(character) - ord("0") for character in pattern)


def expected_occurrences(range_length: int, pattern_length: int) -> float:
    """Expected number of occurrences under an independent, uniform digit model."""
    windows = range_length - pattern_length + 1
    if windows <= 0:
        return 0.0
    return windows / 10**pattern_length


def gaps_between(positions: PositionArray) -> PositionArray:
    """Distances between consecutive occurrences (``positions[i+1] - positions[i]``)."""
    return np.diff(positions)


def _find_in_window(window: bytes, needle: bytes, owned_length: int) -> PositionArray:
    """Return 0-based offsets of matches that start within the first ``owned_length`` bytes."""
    if len(needle) == 1:
        data = np.frombuffer(window, dtype=np.uint8)[:owned_length]
        return np.flatnonzero(data == needle[0]).astype(np.int64)
    found: list[int] = []
    index = window.find(needle)
    while index != -1 and index < owned_length:
        found.append(index)
        index = window.find(needle, index + 1)
    return np.array(found, dtype=np.int64)


def search_sequence(
    store: DigitStore,
    pattern: str,
    start: int = 1,
    end: int | None = None,
    max_stored_positions: int = DEFAULT_MAX_STORED_POSITIONS,
) -> SearchResult:
    """Find every occurrence of a digit sequence inside a position range.

    Args:
        store: Dataset to search.
        pattern: Sequence of decimal digits, e.g. ``"314159"``.
        start: First position of the range (1-based, inclusive).
        end: Last position of the range (inclusive). Defaults to the last stored digit.
        max_stored_positions: Upper bound on returned positions. Counting always covers
            the whole range; only the stored list is cut short.

    Returns:
        A :class:`SearchResult`. An absent pattern gives ``total_count == 0``.

    Raises:
        InvalidPatternError: If the pattern is empty or not made of digits.
        PositionOutOfRangeError: If the range is empty or outside the dataset.
    """
    needle = encode_pattern(pattern)
    if max_stored_positions < 0:
        raise ValueError("max_stored_positions must be >= 0")
    last = store.total_digits if end is None else end
    if start < 1 or last > store.total_digits or start > last:
        raise PositionOutOfRangeError(
            f"search range {start}..{last} is not inside 1..{store.total_digits}"
        )

    started = time.perf_counter()
    pattern_length = len(needle)
    last_match_start = last - pattern_length + 1
    stored: list[PositionArray] = []
    stored_count = 0
    total_count = 0
    first_position: int | None = None

    block_start = start
    while block_start <= last_match_start:
        # Scan up to the end of the chunk that holds block_start.
        chunk_index = (block_start - 1) // store.chunk_size
        chunk_end = min((chunk_index + 1) * store.chunk_size, last_match_start)
        owned_length = chunk_end - block_start + 1
        window = store.get_range(block_start, owned_length + pattern_length - 1).tobytes()
        positions = _find_in_window(window, needle, owned_length) + block_start
        if positions.size:
            if first_position is None:
                first_position = int(positions[0])
            total_count += int(positions.size)
            room = max_stored_positions - stored_count
            if room > 0:
                kept = positions[:room]
                stored.append(kept)
                stored_count += int(kept.size)
        block_start = chunk_end + 1

    all_positions = np.concatenate(stored) if stored else np.empty(0, dtype=np.int64)
    return SearchResult(
        pattern=pattern,
        range_start=start,
        range_end=last,
        total_count=total_count,
        first_position=first_position,
        positions=all_positions,
        positions_truncated=total_count > stored_count,
        expected_count=expected_occurrences(last - start + 1, pattern_length),
        elapsed_seconds=time.perf_counter() - started,
    )
