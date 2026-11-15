"""Frequency, n-gram, statistical test, comparison and pattern endpoints."""

import secrets
import time
from dataclasses import asdict
from typing import Annotated, Literal

import numpy as np
from fastapi import APIRouter, Query
from numpy.typing import NDArray

from piscope_api.errors import RequestLimitError
from piscope_api.schemas.analysis import (
    CompareRequest,
    CompareResponse,
    DigitFrequencyModel,
    DigitRunModel,
    FrequencyResponse,
    NgramResponse,
    NgramRow,
    ObservationsResponse,
    RandomSourceModel,
    RunLengthRowModel,
    RunsResponse,
    SimulatedStatisticModel,
    StatisticsRequest,
    StatisticsResponse,
    TestResultModel,
    WindowResponse,
    WindowRow,
)
from piscope_api.services import notes
from piscope_api.services.observations import build_observations
from piscope_api.settings import Settings
from piscope_api.state import SettingsDep, StateDep, StoreDep
from piscope_engine.digits.store import DigitStore
from piscope_engine.patterns.runs import longest_runs, run_length_distribution
from piscope_engine.patterns.windows import analyze_windows
from piscope_engine.statistics.battery import (
    BatteryOptions,
    BatteryResult,
    compare_with_random,
    run_battery,
)
from piscope_engine.statistics.frequency import analyze_frequency
from piscope_engine.statistics.hypothesis_tests import ngram_block_test
from piscope_engine.statistics.ngrams import ngram_label, summarize_ngrams
from piscope_engine.statistics.result import TestResult

router = APIRouter(prefix="/analysis")

type DigitArray = NDArray[np.uint8]

StartQuery = Annotated[int, Query(ge=1, description="First position to analyse (1-based)")]
CountQuery = Annotated[
    int | None, Query(ge=1, description="Digits to analyse; defaults to all from start")
]


def resolve_count(store: DigitStore, start: int, count: int | None, limit: int) -> int:
    """Fill in a default count (to the end of the dataset) and enforce a size limit."""
    resolved = count if count is not None else max(store.total_digits - start + 1, 1)
    if resolved > limit:
        raise RequestLimitError(
            f"this analysis accepts at most {limit:,} digits per request, got {resolved:,}; "
            "choose a smaller range"
        )
    return resolved


def load_digits(store: DigitStore, settings: Settings, start: int, count: int | None) -> DigitArray:
    """Load a bounded range of digits into memory for array-based analyses."""
    resolved = resolve_count(store, start, count, settings.max_statistics_digits)
    return store.get_range(start, resolved)


def to_model(result: TestResult, adjusted_p_value: float | None = None) -> TestResultModel:
    """Convert an engine test result to its API schema."""
    return TestResultModel(**asdict(result), adjusted_p_value=adjusted_p_value)


def battery_models(battery: BatteryResult) -> list[TestResultModel]:
    """Convert a battery, attaching adjusted p-values."""
    return [
        to_model(result, battery.adjusted_p_values.get(result.key)) for result in battery.results
    ]


def _check_test_options(
    settings: Settings, sample_size: int, max_lag: int, ngram_length: int, tests: list[str]
) -> None:
    if max_lag > settings.max_autocorrelation_lag:
        raise RequestLimitError(
            f"max_lag {max_lag} exceeds the limit of {settings.max_autocorrelation_lag}"
        )
    if ngram_length > settings.max_ngram_length:
        raise RequestLimitError(
            f"ngram_length {ngram_length} exceeds the limit of {settings.max_ngram_length}"
        )
    if "autocorrelation" in tests and max_lag >= sample_size:
        raise ValueError(f"max_lag {max_lag} must be smaller than the sample size {sample_size}")


