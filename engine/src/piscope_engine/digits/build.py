"""Generate, verify and store a digit dataset in one step."""

import hashlib
import logging
from collections.abc import Iterator
from importlib.metadata import version
from pathlib import Path

import numpy as np
from numpy.typing import NDArray

from piscope_engine.digits.generation import (
    DEFAULT_GUARD_DIGITS,
    chudnovsky_digits,
    chudnovsky_term_count,
    gauss_legendre_digits,
)
from piscope_engine.digits.indexing import DEFAULT_CHUNK_SIZE
from piscope_engine.digits.manifest import DatasetManifest, VerificationRecord
from piscope_engine.digits.reference import (
    REFERENCE_CHUNK_SHA256,
    REFERENCE_CHUNK_SIZE,
    REFERENCE_SOURCE,
)
from piscope_engine.digits.writer import write_dataset
from piscope_engine.errors import VerificationError

logger = logging.getLogger(__name__)

type DigitArray = NDArray[np.uint8]

_TEXT_BLOCK_CHARS = 1 << 20


def first_mismatch(left: DigitArray, right: DigitArray) -> int | None:
    """Return the 1-based position of the first differing digit, or None if equal.

    Only the common prefix is compared.
    """
    length = min(left.size, right.size)
    differing = np.flatnonzero(left[:length] != right[:length])
    if differing.size == 0:
        return None
    return int(differing[0]) + 1


def iter_digits_from_text(path: Path) -> Iterator[DigitArray]:
    """Stream the decimals of pi from a text file.

    The file may start with ``3.`` and may contain whitespace; both are ignored. Any
    other character is an error. If the file does not start with ``3.`` it is assumed
    to begin at position 1.

    Raises:
        VerificationError: If the file contains unexpected characters.
    """
    first_block = True
    with path.open("r", encoding="ascii") as handle:
        while block := handle.read(_TEXT_BLOCK_CHARS):
            if first_block:
                stripped = block.lstrip()
                if stripped.startswith("3."):
                    block = stripped[2:]
                first_block = False
            compact = "".join(block.split())
            if not compact:
                continue
            if not compact.isascii() or not compact.isdigit():
                raise VerificationError(f"{path} contains non-digit characters")
            yield (np.frombuffer(compact.encode("ascii"), dtype=np.uint8) - ord("0")).astype(
                np.uint8
            )


def verify_against_text(digits: DigitArray, path: Path, source: str) -> VerificationRecord:
    """Compare digits with a published reference file.

    Args:
        digits: Digits starting at position 1.
        path: Reference text file.
        source: Where the file came from (URL or citation), recorded in the manifest.

    Returns:
        A record of the comparison, including the reference file's SHA-256.

    Raises:
        VerificationError: On the first mismatch, or if nothing could be compared.
    """
    compared = 0
    for block in iter_digits_from_text(path):
        take = min(block.size, digits.size - compared)
        if take <= 0:
            break
        mismatch = first_mismatch(digits[compared : compared + take], block[:take])
        if mismatch is not None:
            raise VerificationError(
                f"digits disagree with reference {source} at position {compared + mismatch}"
            )
        compared += take
    if compared == 0:
        raise VerificationError(f"reference file {path} contained no digits")
    file_hash = hashlib.sha256(path.read_bytes()).hexdigest()
    return VerificationRecord(
        method="published-reference",
        digits_compared=compared,
        detail=f"source: {source}; file sha256: {file_hash}",
    )


def verify_against_known_checksums(digits: DigitArray) -> list[VerificationRecord]:
    """Compare leading million-digit blocks with checksums of published digit files.

    Only blocks that are fully covered by ``digits`` and have a shipped reference
    checksum are compared, so short datasets produce no record.

    Raises:
        VerificationError: If a covered block does not match its published checksum.
    """
    compared = 0
    for index, expected in sorted(REFERENCE_CHUNK_SHA256.items()):
        begin = index * REFERENCE_CHUNK_SIZE
        end = begin + REFERENCE_CHUNK_SIZE
        if digits.size < end:
            break
        actual = hashlib.sha256(digits[begin:end].tobytes()).hexdigest()
        if actual != expected:
            raise VerificationError(
                f"positions {begin + 1}..{end} do not match the published checksum; nothing written"
            )
        compared = end
    if compared == 0:
        return []
    return [
        VerificationRecord(
            method="published-checksum",
            digits_compared=compared,
            detail=f"SHA-256 comparison against {REFERENCE_SOURCE}",
        )
    ]


def build_dataset(
    data_dir: Path,
    total_digits: int,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    guard_digits: int = DEFAULT_GUARD_DIGITS,
    reference_file: Path | None = None,
    reference_source: str | None = None,
) -> DatasetManifest:
    """Generate ``total_digits`` decimals of pi, verify them and store them.

    The digits come from Chudnovsky binary splitting and are compared in full against
    an independent Gauss-Legendre computation before anything is written. If a dataset
    already exists in ``data_dir`` it is expanded: stored chunks are checked against the
    new computation by checksum and only new chunks are written.

    Args:
        data_dir: Dataset directory.
        total_digits: Number of decimals to store, counted from position 1.
        chunk_size: Digits per chunk.
        guard_digits: Extra working digits used by both algorithms.
        reference_file: Optional published digit file for a third comparison.
        reference_source: Citation or URL for ``reference_file``.

    Returns:
        The manifest of the stored dataset.

    Raises:
        VerificationError: If the two algorithms or the reference disagree.
        DatasetIntegrityError: If the result contradicts digits already stored.
    """
    digits = chudnovsky_digits(total_digits, guard_digits)
    check = gauss_legendre_digits(total_digits, guard_digits)
    mismatch = first_mismatch(digits, check)
    if mismatch is not None or check.size != digits.size:
        raise VerificationError(
            f"Chudnovsky and Gauss-Legendre disagree at position {mismatch}; nothing written"
        )
    verifications = [
        VerificationRecord(
            method="gauss-legendre",
            digits_compared=total_digits,
            detail=(
                "independent Gauss-Legendre (Brent-Salamin) AGM iteration in fixed-point "
                f"integer arithmetic, {guard_digits} guard digits, all digits compared"
            ),
        )
    ]
    verifications.extend(verify_against_known_checksums(digits))
    if reference_file is not None:
        source = reference_source or str(reference_file)
        verifications.append(verify_against_text(digits, reference_file, source))

    generator: dict[str, str | int] = {
        "algorithm": "chudnovsky-binary-splitting",
        "terms": chudnovsky_term_count(total_digits, guard_digits),
        "guard_digits": guard_digits,
        "rounding": "truncated, not rounded",
        "arithmetic": f"gmpy2 {version('gmpy2')}",
        "engine_version": version("piscope-engine"),
    }
    return write_dataset(
        data_dir, [digits], generator=generator, verifications=verifications, chunk_size=chunk_size
    )
