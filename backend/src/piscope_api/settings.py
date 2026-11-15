"""Runtime configuration, read from ``PISCOPE_*`` environment variables."""

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """API settings. Every limit that protects the server from heavy requests is here."""

    model_config = SettingsConfigDict(env_prefix="PISCOPE_", env_file=".env", extra="ignore")

    data_dir: Path = Field(default=Path("data"), description="Dataset directory")
    experiments_file: Path | None = Field(
        default=None, description="Experiment log (JSONL). Defaults to <data_dir>/experiments.jsonl"
    )
    verify_checksums_on_startup: bool = Field(
        default=True, description="Recompute chunk SHA-256 checksums when the API starts"
    )
    cors_origins: list[str] = Field(
        default=["http://localhost:3000", "http://127.0.0.1:3000"],
        description="Origins allowed to call the API from a browser",
    )

    max_range_digits: int = Field(default=10_000, ge=1, description="Digits per range request")
    max_pattern_length: int = Field(default=1_000, ge=1, description="Search pattern length")
    search_default_limit: int = Field(default=100, ge=1)
    search_max_limit: int = Field(default=1_000, ge=1, description="Matches per search page")
    search_max_stored_positions: int = Field(
        default=5_000_000, ge=1, description="Match positions kept per search for pagination"
    )
    search_cache_entries: int = Field(default=32, ge=0, description="Cached search results")

    max_analysis_digits: int = Field(
        default=100_000_000, ge=1, description="Digits per frequency request (streamed)"
    )
    max_statistics_digits: int = Field(
        default=10_000_000,
        ge=1,
        description="Digits per n-gram, statistics, window or run request (held in memory)",
    )
    max_ngram_length: int = Field(default=6, ge=1, le=7, description="Largest n for n-grams")
    max_ngram_rows: int = Field(default=1_000, ge=1, description="Rows per n-gram table page")
    max_autocorrelation_lag: int = Field(default=100, ge=1)
    max_random_digits: int = Field(
        default=10_000_000, ge=1, description="Digits per simulated random sequence"
    )
    max_simulations: int = Field(default=200, ge=1, description="Simulated sequences per request")
    max_simulated_total_digits: int = Field(
        default=50_000_000, ge=1, description="Simulated digits per request, all sequences"
    )
    max_windows: int = Field(default=200, ge=1, description="Windows per concentration request")
    max_experiments_returned: int = Field(default=100, ge=1)

    @property
    def experiments_path(self) -> Path:
        """Location of the experiment log."""
        return self.experiments_file or self.data_dir / "experiments.jsonl"
