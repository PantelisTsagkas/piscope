"""Writing and expanding digit datasets.

The writer consumes digits as a stream of blocks starting at position 1, cuts them into
fixed-size chunks and writes each chunk atomically. When a dataset already exists the
incoming stream must reproduce it exactly: every chunk that is already stored and
complete is compared by SHA-256 and left untouched, and only new (or previously
partial) chunks are written. A dataset is never shrunk.
"""

import hashlib
import logging
import os
from collections.abc import Iterable, Iterator
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
from numpy.typing import NDArray

from piscope_engine.digits.indexing import DEFAULT_CHUNK_SIZE, chunk_filename
from piscope_engine.digits.manifest import (
    FORMAT_VERSION,
    ChunkRecord,
    DatasetManifest,
    VerificationRecord,
    load_manifest,
    save_manifest,
)
from piscope_engine.digits.store import sha256_of_file
from piscope_engine.errors import DatasetIntegrityError, DatasetNotFoundError

logger = logging.getLogger(__name__)

type DigitArray = NDArray[np.uint8]


def _utc_now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def _require_digit_values(block: DigitArray) -> None:
    if block.dtype != np.uint8:
        raise ValueError(f"digit blocks must be uint8, got {block.dtype}")
    if block.size and int(block.max()) > 9:
        raise ValueError("digit blocks may only contain values 0-9")


def _rechunk(blocks: Iterable[DigitArray], chunk_size: int) -> Iterator[DigitArray]:
    """Regroup arbitrary blocks into arrays of exactly ``chunk_size`` (last may be short)."""
    pending: list[DigitArray] = []
    pending_size = 0
    for block in blocks:
        _require_digit_values(block)
        offset = 0
        while offset < block.size:
            take = min(chunk_size - pending_size, block.size - offset)
            pending.append(block[offset : offset + take])
            pending_size += take
            offset += take
            if pending_size == chunk_size:
                yield np.concatenate(pending)
                pending = []
                pending_size = 0
    if pending_size:
        yield np.concatenate(pending)


def _write_temp_chunk(path: Path, digits: DigitArray) -> Path:
    """Write digits next to ``path`` and return the temp file, ready to be renamed."""
    temp_path = path.with_suffix(".bin.tmp")
    with temp_path.open("wb") as handle:
        handle.write(digits.tobytes())
        handle.flush()
        os.fsync(handle.fileno())
    return temp_path


def _load_existing(data_dir: Path) -> DatasetManifest | None:
    try:
        return load_manifest(data_dir)
    except DatasetNotFoundError:
        return None


def write_dataset(
    data_dir: Path,
    blocks: Iterable[DigitArray],
    generator: dict[str, str | int],
    verifications: list[VerificationRecord],
    chunk_size: int = DEFAULT_CHUNK_SIZE,
) -> DatasetManifest:
    """Create a dataset, or expand an existing one, from a stream of digits.

    Args:
        data_dir: Dataset directory (created if missing).
        blocks: Digit arrays (uint8, values 0-9) that concatenate to the digits of pi
            starting at position 1.
        generator: Provenance of the digits (algorithm, parameters, library versions).
        verifications: Independent checks already performed on these digits.
        chunk_size: Digits per chunk. Must match an existing dataset.

    Returns:
        The manifest that was written.

    Raises:
        DatasetIntegrityError: If the stream disagrees with digits already stored, if a
            stored chunk is corrupt, or if the stream is shorter than the stored dataset.
        ValueError: If a block contains values outside 0-9 or the stream is empty.
    """
    data_dir.mkdir(parents=True, exist_ok=True)
    existing = _load_existing(data_dir)
    if existing is not None and existing.chunk_size != chunk_size:
        raise DatasetIntegrityError(
            f"existing dataset uses chunk_size {existing.chunk_size}, cannot write {chunk_size}"
        )
    existing_chunks = existing.chunks if existing is not None else []

    records: list[ChunkRecord] = []
    # A chunk that replaces a stored partial chunk is only renamed into place once the
    # whole stream has been accepted, so a failed expansion leaves the dataset readable.
    deferred_replacements: list[tuple[Path, Path]] = []
    total = 0
    try:
        total = _consume_stream(
            data_dir, blocks, chunk_size, existing_chunks, records, deferred_replacements
        )
        if total == 0:
            raise ValueError("cannot write an empty dataset")
        if existing is not None and total < existing.total_digits:
            raise DatasetIntegrityError(
                f"refusing to shrink dataset from {existing.total_digits} to {total} digits"
            )
    except BaseException:
        for temp_path, _ in deferred_replacements:
            temp_path.unlink(missing_ok=True)
        raise
    for temp_path, final_path in deferred_replacements:
        temp_path.replace(final_path)

    now = _utc_now()
    manifest = DatasetManifest(
        format_version=FORMAT_VERSION,
        constant="pi",
        base=10,
        chunk_size=chunk_size,
        total_digits=total,
        generator=generator,
        verifications=verifications,
        chunks=records,
        created_at=existing.created_at if existing is not None else now,
        updated_at=now,
    )
    save_manifest(data_dir, manifest)
    return manifest


def _consume_stream(
    data_dir: Path,
    blocks: Iterable[DigitArray],
    chunk_size: int,
    existing_chunks: list[ChunkRecord],
    records: list[ChunkRecord],
    deferred_replacements: list[tuple[Path, Path]],
) -> int:
    """Write every chunk of the stream and return the number of digits consumed."""
    total = 0
    for index, digits in enumerate(_rechunk(blocks, chunk_size)):
        filename = chunk_filename(index)
        path = data_dir / filename
        checksum = hashlib.sha256(digits.tobytes()).hexdigest()
        previous = existing_chunks[index] if index < len(existing_chunks) else None
        if previous is not None:
            _require_prefix_match(path, previous, digits, checksum)
        if previous is not None and previous.complete:
            logger.info("chunk %d already stored and verified, skipping", index)
        elif previous is not None:
            deferred_replacements.append((_write_temp_chunk(path, digits), path))
            logger.info(
                "chunk %d grows from %d to %d digits", index, previous.digit_count, digits.size
            )
        else:
            _write_temp_chunk(path, digits).replace(path)
            logger.info("wrote %s (%d digits)", filename, digits.size)
        records.append(
            ChunkRecord(
                index=index,
                filename=filename,
                digit_count=int(digits.size),
                sha256=checksum,
                complete=digits.size == chunk_size,
            )
        )
        total += int(digits.size)
    return total


def _require_prefix_match(
    path: Path, previous: ChunkRecord, digits: DigitArray, checksum: str
) -> None:
    """Check that incoming digits reproduce a chunk that is already on disk."""
    if sha256_of_file(path) != previous.sha256:
        raise DatasetIntegrityError(f"stored chunk {previous.filename} fails its checksum")
    if digits.size < previous.digit_count:
        raise DatasetIntegrityError(
            f"incoming digits are shorter than stored chunk {previous.filename}"
        )
    if previous.complete:
        matches = checksum == previous.sha256
    else:
        prefix = digits[: previous.digit_count].tobytes()
        matches = hashlib.sha256(prefix).hexdigest() == previous.sha256
    if not matches:
        raise DatasetIntegrityError(
            f"incoming digits disagree with stored chunk {previous.filename}; "
            "nothing was changed in that chunk"
        )
