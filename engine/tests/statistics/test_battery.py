import numpy as np
import pytest
from numpy.typing import NDArray

from piscope_engine.statistics.battery import (
    ALL_TESTS,
    BatteryOptions,
    compare_with_random,
    run_battery,
)
from piscope_engine.statistics.multiple_testing import adjust_p_values
from piscope_engine.statistics.simulation import describe_source, random_digit_sequences


def test_same_seed_gives_identical_sequences() -> None:
    first = random_digit_sequences(1_000, seed=42, count=3)
    second = random_digit_sequences(1_000, seed=42, count=3)
    for left, right in zip(first, second, strict=True):
        np.testing.assert_array_equal(left, right)
    assert first[0].dtype == np.uint8
    assert int(first[0].max()) <= 9


def test_different_seeds_and_children_differ() -> None:
    base = random_digit_sequences(1_000, seed=42, count=2)
    other = random_digit_sequences(1_000, seed=43, count=1)
    assert not np.array_equal(base[0], other[0])
    assert not np.array_equal(base[0], base[1])


def test_sequence_does_not_depend_on_how_many_are_requested() -> None:
    one = random_digit_sequences(500, seed=7, count=1)
    five = random_digit_sequences(500, seed=7, count=5)
    np.testing.assert_array_equal(one[0], five[0])


def test_source_is_recorded() -> None:
    source = describe_source(42)
    assert source.seed == 42
    assert source.bit_generator == "PCG64"
    assert source.numpy_version == np.__version__


@pytest.mark.parametrize(("length", "seed", "count"), [(0, 1, 1), (10, -1, 1), (10, 1, 0)])
def test_invalid_simulation_requests(length: int, seed: int, count: int) -> None:
    with pytest.raises(ValueError, match="must be"):
        random_digit_sequences(length, seed, count)


def test_battery_runs_every_test(reference_10k: NDArray[np.uint8]) -> None:
    battery = run_battery(reference_10k)
    assert [result.key for result in battery.results] == list(ALL_TESTS)
    assert battery.tests_with_p_values == 4  # entropy has no p-value
    assert set(battery.adjusted_p_values) == {
        "chi_square",
        "autocorrelation",
        "runs",
        "ngram_blocks",
    }
    raw = [r.p_value for r in battery.results if r.p_value is not None]
    assert list(battery.adjusted_p_values.values()) == pytest.approx(adjust_p_values(raw, "holm"))
    for result in battery.results:
        if result.p_value is not None:
            assert battery.adjusted_p_values[result.key] >= result.p_value


def test_battery_subset_and_options(reference_10k: NDArray[np.uint8]) -> None:
    options = BatteryOptions(
        tests=("runs", "autocorrelation"),
        max_lag=7,
        runs_dichotomy="parity",
        correction="bonferroni",
    )
    battery = run_battery(reference_10k, options)
    assert [result.key for result in battery.results] == ["runs", "autocorrelation"]
    assert battery.results[0].details["dichotomy"] == "parity"
    assert battery.results[1].degrees_of_freedom == 7
    assert battery.correction == "bonferroni"


def test_battery_rejects_bad_requests(reference_10k: NDArray[np.uint8]) -> None:
    with pytest.raises(ValueError, match="unknown test"):
        run_battery(reference_10k, BatteryOptions(tests=("chi_square", "astrology")))
    with pytest.raises(ValueError, match="at least one"):
        run_battery(reference_10k, BatteryOptions(tests=()))
    with pytest.raises(ValueError, match="empty"):
        run_battery(np.array([], dtype=np.uint8))


def test_comparison_is_reproducible(reference_10k: NDArray[np.uint8]) -> None:
    first = compare_with_random(reference_10k[:2_000], seed=99, simulations=8)
    second = compare_with_random(reference_10k[:2_000], seed=99, simulations=8)
    assert first.statistics == second.statistics
    assert first.first_simulation_counts == second.first_simulation_counts
    different = compare_with_random(reference_10k[:2_000], seed=100, simulations=8)
    assert different.statistics != first.statistics
    assert first.source.seed == 99
    assert first.simulations == 8
    assert first.length == 2_000


def test_comparison_statistics_are_consistent(reference_10k: NDArray[np.uint8]) -> None:
    digits = reference_10k[:3_000]
    comparison = compare_with_random(digits, seed=5, simulations=12)
    simulated = random_digit_sequences(3_000, seed=5, count=12)
    chi = next(item for item in comparison.statistics if item.key == "chi_square")
    recomputed = [run_battery(s).results[0].statistic for s in simulated]
    assert chi.simulated == pytest.approx(recomputed)
    assert chi.observed == pytest.approx(run_battery(digits).results[0].statistic)
    assert chi.simulated_mean == pytest.approx(float(np.mean(recomputed)))
    assert chi.simulated_std == pytest.approx(float(np.std(recomputed, ddof=1)))
    assert chi.fraction_at_or_below == pytest.approx(
        sum(value <= chi.observed for value in recomputed) / 12
    )
    assert sum(comparison.observed_counts) == 3_000
    assert sum(comparison.first_simulation_counts) == 3_000
    assert comparison.first_simulation_counts == np.bincount(simulated[0], minlength=10).tolist()


def test_comparison_needs_a_simulation(reference_10k: NDArray[np.uint8]) -> None:
    with pytest.raises(ValueError, match="simulations"):
        compare_with_random(reference_10k, seed=1, simulations=0)
