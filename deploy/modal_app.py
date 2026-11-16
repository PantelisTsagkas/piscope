"""Hosted PiScope API on Modal.

Deploy from the repository root:  uv run modal deploy deploy/modal_app.py
Remove:                           uv run modal app stop piscope-api

The image installs the exact versions in uv.lock, then generates and verifies the first
million digits at build time, so a cold start only has to open the files. One container
at most, scaled to zero when idle. The experiment log lives on the container's own disk:
it is shared by everyone using the site and disappears when the container stops.
"""

from pathlib import Path
from typing import TYPE_CHECKING

import modal

if TYPE_CHECKING:
    from fastapi import FastAPI

REPO_ROOT = Path(__file__).resolve().parent.parent
APP_DIR = "/app"
DATA_DIR = "/data"
DIGITS = 1_000_000

# Browser origins allowed to call the API: the deployed interface.
WEB_ORIGINS = '["https://piscope.vercel.app"]'

# The local defaults assume one trusted user. A public URL gets tighter ceilings.
PUBLIC_LIMITS = {
    "PISCOPE_MAX_ANALYSIS_DIGITS": "1000000",
    "PISCOPE_MAX_STATISTICS_DIGITS": "1000000",
    "PISCOPE_MAX_RANDOM_DIGITS": "1000000",
    "PISCOPE_MAX_SIMULATIONS": "50",
    "PISCOPE_MAX_SIMULATED_TOTAL_DIGITS": "10000000",
    "PISCOPE_SEARCH_MAX_STORED_POSITIONS": "1000000",
}

SOURCE_IGNORE = ["**/__pycache__", "**/tests", "**/benchmarks", "**/*.egg-info"]

image = (
    modal.Image.debian_slim(python_version="3.12")
    .pip_install("uv==0.11.7")
    .add_local_file(REPO_ROOT / "pyproject.toml", f"{APP_DIR}/pyproject.toml", copy=True)
    .add_local_file(REPO_ROOT / "uv.lock", f"{APP_DIR}/uv.lock", copy=True)
    .add_local_dir(REPO_ROOT / "engine", f"{APP_DIR}/engine", copy=True, ignore=SOURCE_IGNORE)
    .add_local_dir(REPO_ROOT / "backend", f"{APP_DIR}/backend", copy=True, ignore=SOURCE_IGNORE)
    .run_commands(
        # Third-party packages at the locked versions, then the two workspace packages.
        f"cd {APP_DIR} && uv export --frozen --no-dev --package piscope-api"
        " --no-emit-workspace --no-hashes -o /tmp/requirements.txt",
        "uv pip install --system --compile-bytecode -r /tmp/requirements.txt",
        f"uv pip install --system --compile-bytecode --no-deps {APP_DIR}/engine {APP_DIR}/backend",
        f"piscope-digits --data-dir {DATA_DIR} generate --digits {DIGITS}",
    )
    .env(
        {
            "PISCOPE_DATA_DIR": DATA_DIR,
            "PISCOPE_EXPERIMENTS_FILE": "/tmp/piscope-experiments.jsonl",
            "PISCOPE_CORS_ORIGINS": WEB_ORIGINS,
            **PUBLIC_LIMITS,
        }
    )
)

app = modal.App("piscope-api", image=image)


@app.function(max_containers=1, scaledown_window=300, timeout=60, cpu=1.0, memory=1024)
@modal.concurrent(max_inputs=16)
@modal.asgi_app()
def api() -> "FastAPI":
    """Build the FastAPI application inside the container."""
    from piscope_api.main import create_app

    return create_app()
