"""Append-only log of experiments run through the API, stored as JSON Lines."""

import json
import logging
import threading
import uuid
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path

logger = logging.getLogger(__name__)

_MAX_STORED = 2_000
_TRIM_TO = 1_000

type JsonValue = str | int | float | bool | list[JsonValue] | dict[str, JsonValue] | None


@dataclass(frozen=True, slots=True)
class Experiment:
    """One recorded analysis.

    Attributes:
        id: Unique identifier.
        timestamp: ISO 8601 UTC time the experiment finished.
        kind: ``search``, ``statistics``, ``ngrams`` or ``comparison``.
        title: Short human-readable description.
        parameters: Everything needed to repeat the experiment (range, pattern, seed).
        summary: Headline results.
    """

    id: str
    timestamp: str
    kind: str
    title: str
    parameters: dict[str, JsonValue]
    summary: dict[str, JsonValue]


class ExperimentLog:
    """Thread-safe JSONL experiment log. A missing or unreadable file reads as empty."""

    def __init__(self, path: Path) -> None:
        """Create a log backed by ``path`` (created on first write)."""
        self._path = path
        self._lock = threading.Lock()

    def record(
        self,
        kind: str,
        title: str,
        parameters: dict[str, JsonValue],
        summary: dict[str, JsonValue],
    ) -> Experiment:
        """Append an experiment and return it. Logging failures never fail the request."""
        experiment = Experiment(
            id=uuid.uuid4().hex,
            timestamp=datetime.now(UTC).isoformat(timespec="seconds"),
            kind=kind,
            title=title,
            parameters=parameters,
            summary=summary,
        )
        with self._lock:
            try:
                self._path.parent.mkdir(parents=True, exist_ok=True)
                with self._path.open("a", encoding="utf-8") as handle:
                    handle.write(json.dumps(asdict(experiment)) + "\n")
                self._trim_if_needed()
            except OSError:
                logger.exception("could not write experiment log at %s", self._path)
        return experiment

    def _read_all(self) -> list[Experiment]:
        if not self._path.is_file():
            return []
        experiments: list[Experiment] = []
        for line in self._path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                experiments.append(Experiment(**json.loads(line)))
            except (json.JSONDecodeError, TypeError):
                logger.warning("skipping malformed experiment log line")
        return experiments

    def _trim_if_needed(self) -> None:
        experiments = self._read_all()
        if len(experiments) <= _MAX_STORED:
            return
        kept = experiments[-_TRIM_TO:]
        temp_path = self._path.with_suffix(".jsonl.tmp")
        temp_path.write_text(
            "".join(json.dumps(asdict(item)) + "\n" for item in kept), encoding="utf-8"
        )
        temp_path.replace(self._path)

    def recent(self, limit: int, kind: str | None = None) -> list[Experiment]:
        """Return up to ``limit`` experiments, newest first, optionally of one kind."""
        with self._lock:
            experiments = self._read_all()
        if kind is not None:
            experiments = [item for item in experiments if item.kind == kind]
        return list(reversed(experiments[-limit:])) if limit > 0 else []

    def clear(self) -> None:
        """Delete every recorded experiment."""
        with self._lock:
            self._path.unlink(missing_ok=True)
