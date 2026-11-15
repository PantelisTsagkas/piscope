"""Sequence search."""

import numpy as np
from fastapi import APIRouter

from piscope_api.errors import RequestLimitError
from piscope_api.schemas.search import GapSummary, SearchMatch, SearchRequest, SearchResponse
from piscope_api.state import SettingsDep, StateDep, StoreDep
from piscope_engine.search.sequence import SearchResult, gaps_between

router = APIRouter()


def _gap_summary(result: SearchResult) -> GapSummary | None:
    gaps = gaps_between(result.positions)
    if gaps.size == 0:
        return None
    return GapSummary(
        count=int(gaps.size),
        minimum=int(gaps.min()),
        maximum=int(gaps.max()),
        mean=float(gaps.mean()),
        median=float(np.median(gaps)),
        expected_mean=float(10 ** len(result.pattern)),
    )


@router.post("/search", response_model=SearchResponse, tags=["search"])
def search(
    request: SearchRequest, store: StoreDep, state: StateDep, settings: SettingsDep
) -> SearchResponse:
    """Find every occurrence of a digit sequence and return one page of positions.

    Position 1 is the first digit after the decimal point. Overlapping occurrences are
    counted separately. Only matches lying entirely inside ``start..end`` are reported.
    """
    if len(request.pattern) > settings.max_pattern_length:
        raise RequestLimitError(
            f"pattern has {len(request.pattern)} digits; the limit is {settings.max_pattern_length}"
        )
    default_limit = min(settings.search_default_limit, settings.search_max_limit)
    limit = request.limit if request.limit is not None else default_limit
    if limit > settings.search_max_limit:
        raise RequestLimitError(f"limit {limit} exceeds the maximum of {settings.search_max_limit}")
    end = request.end if request.end is not None else store.total_digits

    result, cached = state.search_cache.search(store, request.pattern, request.start, end)
    positions = result.positions
    page = positions[request.offset : request.offset + limit]
    matches: list[SearchMatch] = []
    for page_index, position in enumerate(page.tolist()):
        index = request.offset + page_index
        previous = int(positions[index - 1]) if index > 0 else None
        matches.append(
            SearchMatch(
                index=index,
                position=position,
                gap_from_previous=position - previous if previous is not None else None,
            )
        )

    if not cached and request.offset == 0:
        state.experiments.record(
            kind="search",
            title=f"Search for {_shorten(request.pattern)}",
            parameters={"pattern": request.pattern, "start": result.range_start, "end": end},
            summary={
                "total_count": result.total_count,
                "first_position": result.first_position,
                "expected_count": result.expected_count,
            },
        )

    has_last = positions.size > 0 and not result.positions_truncated
    return SearchResponse(
        pattern=result.pattern,
        pattern_length=len(result.pattern),
        range_start=result.range_start,
        range_end=result.range_end,
        total_count=result.total_count,
        expected_count=result.expected_count,
        first_position=result.first_position,
        last_position=int(positions[-1]) if has_last else None,
        offset=request.offset,
        limit=limit,
        matches=matches,
        has_more=request.offset + len(matches) < int(positions.size),
        positions_truncated=result.positions_truncated,
        pageable_count=int(positions.size),
        gaps=_gap_summary(result),
        elapsed_ms=result.elapsed_seconds * 1000,
        cached=cached,
    )


def _shorten(pattern: str, limit: int = 24) -> str:
    return pattern if len(pattern) <= limit else f"{pattern[:limit]}... ({len(pattern)} digits)"
