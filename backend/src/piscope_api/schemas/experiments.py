"""Schemas for the experiment log."""

from typing import Any

from piscope_api.schemas.common import ApiModel


class ExperimentModel(ApiModel):
    """One recorded experiment."""

    id: str
    timestamp: str
    kind: str
    title: str
    parameters: dict[str, Any]
    summary: dict[str, Any]


class ExperimentListResponse(ApiModel):
    """Recent experiments, newest first."""

    experiments: list[ExperimentModel]
