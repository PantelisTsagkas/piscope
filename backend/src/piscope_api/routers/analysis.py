"""Frequency and statistical analysis endpoints."""

from typing import Annotated

from fastapi import APIRouter, Query

from piscope_api.errors import RequestLimitError
from piscope_api.schemas.analysis import DigitFrequencyModel, FrequencyResponse
from piscope_api.settings import Settings
from piscope_api.state import SettingsDep, StoreDep
from piscope_engine.digits.store import DigitStore
from piscope_engine.statistics.frequency import analyze_frequency

router = APIRouter(prefix="/analysis")

FREQUENCY_NOTE = (
    "Expected counts assume each digit is equally likely (1/10). Deviations of a few "
    "standard deviations are normal in any finite sample; see the chi-square test in the "
    "Statistical Lab for a single test of the whole distribution."
)


def resolve_range(
    store: DigitStore, settings: Settings, start: int, count: int | None
) -> tuple[int, int]:
    """Fill in a default count (to the end of the dataset) and enforce the size limit."""
    resolved = count if count is not None else store.total_digits - start + 1
    if resolved > settings.max_analysis_digits:
        raise RequestLimitError(
            f"count {resolved} exceeds the limit of {settings.max_analysis_digits} digits"
        )
    return start, resolved


@router.get("/frequency", response_model=FrequencyResponse, tags=["analysis"])
def frequency(
    store: StoreDep,
    settings: SettingsDep,
    start: Annotated[int, Query(ge=1, description="First position to analyse")] = 1,
    count: Annotated[
        int | None, Query(ge=1, description="Digits to analyse; defaults to all that follow")
    ] = None,
) -> FrequencyResponse:
    """Count each digit 0-9 in a range and compare with a uniform model."""
    start, resolved = resolve_range(store, settings, start, count)
    analysis = analyze_frequency(store, start, resolved)
    return FrequencyResponse(
        range_start=analysis.range_start,
        range_end=analysis.range_end,
        sample_size=analysis.sample_size,
        expected_relative_frequency=0.1,
        digits=[
            DigitFrequencyModel(
                digit=entry.digit,
                count=entry.count,
                relative_frequency=entry.relative_frequency,
                expected_count=entry.expected_count,
                deviation=entry.deviation,
                standardized_deviation=entry.standardized_deviation,
            )
            for entry in analysis.digits
        ],
        most_frequent=analysis.most_frequent,
        least_frequent=analysis.least_frequent,
        note=FREQUENCY_NOTE,
    )
