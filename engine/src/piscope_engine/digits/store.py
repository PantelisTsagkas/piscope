"""Read-only, memory-mapped access to a stored digit dataset."""

import hashlib
import threading
from collections import OrderedDict
from collections.abc import Iterator
from pathlib import Path

import numpy as np
from numpy.typing import NDArray

from piscope_engine.digits.indexing import chunk_first_position, position_to_address
from piscope_engine.digits.manifest import ChunkRecord, DatasetManifest, load_manifest
from piscope_engine.errors import DatasetIntegrityError, PositionOutOfRangeError

type DigitArray = NDArray[np.uint8]

_HASH_BLOCK_BYTES = 1 << 20
_DEFAULT_MAX_OPEN_CHUNKS = 64


def sha256_of_file(path: Path) -> str:
    """Return the hex SHA-256 of a file, read in fixed-size blocks."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while block := handle.read(_HASH_BLOCK_BYTES):
            digest.update(block)
    return digest.hexdigest()


def digits_to_text(digits: DigitArray) -> str:
    """Render digit values 0-9 as a string of ASCII digits."""
    return (digits + ord("0")).astype(np.uint8).tobytes().decode("ascii")


class DigitStore:
    """Random access to the stored decimal digits of pi.

    Chunks are memory-mapped lazily and kept in a small least-recently-used cache, so
    memory use and open file handles stay bounded however large the dataset grows.
    All positions are 1-based: position 1 is the first digit after the decimal point.
    Instances are safe to share between threads.

    Opening a store checks the manifest and the size of every chunk file. Checksums are
    not recomputed on open (that reads every byte); call :meth:`verify_checksums`.
    """

    def __init__(self, data_dir: Path, max_open_chunks: int = _DEFAULT_MAX_OPEN_CHUNKS) -> None:
        """Open the dataset stored in ``data_dir``.

        Raises:
            DatasetNotFoundError: If the directory has no manifest.
            DatasetIntegrityError: If a chunk file is missing or has the wrong size.
        """
        if max_open_chunks < 1:
            raise ValueError("max_open_chunks must be >= 1")
        self._data_dir = data_dir
        self._manifest = load_manifest(data_dir)
        self._max_open_chunks = max_open_chunks
        self._open_chunks: OrderedDict[int, np.memmap] = OrderedDict()
        self._cache_lock = threading.Lock()
        for chunk in self._manifest.chunks:
            self._check_chunk_file(chunk)

    @property
    def manifest(self) -> DatasetManifest:
        """The dataset manifest loaded when the store was opened."""
        return self._manifest

    @property
    def data_dir(self) -> Path:
        """Directory holding the manifest and chunk files."""
        return self._data_dir

    @property
    def total_digits(self) -> int:
        """Number of digits available, i.e. the largest valid position."""
        return self._manifest.total_digits

    @property
    def chunk_size(self) -> int:
        """Digits per full chunk."""
        return self._manifest.chunk_size

    @property
    def chunk_count(self) -> int:
        """Number of chunk files in the dataset."""
        return len(self._manifest.chunks)

    def _check_chunk_file(self, chunk: ChunkRecord) -> None:
        path = self._data_dir / chunk.filename
        if not path.is_file():
            raise DatasetIntegrityError(f"chunk file missing: {path}")
        actual_size = path.stat().st_size
        if actual_size != chunk.digit_count:
            raise DatasetIntegrityError(
                f"{path} holds {actual_size} bytes, manifest says {chunk.digit_count}"
            )

    def chunk_view(self, chunk_index: int) -> np.memmap:
        """Return a read-only memory map of one chunk.

        Raises:
            PositionOutOfRangeError: If the chunk does not exist.
        """
        if not 0 <= chunk_index < self.chunk_count:
            raise PositionOutOfRangeError(
                f"chunk {chunk_index} does not exist (dataset has {self.chunk_count})"
            )
        with self._cache_lock:
            cached = self._open_chunks.get(chunk_index)
            if cached is not None:
                self._open_chunks.move_to_end(chunk_index)
                return cached
            record = self._manifest.chunks[chunk_index]
            view = np.memmap(
                self._data_dir / record.filename,
                dtype=np.uint8,
                mode="r",
                shape=(record.digit_count,),
            )
            self._open_chunks[chunk_index] = view
            if len(self._open_chunks) > self._max_open_chunks:
                self._open_chunks.popitem(last=False)
            return view

    def _require_range(self, start: int, count: int) -> None:
        if count < 0:
            raise ValueError(f"count must be >= 0, got {count}")
        if start < 1:
            raise PositionOutOfRangeError(f"positions start at 1, got {start}")
        last = start + count - 1
        if last > self.total_digits:
            raise PositionOutOfRangeError(
                f"range {start}..{last} exceeds the {self.total_digits} available digits"
            )

    def get_digit(self, position: int) -> int:
        """Return the digit at a 1-based position.

        Raises:
            PositionOutOfRangeError: If the position is outside ``1..total_digits``.
        """
        self._require_range(position, 1)
        address = position_to_address(position, self.chunk_size)
        return int(self.chunk_view(address.chunk_index)[address.offset])

    def get_range(self, start: int, count: int) -> DigitArray:
        """Return ``count`` digits beginning at 1-based position ``start``.

        The range may span any number of chunk boundaries. The result is an in-memory
        copy, so callers should bound ``count``; use :meth:`iter_blocks` to stream.

        Raises:
            PositionOutOfRangeError: If any requested position is unavailable.
        """
        self._require_range(start, count)
        result = np.empty(count, dtype=np.uint8)
        written = 0
        while written < count:
            address = position_to_address(start + written, self.chunk_size)
            view = self.chunk_view(address.chunk_index)
            take = min(count - written, len(view) - address.offset)
            result[written : written + take] = view[address.offset : address.offset + take]
            written += take
        return result

    def get_text(self, start: int, count: int) -> str:
        """Return ``count`` digits from ``start`` as a string of ASCII digits."""
        return digits_to_text(self.get_range(start, count))

    def iter_blocks(
        self, start: int, count: int, block_size: int = 1_000_000
    ) -> Iterator[tuple[int, DigitArray]]:
        """Yield ``(first_position, digits)`` blocks covering a range in order.

        Lets analyses stream over large ranges with bounded memory.

        Raises:
            PositionOutOfRangeError: If any requested position is unavailable.
        """
        if block_size < 1:
            raise ValueError("block_size must be >= 1")
        self._require_range(start, count)
        done = 0
        while done < count:
            take = min(block_size, count - done)
            yield start + done, self.get_range(start + done, take)
            done += take

    def chunk_first_position(self, chunk_index: int) -> int:
        """Return the 1-based position of the first digit in a chunk."""
        return chunk_first_position(chunk_index, self.chunk_size)

    def verify_checksums(self) -> None:
        """Recompute every chunk's SHA-256 and compare with the manifest.

        Raises:
            DatasetIntegrityError: On the first chunk whose checksum does not match.
        """
        for chunk in self._manifest.chunks:
            self._check_chunk_file(chunk)
            actual = sha256_of_file(self._data_dir / chunk.filename)
            if actual != chunk.sha256:
                raise DatasetIntegrityError(
                    f"checksum mismatch for {chunk.filename}: "
                    f"expected {chunk.sha256}, found {actual}"
                )

    def close(self) -> None:
        """Drop all cached memory maps."""
        with self._cache_lock:
            self._open_chunks.clear()
