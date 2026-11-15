"""Dataset manifest: the JSON metadata stored next to the binary chunk files."""

import json
import os
from dataclasses import asdict, dataclass, field
from pathlib import Path

from piscope_engine.errors import DatasetIntegrityError, DatasetNotFoundError

MANIFEST_FILENAME = "manifest.json"
FORMAT_VERSION = 1
ENCODING_DESCRIPTION = "one unsigned byte per decimal digit, values 0-9"
INDEXING_DESCRIPTION = (
    "position 1 is the first digit after the decimal point; the integer digit 3 is not stored"
)


@dataclass(frozen=True, slots=True)
class ChunkRecord:
    """Metadata for one chunk file.

    Attributes:
        index: 0-based chunk index.
        filename: File name relative to the dataset directory.
        digit_count: Number of digits in the file (equals its size in bytes).
        sha256: Hex SHA-256 of the file contents.
        complete: True when the chunk holds a full ``chunk_size`` digits. Only the
            final chunk of a dataset may be incomplete.
    """

    index: int
    filename: str
    digit_count: int
    sha256: str
    complete: bool


@dataclass(frozen=True, slots=True)
class VerificationRecord:
    """One independent check that was run against the digits before they were stored.

    Attributes:
        method: Short identifier, e.g. ``gauss-legendre`` or ``published-reference``.
        digits_compared: How many leading digits were compared.
        detail: Human-readable provenance (algorithm parameters, source URL, checksum).
    """

    method: str
    digits_compared: int
    detail: str


@dataclass(frozen=True, slots=True)
class DatasetManifest:
    """Everything known about a stored digit dataset.

    Attributes:
        format_version: Version of this manifest layout.
        constant: Name of the constant; always ``pi``.
        base: Numeric base of the stored digits; always 10.
        chunk_size: Digits per full chunk.
        total_digits: Digits available, counted from position 1.
        generator: Algorithm and parameters that produced the digits.
        verifications: Independent checks run before the digits were written.
        chunks: Per-chunk records in index order.
        created_at: ISO 8601 UTC timestamp of first creation.
        updated_at: ISO 8601 UTC timestamp of the last expansion.
        encoding: Description of the byte encoding.
        indexing: Description of the position convention.
    """

    format_version: int
    constant: str
    base: int
    chunk_size: int
    total_digits: int
    generator: dict[str, str | int]
    verifications: list[VerificationRecord]
    chunks: list[ChunkRecord]
    created_at: str
    updated_at: str
    encoding: str = ENCODING_DESCRIPTION
    indexing: str = INDEXING_DESCRIPTION
    notes: list[str] = field(default_factory=list)

    @property
    def has_partial_chunk(self) -> bool:
        """True when the final chunk holds fewer than ``chunk_size`` digits."""
        return bool(self.chunks) and not self.chunks[-1].complete

    def validate(self) -> None:
        """Check internal consistency of the manifest.

        Raises:
            DatasetIntegrityError: If counts, indices or flags contradict each other.
        """
        if self.format_version != FORMAT_VERSION:
            raise DatasetIntegrityError(f"unsupported manifest version {self.format_version}")
        if self.base != 10 or self.constant != "pi":
            raise DatasetIntegrityError("manifest does not describe base-10 digits of pi")
        if self.chunk_size < 1:
            raise DatasetIntegrityError(f"invalid chunk_size {self.chunk_size}")
        running_total = 0
        last_index = len(self.chunks) - 1
        for expected_index, chunk in enumerate(self.chunks):
            if chunk.index != expected_index:
                raise DatasetIntegrityError(
                    f"chunk records out of order: found index {chunk.index} at {expected_index}"
                )
            is_full = chunk.digit_count == self.chunk_size
            if chunk.complete != is_full:
                raise DatasetIntegrityError(f"chunk {chunk.index} has a wrong 'complete' flag")
            if not is_full and expected_index != last_index:
                raise DatasetIntegrityError(f"chunk {chunk.index} is partial but not the last")
            if not 0 < chunk.digit_count <= self.chunk_size:
                raise DatasetIntegrityError(f"chunk {chunk.index} has an invalid digit count")
            running_total += chunk.digit_count
        if running_total != self.total_digits:
            raise DatasetIntegrityError(
                f"total_digits is {self.total_digits} but chunks hold {running_total}"
            )


def manifest_path(data_dir: Path) -> Path:
    """Return the manifest location for a dataset directory."""
    return data_dir / MANIFEST_FILENAME


def load_manifest(data_dir: Path) -> DatasetManifest:
    """Read and validate the manifest of a dataset directory.

    Raises:
        DatasetNotFoundError: If no manifest exists.
        DatasetIntegrityError: If the manifest is malformed or inconsistent.
    """
    path = manifest_path(data_dir)
    if not path.is_file():
        raise DatasetNotFoundError(f"no dataset manifest at {path}")
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        manifest = DatasetManifest(
            format_version=int(raw["format_version"]),
            constant=str(raw["constant"]),
            base=int(raw["base"]),
            chunk_size=int(raw["chunk_size"]),
            total_digits=int(raw["total_digits"]),
            generator=dict(raw["generator"]),
            verifications=[VerificationRecord(**item) for item in raw["verifications"]],
            chunks=[ChunkRecord(**item) for item in raw["chunks"]],
            created_at=str(raw["created_at"]),
            updated_at=str(raw["updated_at"]),
            encoding=str(raw.get("encoding", ENCODING_DESCRIPTION)),
            indexing=str(raw.get("indexing", INDEXING_DESCRIPTION)),
            notes=list(raw.get("notes", [])),
        )
    except (json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
        raise DatasetIntegrityError(f"malformed manifest at {path}: {exc}") from exc
    manifest.validate()
    return manifest


def save_manifest(data_dir: Path, manifest: DatasetManifest) -> None:
    """Validate and atomically write a manifest (temp file, fsync, rename)."""
    manifest.validate()
    path = manifest_path(data_dir)
    temp_path = path.with_suffix(".json.tmp")
    payload = json.dumps(asdict(manifest), indent=2) + "\n"
    with temp_path.open("w", encoding="utf-8") as handle:
        handle.write(payload)
        handle.flush()
        os.fsync(handle.fileno())
    temp_path.replace(path)
