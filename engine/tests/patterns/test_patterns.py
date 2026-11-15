import numpy as np
import pytest
from numpy.typing import NDArray

from piscope_engine.patterns.runs import find_runs, longest_runs, run_length_distribution
from piscope_engine.patterns.windows import analyze_windows
from piscope_engine.statistics.simulation import random_digit_sequences

from engine_support import text_to_digits


def test_find_runs_by_hand() -> None:
    runs = find_runs(text_to_digits("1122233334"))
    assert [(run.digit, run.length, run.position) for run in runs] == [
        (1, 2, 1),
        (2, 3, 3),
        (3, 4, 6),
        (4, 1, 10),
    ]
    assert find_runs(np.array([], dtype=np.uint8)) == []


def test_longest_runs_order_and_offset() -> None:
    digits = text_to_digits("5550001112222")
    top = longest_runs(digits, top=3, first_position=101)
    assert [(run.digit, run.length, run.position) for run in top] == [
        (2, 4, 110),
        (5, 3, 101),  # ties: earliest first
        (0, 3, 104),
    ]
    with pytest.raises(ValueError, match="top"):
        longest_runs(digits, top=0)


def test_longest_run_in_published_pi_is_the_six_nines(reference_10k: NDArray[np.uint8]) -> None:
    longest = longest_runs(reference_10k, top=1)[0]
    assert (longest.digit, longest.length, longest.position) == (9, 6, 762)


def test_run_length_distribution() -> None:
    rows = run_length_distribution(text_to_digits("1122233334"))
    assert [(row.length, row.observed) for row in rows] == [(1, 1), (2, 1), (3, 1), (4, 1)]
    assert rows[0].expected == pytest.approx(10 * 0.81)
    assert rows[1].expected == pytest.approx(10 * 0.081)


def test_run_length_expectation_matches_simulation() -> None:
    digits = random_digit_sequences(500_000, seed=8)[0]
    rows = run_length_distribution(digits)
    for row in rows[:3]:
        assert row.observed == pytest.approx(row.expected, rel=0.03)


def test_windows_by_hand() -> None:
    analysis = analyze_windows(text_to_digits("0000011111" + "0123456789" + "777"), 2)
    assert analysis.window_size == 11  # 23 digits // 2, one leftover digit ignored
    assert analysis.counts.shape == (2, 10)
    assert analysis.counts[0].tolist() == [6, 5, 0, 0, 0, 0, 0, 0, 0, 0]
    assert int(analysis.counts.sum()) == 22
    spread = (11 * 0.09) ** 0.5
    assert analysis.standardized[0, 0] == pytest.approx((6 - 1.1) / spread)
    assert analysis.max_abs_z == pytest.approx((6 - 1.1) / spread)


def test_window_outlier_counts_on_random_digits() -> None:
    digits = random_digit_sequences(1_000_000, seed=21)[0]
    analysis = analyze_windows(digits, 100)
    assert analysis.window_size == 10_000
    assert analysis.expected_cells_beyond_two == pytest.approx(45.5)
    assert 20 <= analysis.cells_beyond_two <= 75  # chance alone produces dozens of |z| > 2
    assert analysis.cells_beyond_three <= 12


def test_window_validation() -> None:
    with pytest.raises(ValueError, match="window_count"):
        analyze_windows(text_to_digits("123"), 0)
    with pytest.raises(ValueError, match="more windows"):
        analyze_windows(text_to_digits("123"), 4)
