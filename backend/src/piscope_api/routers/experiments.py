"""Experiment log endpoints."""

from dataclasses import asdict
from typing import Annotated

from fastapi import APIRouter, Query, Response

from piscope_api.schemas.experiments import ExperimentListResponse, ExperimentModel
from piscope_api.state import SettingsDep, StateDep

router = APIRouter()


@router.get("/experiments", response_model=ExperimentListResponse, tags=["experiments"])
def list_experiments(
    state: StateDep,
    settings: SettingsDep,
    limit: Annotated[int, Query(ge=1, description="Maximum experiments to return")] = 20,
    kind: Annotated[str | None, Query(description="Filter by experiment kind")] = None,
) -> ExperimentListResponse:
    """Return recent experiments, newest first."""
    capped = min(limit, settings.max_experiments_returned)
    return ExperimentListResponse(
        experiments=[
            ExperimentModel(**asdict(item)) for item in state.experiments.recent(capped, kind)
        ]
    )


@router.delete("/experiments", status_code=204, tags=["experiments"])
def clear_experiments(state: StateDep) -> Response:
    """Delete the experiment log."""
    state.experiments.clear()
    return Response(status_code=204)