@router.get("/frequency", response_model=FrequencyResponse, tags=["analysis"])
def frequency(
    store: StoreDep, settings: SettingsDep, start: StartQuery = 1, count: CountQuery = None
) -> FrequencyResponse:
    """Count each digit 0-9 in a range and compare with a uniform model."""
    resolved = resolve_count(store, start, count, settings.max_analysis_digits)
    analysis = analyze_frequency(store, start, resolved)
    return FrequencyResponse(
        range_start=analysis.range_start,
        range_end=analysis.range_end,
        sample_size=analysis.sample_size,
        expected_relative_frequency=0.1,
        digits=[DigitFrequencyModel(**asdict(entry)) for entry in analysis.digits],
        most_frequent=analysis.most_frequent,
        least_frequent=analysis.least_frequent,
        note=notes.FREQUENCY_NOTE,
    )


@router.get("/ngrams", response_model=NgramResponse, tags=["analysis"])
def ngrams(
    store: StoreDep,
    settings: SettingsDep,
    n: Annotated[int, Query(ge=1, description="N-gram length")] = 2,
    start: StartQuery = 1,
    count: CountQuery = None,
    overlapping: Annotated[
        bool, Query(description="Count a window at every position (true) or disjoint blocks")
    ] = True,
    sort: Annotated[
        Literal["count_desc", "count_asc", "ngram"], Query(description="Row order")
    ] = "count_desc",
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1)] = 100,
) -> NgramResponse:
    """Count every n-gram of length ``n`` in a range and return one page of the table."""
    if n > settings.max_ngram_length:
        raise RequestLimitError(f"n {n} exceeds the limit of {settings.max_ngram_length}")
    if limit > settings.max_ngram_rows:
        raise RequestLimitError(f"limit {limit} exceeds the maximum of {settings.max_ngram_rows}")
    digits = load_digits(store, settings, start, count)
    summary = summarize_ngrams(digits, n, overlapping)
    counts = summary.counts
    spread = float(np.sqrt(summary.expected_count * (1 - 1 / summary.possible)))

    def row(value: int) -> NgramRow:
        deviation = float(counts[value]) - summary.expected_count
        return NgramRow(
            ngram=ngram_label(value, n),
            count=int(counts[value]),
            deviation=deviation,
            standardized_deviation=deviation / spread if spread > 0 else 0.0,
        )

    values = np.arange(summary.possible)
    descending = np.lexsort((values, -counts))
    ascending = np.lexsort((values, counts))
    order = {"count_desc": descending, "count_asc": ascending, "ngram": values}[sort]
    page = order[offset : offset + limit].tolist()

    try:
        block_test: TestResultModel | None = to_model(ngram_block_test(digits, n))
    except ValueError:
        block_test = None

    return NgramResponse(
        length=n,
        overlapping=overlapping,
        range_start=start,
        range_end=start + int(digits.size) - 1,
        windows=summary.windows,
        possible=summary.possible,
        observed_distinct=summary.observed_distinct,
        missing=summary.possible - summary.observed_distinct,
        expected_count=summary.expected_count,
        sort=sort,
        offset=offset,
        limit=limit,
        total_rows=summary.possible,
        has_more=offset + len(page) < summary.possible,
        rows=[row(value) for value in page],
        most_common=[row(value) for value in descending[:5].tolist()],
        least_common=[row(value) for value in ascending[:5].tolist()],
        matrix=counts.reshape(10, 10).tolist() if n == 2 else None,
        block_test=block_test,
        note=notes.NGRAM_NOTE_OVERLAPPING if overlapping else notes.NGRAM_NOTE_DISJOINT,
    )


