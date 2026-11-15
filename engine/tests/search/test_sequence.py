from pathlib import Path

import numpy as np
import pytest
from numpy.typing import NDArray

from piscope_engine.digits.store import DigitStore, digits_to_text
from piscope_engine.errors import InvalidPatternError, PositionOutOfRangeError
from piscope_engine.search.sequence import (
    encode_pattern,
    expected_occurrences,
    gaps_between,
    search_sequence,
)

from engine_support import make_store, text_to_digits


def naive_positions(text: str, pattern: str, start: int = 1, end: int | None = None) -> list[int]:
    """Oracle: every 1-based start position of pattern lying fully inside [start, end]."""
    last = len(text) if end is None else end
    found: list[int] = []
    for position in range(start, last - len(pattern) + 2):
        if text[position - 1 : position - 1 + len(pattern)] == pattern:
            found.append(position)
    return found


def test_encode_pattern() -> None:
    assert encode_pattern("0190") == bytes([0, 1, 9, 0])


@pytest.mark.parametrize(
    "pattern", ["", "12a4", "3.14", " 12", "-1", "\u0661\u0662\u0663", "1\uff12"]
)
def test_invalid_patterns_are_rejected(synthetic_store: DigitStore, pattern: str) -> None:
    with pytest.raises(InvalidPatternError):
        search_sequence(synthetic_store, pattern)


@pytest.mark.parametrize("length", [1, 2, 3, 4])
def test_matches_naive_oracle_on_synthetic_data(
    synthetic_store: DigitStore, synthetic_digits: NDArray[np.uint8], length: int
) -> None:
    text = digits_to_text(synthetic_digits)
    patterns = {text[offset : offset + length] for offset in range(0, 1_000, 37)}
    for pattern in patterns:
        result = search_sequence(synthetic_store, pattern)
        expected = naive_positions(text, pattern)
        assert result.positions.tolist() == expected
        assert result.total_count == len(expected)
        assert result.first_position == expected[0]
        assert not result.positions_truncated


def test_pattern_straddling_every_chunk_boundary(tmp_path: Path) -> None:
    # Chunks of 10 digits; "123456" is planted so that it crosses boundaries at every split.
    text = "0000000123" + "4560000000" + "0000012345" + "6000000000" + "0000000001" + "23456"
    store = make_store(tmp_path, text_to_digits(text), chunk_size=10)
    result = search_sequence(store, "123456")
    assert result.positions.tolist() == naive_positions(text, "123456") == [8, 26, 50]


def test_overlapping_matches_are_counted_once_each(tmp_path: Path) -> None:
    store = make_store(tmp_path, np.zeros(95, dtype=np.uint8), chunk_size=10)
    result = search_sequence(store, "000")
    assert result.total_count == 93
    assert result.positions.tolist() == list(range(1, 94))
    assert len(set(result.positions.tolist())) == 93


def test_pattern_longer_than_a_chunk(tmp_path: Path) -> None:
    text = "9" * 7 + "0123456789012345678901234" + "9" * 8
    store = make_store(tmp_path, text_to_digits(text), chunk_size=10)
    result = search_sequence(store, "0123456789012345678901234")
    assert result.positions.tolist() == [8]


def test_match_on_last_digits_and_in_partial_chunk(tmp_path: Path) -> None:
    text = "1" * 20 + "11427"  # final chunk is partial (5 digits)
    store = make_store(tmp_path, text_to_digits(text), chunk_size=10)
    assert search_sequence(store, "427").positions.tolist() == [23]
    assert search_sequence(store, "7").positions.tolist() == [25]
    assert search_sequence(store, "1142").positions.tolist() == [21]


def test_pattern_longer_than_dataset_finds_nothing(tmp_path: Path) -> None:
    store = make_store(tmp_path, text_to_digits("12345"), chunk_size=10)
    result = search_sequence(store, "123456")
    assert result.total_count == 0
    assert result.first_position is None
    assert result.positions.size == 0
    assert result.expected_count == 0.0


def test_absent_pattern(tmp_path: Path) -> None:
    store = make_store(tmp_path, np.zeros(50, dtype=np.uint8), chunk_size=10)
    result = search_sequence(store, "1")
    assert result.total_count == 0
    assert result.first_position is None


@pytest.mark.parametrize(
    ("start", "end"), [(1, 1_050), (37, 512), (100, 101), (101, 200), (995, 1_050)]
)
def test_range_only_reports_matches_fully_inside(
    synthetic_store: DigitStore, synthetic_digits: NDArray[np.uint8], start: int, end: int
) -> None:
    text = digits_to_text(synthetic_digits)
    for pattern in ["7", "42", text[98:102], text[510:513]]:
        result = search_sequence(synthetic_store, pattern, start=start, end=end)
        assert result.positions.tolist() == naive_positions(text, pattern, start, end)
        assert (result.range_start, result.range_end) == (start, end)


@pytest.mark.parametrize(("start", "end"), [(0, 10), (10, 5), (1, 1_051), (2_000, 2_010)])
def test_invalid_ranges_are_rejected(synthetic_store: DigitStore, start: int, end: int) -> None:
    with pytest.raises(PositionOutOfRangeError):
        search_sequence(synthetic_store, "1", start=start, end=end)


def test_stored_positions_can_be_capped_without_affecting_count(tmp_path: Path) -> None:
    store = make_store(tmp_path, np.zeros(95, dtype=np.uint8), chunk_size=10)
    result = search_sequence(store, "0", max_stored_positions=12)
    assert result.total_count == 95
    assert result.positions.tolist() == list(range(1, 13))
    assert result.positions_truncated


def test_known_sequences_in_published_pi(
    pi_store: DigitStore, reference_10k: NDArray[np.uint8]
) -> None:
    text = digits_to_text(reference_10k)
    assert search_sequence(pi_store, "14159").first_position == 1
    for pattern in ["999999", "2718", "0000", "31415", "123", "9", "00"]:
        result = search_sequence(pi_store, pattern)
        assert result.positions.tolist() == naive_positions(text, pattern), pattern
    # The run of six 9s (the "Feynman point") starts at decimal position 762.
    assert naive_positions(text, "999999") == [762]


def test_expected_occurrences() -> None:
    assert expected_occurrences(1_000_000, 1) == pytest.approx(100_000)
    assert expected_occurrences(1_000_000, 6) == pytest.approx(0.999995)
    assert expected_occurrences(3, 5) == 0.0


def test_gaps_between() -> None:
    assert gaps_between(np.array([3, 10, 11, 40], dtype=np.int64)).tolist() == [7, 1, 29]
    assert gaps_between(np.array([5], dtype=np.int64)).size == 0
