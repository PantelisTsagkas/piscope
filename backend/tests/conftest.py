"""Fixtures for API tests: a real app over the first 10,000 published decimals of pi."""

from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from piscope_api.main import create_app
from piscope_api.settings import Settings

from api_support import load_reference_text, write_test_dataset


@pytest.fixture(scope="session")
def pi_text() -> str:
    return load_reference_text()


@pytest.fixture
def settings(tmp_path: Path, pi_text: str) -> Settings:
    data_dir = tmp_path / "data"
    write_test_dataset(data_dir, pi_text, chunk_size=1_000)
    return Settings(data_dir=data_dir, max_range_digits=2_000, search_max_limit=50, _env_file=None)


@pytest.fixture
def client(settings: Settings) -> Iterator[TestClient]:
    with TestClient(create_app(settings)) as test_client:
        yield test_client
