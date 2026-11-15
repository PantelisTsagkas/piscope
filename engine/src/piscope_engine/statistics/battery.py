"""Run a set of tests on one sequence and compare sequences against simulations."""

from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

from piscope_engine.statistics.hypothesis_tests import (
    Dichotomy,
    autocorrelation_test,
    chi_square_test,
    digit_counts,
    ngram_block_test,
    runs_test,
    shannon_entropy,
)
from piscope_engine.statistics.multiple_testing import Correction, adjust_p_values
from piscope_engine.statistics.result import TestResult
from piscope_engine.statistics.simulation import (
    RandomSource,
    describe_source,
    random_digit_sequences,
)

type DigitArray = NDArray[np.uint8]

ALL_TESTS: tuple[str, ...] = (
    "chi_square",
    "shannon_entropy",
    "autocorrelation",
    "runs",
    "ngram_blocks",
)


@dataclass(frozen=True, slots=True)
class BatteryOptions:
    """Settings for a run of several tests.

    Attributes:
        tests: Keys of the tests to run, a subset of :data:`ALL_TESTS`.
        max_lag: Largest lag for the autocorrelation test.
        ngram_length: Block length for the n-gram block test.
        runs_dichotomy: Recoding used by the runs test.
        correction: Multiple-testing correction applied across the tests that were run.
    """

    tests: tuple[str, ...] = ALL_TESTS
    max_lag: int = 20
    ngram_length: int = 2
    runs_dichotomy: Dichotomy = "high_low"
    correction: Correction = "holm"


@dataclass(frozen=True, slots=True)
class BatteryResult:
    """Results of several tests on one sequence.

    Attributes:
        results: One entry per requested test, in request order.
        adjusted_p_values: Test key to multiplicity-adjusted p-value, for every test
            that has a p-value.
        correction: The correction that produced ``adjusted_p_values``.
        tests_with_p_values: Size of the family the correction was applied to.
    """

    results: list[TestResult]
    adjusted_p_values: dict[str, float]
    correction: Correction
    tests_with_p_values: int


@dataclass(frozen=True, slots=True)
class SimulatedStatistic:
    """Where one statistic of the analysed digits falls among simulated sequences.

    Attributes:
        key: Test key.
        name: Test name.
        statistic_name: Name of the statistic.
        observed: The statistic for the analysed digits.
        simulated: The statistic for every simulated sequence, in simulation order.
        simulated_mean: Mean of ``simulated``.
        simulated_std: Sample standard deviation of ``simulated`` (0 for one simulation).
        simulated_min: Smallest simulated value.
        simulated_max: Largest simulated value.
        fraction_at_or_below: Share of simulated values less than or equal to
            ``observed``; an empirical percentile, not a p-value.
    """

    key: str
    name: str
    statistic_name: str
    observed: float
    simulated: list[float]
    simulated_mean: float
    simulated_std: float
    simulated_min: float
    simulated_max: float
    fraction_at_or_below: float


@dataclass(frozen=True, slots=True)
class ComparisonResult:
    """A sequence compared with simulated random sequences of the same length.

    Attributes:
        observed: Battery results for the analysed digits.
        first_simulation: Battery results for the first simulated sequence.
        observed_counts: Digit counts of the analysed digits.
        first_simulation_counts: Digit counts of the first simulated sequence.
        statistics: Per-test comparison against all simulations.
        simulations: Number of simulated sequences.
        length: Digits in each sequence.
        source: Reproducibility record for the random sequences.
    """

    observed: BatteryResult
    first_simulation: BatteryResult
    observed_counts: list[int]
    first_simulation_counts: list[int]
    statistics: list[SimulatedStatistic]
    simulations: int
    length: int
    source: RandomSource


def run_battery(digits: DigitArray, options: BatteryOptions | None = None) -> BatteryResult:
    """Run the requested tests on a digit sequence.

    Raises:
        ValueError: If a test key is unknown, no test is requested, or the sequence is
            too short for a requested test.
    """
    chosen = options or BatteryOptions()
    if not chosen.tests:
        raise ValueError("at least one test must be requested")
    unknown = [key for key in chosen.tests if key not in ALL_TESTS]
    if unknown:
        raise ValueError(f"unknown test(s): {', '.join(unknown)}")
    if digits.size == 0:
        raise ValueError("cannot analyse an empty sequence")

    counts = digit_counts(digits)
    results: list[TestResult] = []
    for key in chosen.tests:
        if key == "chi_square":
            results.append(chi_square_test(counts))
        elif key == "shannon_entropy":
            results.append(shannon_entropy(counts))
        elif key == "autocorrelation":
            results.append(autocorrelation_test(digits, chosen.max_lag))
        elif key == "runs":
            results.append(runs_test(digits, chosen.runs_dichotomy))
        else:
            results.append(ngram_block_test(digits, chosen.ngram_length))

    with_p = [result for result in results if result.p_value is not None]
    raw = [float(result.p_value) for result in with_p if result.p_value is not None]
    adjusted = adjust_p_values(raw, chosen.correction)
    return BatteryResult(
        results=results,
        adjusted_p_values={
            result.key: value for result, value in zip(with_p, adjusted, strict=True)
        },
        correction=chosen.correction,
        tests_with_p_values=len(with_p),
    )


def compare_with_random(
    digits: DigitArray,
    seed: int,
    simulations: int = 20,
    options: BatteryOptions | None = None,
) -> ComparisonResult:
    """Compare a digit sequence with simulated random sequences of equal length.

    The same battery runs on the analysed digits and on every simulated sequence. For
    each statistic the result reports the simulated spread and the share of simulations
    at or below the observed value.

    Args:
        digits: Sequence to analyse (for example a range of pi).
        seed: Seed for the simulations, recorded in the result.
        simulations: Number of simulated sequences.
        options: Battery settings shared by all sequences.

    Raises:
        ValueError: If ``simulations`` is below 1 or the battery cannot run.
    """
    if simulations < 1:
        raise ValueError("simulations must be >= 1")
    chosen = options or BatteryOptions()
    observed = run_battery(digits, chosen)
    sequences = random_digit_sequences(int(digits.size), seed, simulations)
    simulated_values: dict[str, list[float]] = {result.key: [] for result in observed.results}
    first_simulation: BatteryResult | None = None
    for index, sequence in enumerate(sequences):
        battery = run_battery(sequence, chosen)
        if index == 0:
            first_simulation = battery
        for result in battery.results:
            simulated_values[result.key].append(result.statistic)
    if first_simulation is None:
        raise ValueError("no simulations were run")

    statistics: list[SimulatedStatistic] = []
    for result in observed.results:
        values = np.array(simulated_values[result.key], dtype=np.float64)
        statistics.append(
            SimulatedStatistic(
                key=result.key,
                name=result.name,
                statistic_name=result.statistic_name,
                observed=result.statistic,
                simulated=values.tolist(),
                simulated_mean=float(values.mean()),
                simulated_std=float(values.std(ddof=1)) if values.size > 1 else 0.0,
                simulated_min=float(values.min()),
                simulated_max=float(values.max()),
                fraction_at_or_below=float(np.count_nonzero(values <= result.statistic))
                / values.size,
            )
        )
    return ComparisonResult(
        observed=observed,
        first_simulation=first_simulation,
        observed_counts=digit_counts(digits).tolist(),
        first_simulation_counts=digit_counts(sequences[0]).tolist(),
        statistics=statistics,
        simulations=simulations,
        length=int(digits.size),
        source=describe_source(seed),
    )