@router.post("/statistics", response_model=StatisticsResponse, tags=["analysis"])
def statistics(
    request: StatisticsRequest, store: StoreDep, state: StateDep, settings: SettingsDep
) -> StatisticsResponse:
    """Run statistical tests on a range and correct p-values for the tests requested."""
    started = time.perf_counter()
    digits = load_digits(store, settings, request.start, request.count)
    size = int(digits.size)
    _check_test_options(settings, size, request.max_lag, request.ngram_length, list(request.tests))
    battery = run_battery(
        digits,
        BatteryOptions(
            tests=tuple(request.tests),
            max_lag=request.max_lag,
            ngram_length=request.ngram_length,
            runs_dichotomy=request.runs_dichotomy,
            correction=request.correction,
        ),
    )
    range_end = request.start + size - 1
    state.experiments.record(
        kind="statistics",
        title=f"Statistical tests on positions {request.start:,} to {range_end:,}",
        parameters={
            "start": request.start,
            "count": size,
            "tests": list(request.tests),
            "max_lag": request.max_lag,
            "ngram_length": request.ngram_length,
            "runs_dichotomy": request.runs_dichotomy,
            "correction": request.correction,
        },
        summary={
            "p_values": {r.key: r.p_value for r in battery.results if r.p_value is not None},
            "adjusted_p_values": dict(battery.adjusted_p_values),
        },
    )
    return StatisticsResponse(
        range_start=request.start,
        range_end=range_end,
        sample_size=size,
        results=battery_models(battery),
        correction=battery.correction,
        family_size=battery.tests_with_p_values,
        multiple_testing_note=notes.MULTIPLE_TESTING_NOTE,
        scope_note=notes.SCOPE_NOTE,
        elapsed_ms=(time.perf_counter() - started) * 1000,
    )


@router.post("/compare", response_model=CompareResponse, tags=["analysis"])
def compare(
    request: CompareRequest, store: StoreDep, state: StateDep, settings: SettingsDep
) -> CompareResponse:
    """Compare a range of pi with reproducible simulated random sequences."""
    started = time.perf_counter()
    if request.count > settings.max_random_digits:
        raise RequestLimitError(
            f"count {request.count:,} exceeds the limit of {settings.max_random_digits:,}"
        )
    if request.simulations > settings.max_simulations:
        raise RequestLimitError(
            f"simulations {request.simulations} exceeds the limit of {settings.max_simulations}"
        )
    if request.count * request.simulations > settings.max_simulated_total_digits:
        raise RequestLimitError(
            f"count x simulations is {request.count * request.simulations:,}; the limit is "
            f"{settings.max_simulated_total_digits:,} simulated digits per request"
        )
    digits = load_digits(store, settings, request.start, request.count)
    _check_test_options(
        settings, int(digits.size), request.max_lag, request.ngram_length, list(request.tests)
    )
    seed = request.seed if request.seed is not None else secrets.randbits(32)
    comparison = compare_with_random(
        digits,
        seed=seed,
        simulations=request.simulations,
        options=BatteryOptions(
            tests=tuple(request.tests),
            max_lag=request.max_lag,
            ngram_length=request.ngram_length,
            runs_dichotomy=request.runs_dichotomy,
        ),
    )
    range_end = request.start + comparison.length - 1
    state.experiments.record(
        kind="comparison",
        title=(
            f"Pi positions {request.start:,} to {range_end:,} vs "
            f"{request.simulations} random sequence(s)"
        ),
        parameters={
            "start": request.start,
            "count": comparison.length,
            "seed": seed,
            "simulations": request.simulations,
            "tests": list(request.tests),
            "max_lag": request.max_lag,
            "ngram_length": request.ngram_length,
            "runs_dichotomy": request.runs_dichotomy,
            "bit_generator": comparison.source.bit_generator,
            "numpy_version": comparison.source.numpy_version,
        },
        summary={
            "percentiles": {item.key: item.fraction_at_or_below for item in comparison.statistics}
        },
    )
    return CompareResponse(
        range_start=request.start,
        range_end=range_end,
        length=comparison.length,
        simulations=comparison.simulations,
        source=RandomSourceModel(**asdict(comparison.source)),
        pi_results=battery_models(comparison.observed),
        random_results=battery_models(comparison.first_simulation),
        pi_counts=comparison.observed_counts,
        random_counts=comparison.first_simulation_counts,
        statistics=[SimulatedStatisticModel(**asdict(item)) for item in comparison.statistics],
        note=notes.COMPARISON_NOTE,
        elapsed_ms=(time.perf_counter() - started) * 1000,
    )


