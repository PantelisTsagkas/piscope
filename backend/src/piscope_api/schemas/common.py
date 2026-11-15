"""Schemas shared by several endpoints."""

from pydantic import BaseModel, ConfigDict, Field


class ApiModel(BaseModel):
    """Base class: immutable, and unknown request fields are rejected."""

    model_config = ConfigDict(frozen=True, extra="forbid")


class ErrorDetail(ApiModel):
    """Machine-readable error."""

    code: str
    message: str
    details: object | None = None


class ErrorResponse(ApiModel):
    """Envelope returned for every non-2xx response."""

    error: ErrorDetail


class PositionRange(ApiModel):
    """An inclusive range of 1-based decimal positions."""

    start: int = Field(ge=1, description="First position (1 is the first digit after the point)")
    end: int = Field(ge=1, description="Last position, inclusive")
