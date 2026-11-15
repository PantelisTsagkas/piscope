"""Schemas for sequence search."""

from pydantic import Field

from piscope_api.schemas.common import ApiModel


class SearchRequest(ApiModel):
    """Search for a digit sequence. Overlapping occurrences are all counted."""

    pattern: str = Field(
        min_length=1,
        pattern=r"^[0-9]+$",
        description="Digits to find, e.g. '314159'",
        examples=["314159"],
    )
    start: int = Field(default=1, ge=1, description="First position of the search range")
    end: int | None = Field(
        default=None, ge=1, description="Last position (inclusive); defaults to the last digit"
    )
    offset: int = Field(default=0, ge=0, description="Number of matches to skip")
    limit: int | None = Field(default=None, ge=1, description="Matches per page")


class SearchMatch(ApiModel):
    """One occurrence."""

    index: int = Field(description="0-based rank of this occurrence among all matches")
    position: int = Field(description="1-based position of the first digit of the match")
    gap_from_previous: int | None = Field(
        description="Distance from the previous occurrence's position; null for the first"
    )


class GapSummary(ApiModel):
    """Distances between consecutive occurrences."""

    count: int
    minimum: int
    maximum: int
    mean: float
    median: float
    expected_mean: float = Field(
        description="Mean gap expected for independent uniform digits: 10**len(pattern)"
    )


class SearchResponse(ApiModel):
    """A page of search results plus totals for the whole range."""

    pattern: str
    pattern_length: int
    range_start: int
    range_end: int
    total_count: int = Field(description="Occurrences in the whole range, overlaps included")
    expected_count: float = Field(
        description="Occurrences expected for independent uniform digits; a reference, not a test"
    )
    first_position: int | None
    last_position: int | None = Field(
        description="Last occurrence; null if none or if stored positions were truncated"
    )
    offset: int
    limit: int
    matches: list[SearchMatch]
    has_more: bool
    positions_truncated: bool = Field(
        description="True when there are more matches than the server keeps for paging"
    )
    pageable_count: int = Field(description="Number of matches reachable through paging")
    gaps: GapSummary | None
    elapsed_ms: float = Field(description="Time spent scanning the digits for this pattern")
    cached: bool = Field(description="True when this result was served from the search cache")
