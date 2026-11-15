from collections import Counter
from pathlib import Path

import numpy as np
import pytest
from numpy.typing import NDArray

from piscope_engine.digits.store import DigitStore, digits_to_text
from piscope_engine.errors import PositionOutOfRangeError
from piscope_engine.statistics.frequency import analyze_frequency, count_digits, summarize_counts

from engine_support import make_store, text_to_digits


def test_hand_counted_example(tmp_path: Path) -> None:
    store = make_store(tmp_path, text_to_digits("11223344550000000000"), chunk_size=7)
    analysis = analyze_frequency(store, 1, 20)
    assert [entry.count for entry in analysis.digits] == [10, 2, 2, 2, 2, 2, 0, 0, 0, 0]
    assert analysis.sample_size == 20
    assert analysis.most_frequent == [0]
    assert analysis.least_frequent == [6, 7, 8, 9]
    zero = analysis.digits[0]
    assert zero.expected_count == pytest.approx(2.0)
    assert zero.deviation == pytest.approx(8.0)
    assert zero.relative_frequency == pytest.approx(0.5)
    assert zero.standardized_deviation == pytest.approx(8 / (20 * 0.09) ** 0.5)


def test_counts_match_python_counter_across_chunks(
    synthetic_store: DigitStore, synthetic_digits: NDArray[np.uint8]
) -> None:
    for start, count in [(1, 1_050), (95, 310), (1_001, 50), (500, 1)]:
        expected = Counter(digits_to_text(synthetic_digits[start - 1 : start - 1 + count]))
        counts = count_digits(synthetic_store, start, count)
        assert counts.tolist() == [expected.get(str(digit), 0) for digit in range(10)]
        assert int(counts.sum()) == count


def test_first_ten_thousand_digits_of_pi(
    pi_store: DigitStore, reference_10k: NDArray[np.uint8]
) -> None:
    analysis = analyze_frequency(pi_store, 1, 10_000)
    expected = Counter(digits_to_text(reference_10k))
    assert [entry.count for entry in analysis.digits] == [expected[str(d)] for d in range(10)]
    assert (analysis.range_start, analysis.range_end) == (1, 10_000)
    assert sum(entry.relative_frequency for entry in analysis.digits) == pytest.approx(1.0)
    assert sum(entry.deviation for entry in analysis.digits) == pytest.approx(0.0)


def test_range_is_reported(synthetic_store: DigitStore) -> None:
    analysis = analyze_frequency(synthetic_store, 201, 300)
    assert (analysis.range_start, analysis.range_end, analysis.sample_size) == (201, 500, 300)


def test_invalid_requests(synthetic_store: DigitStore) -> None:
    with pytest.raises(PositionOutOfRangeError):
        analyze_frequency(synthetic_store, 1_000, 100)
    with pytest.raises(ValueError, match="empty"):
        analyze_frequency(synthetic_store, 1, 0)
    with pytest.raises(ValueError, match="ten"):
        summarize_counts(np.zeros(9, dtype=np.int64), 1)
