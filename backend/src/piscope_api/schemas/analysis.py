"""Schemas for frequency, n-gram, statistical and comparison endpoints."""

from typing import Any, Literal

from pydantic import Field

from piscope_api.schemas.common import ApiModel

TestKey = Literal["chi_square", "shannon_entropy", "autocorrelation", "runs", "ngram_blocks"]
ALL_TEST_KEYS: list[TestKey] = [
    "chi_square",
    "shannon_entropy",
    "autocorrelation",
    "runs",
    "ngram_blocks",
]


class DigitFrequencyModel(ApiModel):
    """Frequency of one digit."""

    digit: int
    count: int
    relative_frequency: float
    expected_count: float
    deviation: float = Field(description="count - expected_count")
    standardized_deviation: float = Field(
        description="Deviation in binomial standard deviations (a per-digit z-score)"
    )


class FrequencyResponse(ApiModel):
    """Digit frequencies for a position range."""

    range_start: int
    range_end: int
    sample_size: int
    expected_relative_frequency: float
    digits: list[DigitFrequencyModel]
    most_frequent: list[int]
    least_frequent: list[int]
    note: str


class TestResultModel(ApiModel):
    """Outcome of one statistical procedure."""

    key: str
    name: str
    statistic_name: str
    statistic: float
    expected_statistic: float | None
    expected_description: str
    p_value: float | None = Field(
        description=(
            "Probability, under the null model, of a statistic at least this extreme. "
            "Not the probability that any hypothesis is true. Null for descriptive measures."
        )
    )
    adjusted_p_value: float | None = Field(
        default=None, description="p-value after multiple-testing correction across this request"
    )
    degrees_of_freedom: int | None
    sample_size: int
    null_hypothesis: str
    interpretation: str
    assumptions: list[str]
    limitations: list[str]
    details: dict[str, Any]


class NgramRow(ApiModel):
    """Count of one n-gram."""

    ngram: str
    count: int
    deviation: float
    standardized_deviation: float


class NgramResponse(ApiModel):
    """N-gram frequency table for a position range."""

    length: int
    overlapping: bool
    range_start: int
    range_end: int
    windows: int = Field(description="Number of n-grams counted")
    possible: int = Field(description="Distinct n-grams that exist: 10**length")
    observed_distinct: int
    missing: int = Field(description="N-grams that never occur in the range")
    expected_count: float
    sort: str
    offset: int
    limit: int
    total_rows: int
    has_more: bool
    rows: list[NgramRow]
    most_common: list[NgramRow]
    least_common: list[NgramRow]
    matrix: list[list[int]] | None = Field(
        description="For length 2 only: 10x10 counts, matrix[first][second]"
    )
    block_test: TestResultModel | None = Field(
        description="Chi-square test on non-overlapping blocks of the same range"
    )
    note: str


class StatisticsRequest(ApiModel):
    """Run statistical tests on a range of digits."""

    start: int = Field(default=1, ge=1)
    count: int | None = Field(default=None, ge=1, description="Defaults to all digits from start")
    tests: list[TestKey] = Field(default_factory=lambda: list(ALL_TEST_KEYS), min_length=1)
    max_lag: int = Field(default=20, ge=1, description="Largest lag for autocorrelation")
    ngram_length: int = Field(default=2, ge=1, description="Block length for the n-gram test")
    runs_dichotomy: Literal["high_low", "parity"] = "high_low"
    correction: Literal["holm", "bonferroni"] = "holm"


class StatisticsResponse(ApiModel):
    """Results of a battery of tests."""

    range_start: int
    range_end: int
    sample_size: int
    results: list[TestResultModel]
    correction: str
    family_size: int = Field(description="Number of p-values the correction was applied to")
    multiple_testing_note: str
    scope_note: str
    elapsed_ms: float


class CompareRequest(ApiModel):
    """Compare a range of pi with simulated random digit sequences of the same length."""

    start: int = Field(default=1, ge=1)
    count: int = Field(default=100_000, ge=10, description="Digits in each sequence")
    seed: int | None = Field(
        default=None,
        ge=0,
        le=2**53 - 1,
        description=(
            "Random seed, at most 2**53 - 1 so that JavaScript clients can repeat it exactly; "
            "chosen and reported if omitted"
        ),
    )
    simulations: int = Field(default=20, ge=1, description="Number of simulated sequences")
    tests: list[TestKey] = Field(default_factory=lambda: list(ALL_TEST_KEYS), min_length=1)
    max_lag: int = Field(default=20, ge=1)
    ngram_length: int = Field(default=2, ge=1)
    runs_dichotomy: Literal["high_low", "parity"] = "high_low"


class RandomSourceModel(ApiModel):
    """Everything needed to regenerate the simulated sequences."""

    seed: int
    bit_generator: str
    numpy_version: str
    method: str


class SimulatedStatisticModel(ApiModel):
    """One statistic of pi placed among the simulated sequences."""

    key: str
    name: str
    statistic_name: str
    observed: float
    simulated: list[float]
    simulated_mean: float
    simulated_std: float
    simulated_min: float
    simulated_max: float
    fraction_at_or_below: float = Field(
        description="Share of simulations with a statistic <= pi's; an empirical percentile"
    )


class CompareResponse(ApiModel):
    """Pi versus simulated random sequences."""

    range_start: int
    range_end: int
    length: int
    simulations: int
    source: RandomSourceModel
    pi_results: list[TestResultModel]
    random_results: list[TestResultModel] = Field(
        description="Same tests on the first simulated sequence"
    )
    pi_counts: list[int]
    random_counts: list[int]
    statistics: list[SimulatedStatisticModel]
    note: str
    elapsed_ms: float


class WindowRow(ApiModel):
    """Digit counts in one window."""

    index: int
    start: int
    end: int
    counts: list[int]
    standardized: list[float]


class WindowResponse(ApiModel):
    """Digit concentration across consecutive windows."""

    range_start: int
    range_end: int
    window_size: int
    window_count: int
    rows: list[WindowRow]
    cells: int
    cells_beyond_two: int
    expected_cells_beyond_two: float
    cells_beyond_three: int
    expected_cells_beyond_three: float
    max_abs_z: float
    approximation_reliable: bool = Field(
        description="False when windows hold fewer than 50 digits and z-scores are unreliable"
    )
    note: str


class DigitRunModel(ApiModel):
    """A maximal block of one repeated digit."""

    digit: int
    length: int
    position: int


class RunLengthRowModel(ApiModel):
    """Observed and expected number of runs of one length."""

    length: int
    observed: int
    expected: float


class RunsResponse(ApiModel):
    """Runs of repeated digits."""

    range_start: int
    range_end: int
    longest: list[DigitRunModel]
    distribution: list[RunLengthRowModel]
    note: str


class Observation(ApiModel):
    """One computed fact about the analysed range."""

    key: str
    title: str
    value: str
    detail: str
    kind: Literal["descriptive", "test"]
    position: int | None = Field(default=None, description="Position this refers to, if any")
    length: int | None = Field(default=None, description="Length of the sequence at position")


class ObservationsResponse(ApiModel):
    """Computed observations for the dashboard."""

    range_start: int
    range_end: int
    sample_size: int
    observations: list[Observation]
    caveat: str
