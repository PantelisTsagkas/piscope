"""Application state and FastAPI dependencies."""

import logging
from dataclasses import dataclass, field
from typing import Annotated

from fastapi import Depends, Request

from piscope_api.errors import DatasetUnavailableError
from piscope_api.schemas.analysis import ObservationsResponse
from piscope_api.services.experiments import ExperimentLog
from piscope_api.services.search_cache import SearchCache
from piscope_api.settings import Settings
from piscope_engine.digits.store import DigitStore
from piscope_engine.errors import PiScopeError

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class AppState:
    """Objects shared by all requests.

    Attributes:
        settings: Runtime configuration.
        store: The open dataset, or None when it could not be opened.
        store_error: Why the dataset is unavailable, when ``store`` is None.
        checksums_verified: True when every chunk passed its SHA-256 check at startup.
        search_cache: Cache of recent search results.
        experiments: Experiment log.
        observation_cache: Dashboard observations keyed by range and dataset version.
    """

    settings: Settings
    store: DigitStore | None
    store_error: str | None
    checksums_verified: bool
    search_cache: SearchCache
    experiments: ExperimentLog
    observation_cache: dict[tuple[int, int, str], ObservationsResponse] = field(
        default_factory=dict
    )


def build_state(settings: Settings) -> AppState:
    """Open the dataset and create shared services. Never raises for a bad dataset."""
    store: DigitStore | None = None
    store_error: str | None = None
    checksums_verified = False
    try:
        store = DigitStore(settings.data_dir)
        if settings.verify_checksums_on_startup:
            store.verify_checksums()
            checksums_verified = True
    except PiScopeError as exc:
        store = None
        store_error = str(exc)
        logger.error("dataset unavailable: %s", exc)
    return AppState(
        settings=settings,
        store=store,
        store_error=store_error,
        checksums_verified=checksums_verified,
        search_cache=SearchCache(
            settings.search_cache_entries, settings.search_max_stored_positions
        ),
        experiments=ExperimentLog(settings.experiments_path),
    )


def get_state(request: Request) -> AppState:
    """Return the shared application state."""
    return request.app.state.piscope


def get_settings(state: Annotated[AppState, Depends(get_state)]) -> Settings:
    """Return runtime settings."""
    return state.settings


def get_store(state: Annotated[AppState, Depends(get_state)]) -> DigitStore:
    """Return the open dataset or fail with 503."""
    if state.store is None:
        raise DatasetUnavailableError(
            f"{state.store_error}. Generate the dataset with "
            "'uv run piscope-digits generate --digits 1000000' and restart the API."
        )
    return state.store


StateDep = Annotated[AppState, Depends(get_state)]
SettingsDep = Annotated[Settings, Depends(get_settings)]
StoreDep = Annotated[DigitStore, Depends(get_store)]