@router.get("/windows", response_model=WindowResponse, tags=["patterns"])
def windows(
    store: StoreDep,
    settings: SettingsDep,
    start: StartQuery = 1,
    count: CountQuery = None,
    windows: Annotated[int, Query(ge=1, description="Number of equal windows")] = 50,
) -> WindowResponse:
    """Count digits in consecutive windows to show where digits concentrate."""
    if windows > settings.max_windows:
        raise RequestLimitError(f"windows {windows} exceeds the limit of {settings.max_windows}")
    digits = load_digits(store, settings, start, count)
    analysis = analyze_windows(digits, windows, first_position=start)
    cells = analysis.window_count * 10
    rows = [
        WindowRow(
            index=index,
            start=start + index * analysis.window_size,
            end=start + (index + 1) * analysis.window_size - 1,
            counts=analysis.counts[index].tolist(),
            standardized=analysis.standardized[index].tolist(),
        )
        for index in range(analysis.window_count)
    ]
    return WindowResponse(
        range_start=start,
        range_end=start + analysis.window_size * analysis.window_count - 1,
        window_size=analysis.window_size,
        window_count=analysis.window_count,
        rows=rows,
        cells=cells,
        cells_beyond_two=analysis.cells_beyond_two,
        expected_cells_beyond_two=analysis.expected_cells_beyond_two,
        cells_beyond_three=analysis.cells_beyond_three,
        expected_cells_beyond_three=cells * 0.0027,
        max_abs_z=analysis.max_abs_z,
        approximation_reliable=analysis.window_size >= 50,
        note=notes.WINDOW_NOTE,
    )


@router.get("/runs", response_model=RunsResponse, tags=["patterns"])
def runs(
    store: StoreDep,
    settings: SettingsDep,
    start: StartQuery = 1,
    count: CountQuery = None,
    top: Annotated[int, Query(ge=1, le=100, description="How many longest runs to list")] = 10,
) -> RunsResponse:
    """List the longest runs of a repeated digit and the distribution of run lengths."""
    digits = load_digits(store, settings, start, count)
    return RunsResponse(
        range_start=start,
        range_end=start + int(digits.size) - 1,
        longest=[
            DigitRunModel(**asdict(run)) for run in longest_runs(digits, top, first_position=start)
        ],
        distribution=[RunLengthRowModel(**asdict(row)) for row in run_length_distribution(digits)],
        note=notes.RUNS_NOTE,
    )


@router.get("/observations", response_model=ObservationsResponse, tags=["analysis"])
def observations(
    store: StoreDep,
    state: StateDep,
    settings: SettingsDep,
    start: StartQuery = 1,
    count: CountQuery = None,
) -> ObservationsResponse:
    """Compute a short list of facts about a range for the overview dashboard.

    When ``count`` is omitted the range is the whole dataset, capped at the in-memory
    analysis limit; the response states the range actually analysed.
    """
    available = max(store.total_digits - start + 1, 1)
    resolved = count if count is not None else min(available, settings.max_statistics_digits)
    key = (start, resolved, store.manifest.updated_at)
    cached = state.observation_cache.get(key)
    if cached is not None:
        return cached
    digits = load_digits(store, settings, start, resolved)
    response = ObservationsResponse(
        range_start=start,
        range_end=start + int(digits.size) - 1,
        sample_size=int(digits.size),
        observations=build_observations(digits, start, settings.max_ngram_length),
        caveat=notes.OBSERVATIONS_CAVEAT,
    )
    if len(state.observation_cache) >= 16:
        state.observation_cache.clear()
    state.observation_cache[key] = response
    return response
