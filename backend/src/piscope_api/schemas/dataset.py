"""Schemas for health, dataset metadata and digit retrieval."""

from pydantic import Field

from piscope_api.schemas.common import ApiModel


class HealthResponse(ApiModel):
    """Liveness and dataset availability."""

    status: str = Field(description="'ok' when a dataset is loaded, otherwise 'degraded'")
    api_version: str
    engine_version: str
    dataset_available: bool
    dataset_error: str | None = None


class VerificationInfo(ApiModel):
    """An independent check that was run on the digits before they were stored."""

    method: str
    digits_compared: int
    detail: str


class ChunkInfo(ApiModel):
    """One chunk file."""

    index: int
    first_position: int
    digit_count: int
    sha256: str
    complete: bool


class DatasetInfoResponse(ApiModel):
    """Provenance, size and conventions of the stored digits."""

    constant: str
    base: int
    integer_part: str = Field(description="The digit before the decimal point, not stored")
    total_digits: int = Field(description="Decimals available; also the largest valid position")
    first_position: int
    last_position: int
    chunk_size: int
    chunk_count: int
    has_partial_chunk: bool = Field(
        description="True when the final chunk holds fewer digits than chunk_size"
    )
    indexing: str
    encoding: str
    generator: dict[str, str | int]
    verifications: list[VerificationInfo]
    checksums_verified_at_startup: bool
    created_at: str
    updated_at: str
    chunks: list[ChunkInfo]
    limits: dict[str, int] = Field(description="Request limits enforced by this server")


class DigitResponse(ApiModel):
    """A single digit."""

    position: int
    digit: int = Field(ge=0, le=9)


class DigitRangeResponse(ApiModel):
    """A run of consecutive digits."""

    start: int
    end: int
    count: int
    digits: str = Field(description="The digits as a string; its first character is at 'start'")
    total_digits: int
    has_previous: bool
    has_next: bool
