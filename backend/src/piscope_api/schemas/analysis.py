"""Schemas for frequency analysis."""

from pydantic import Field

from piscope_api.schemas.common import ApiModel


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
