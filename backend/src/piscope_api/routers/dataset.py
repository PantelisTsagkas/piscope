"""Health, dataset metadata and digit retrieval."""

from typing import Annotated

from fastapi import APIRouter, Query

from piscope_api import __version__ as api_version
from piscope_api.errors import RequestLimitError
from piscope_api.schemas.dataset import (
    ChunkInfo,
    DatasetInfoResponse,
    DigitRangeResponse,
    DigitResponse,
    HealthResponse,
    VerificationInfo,
)
from piscope_api.state import SettingsDep, StateDep, StoreDep
from piscope_engine import __version__ as engine_version

router = APIRouter()


@router.get("/health", response_model=HealthResponse, tags=["system"])
def health(state: StateDep) -> HealthResponse:
    """Report whether the API is up and a dataset is loaded."""
    return HealthResponse(
        status="ok" if state.store is not None else "degraded",
        api_version=api_version,
        engine_version=engine_version,
        dataset_available=state.store is not None,
        dataset_error=state.store_error,
    )


@router.get("/dataset/info", response_model=DatasetInfoResponse, tags=["dataset"])
def dataset_info(store: StoreDep, state: StateDep, settings: SettingsDep) -> DatasetInfoResponse:
    """Describe the stored digits: size, provenance, verification and conventions."""
    manifest = store.manifest
    return DatasetInfoResponse(
        constant=manifest.constant,
        base=manifest.base,
        integer_part="3",
        total_digits=manifest.total_digits,
        first_position=1,
        last_position=manifest.total_digits,
        chunk_size=manifest.chunk_size,
        chunk_count=len(manifest.chunks),
        has_partial_chunk=manifest.has_partial_chunk,
        indexing=manifest.indexing,
        encoding=manifest.encoding,
        generator=manifest.generator,
        verifications=[
            VerificationInfo(method=v.method, digits_compared=v.digits_compared, detail=v.detail)
            for v in manifest.verifications
        ],
        checksums_verified_at_startup=state.checksums_verified,
        created_at=manifest.created_at,
        updated_at=manifest.updated_at,
        chunks=[
            ChunkInfo(
                index=chunk.index,
                first_position=store.chunk_first_position(chunk.index),
                digit_count=chunk.digit_count,
                sha256=chunk.sha256,
                complete=chunk.complete,
            )
            for chunk in manifest.chunks
        ],
        limits={
            "max_range_digits": settings.max_range_digits,
            "max_pattern_length": settings.max_pattern_length,
            "search_max_limit": settings.search_max_limit,
            "max_analysis_digits": settings.max_analysis_digits,
            "max_statistics_digits": settings.max_statistics_digits,
            "max_simulations": settings.max_simulations,
            "max_simulated_total_digits": settings.max_simulated_total_digits,
            "max_windows": settings.max_windows,
            "max_ngram_length": settings.max_ngram_length,
            "max_autocorrelation_lag": settings.max_autocorrelation_lag,
            "max_random_digits": settings.max_random_digits,
        },
    )


@router.get("/digits", response_model=DigitResponse, tags=["digits"])
def get_digit(
    store: StoreDep,
    position: Annotated[
        int, Query(ge=1, description="1-based position; 1 is the first digit after the point")
    ],
) -> DigitResponse:
    """Return the digit at one position."""
    return DigitResponse(position=position, digit=store.get_digit(position))


@router.get("/digits/range", response_model=DigitRangeResponse, tags=["digits"])
def get_digit_range(
    store: StoreDep,
    settings: SettingsDep,
    start: Annotated[int, Query(ge=1, description="1-based position of the first digit")] = 1,
    count: Annotated[int, Query(ge=1, description="Number of digits to return")] = 1_000,
) -> DigitRangeResponse:
    """Return ``count`` consecutive digits beginning at ``start``."""
    if count > settings.max_range_digits:
        raise RequestLimitError(
            f"count {count} exceeds the limit of {settings.max_range_digits} digits per request"
        )
    digits = store.get_text(start, count)
    end = start + count - 1
    return DigitRangeResponse(
        start=start,
        end=end,
        count=count,
        digits=digits,
        total_digits=store.total_digits,
        has_previous=start > 1,
        has_next=end < store.total_digits,
    )
