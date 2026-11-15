"""Command-line entry point for managing digit datasets: ``piscope-digits``."""

import argparse
import logging
import sys
import time
from pathlib import Path

from piscope_engine.digits.build import build_dataset
from piscope_engine.digits.indexing import DEFAULT_CHUNK_SIZE
from piscope_engine.digits.store import DigitStore
from piscope_engine.errors import PiScopeError

logger = logging.getLogger("piscope_engine.cli")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="piscope-digits", description="Generate and verify stored decimal digits of pi."
    )
    parser.add_argument("--data-dir", type=Path, default=Path("data"), help="dataset directory")
    commands = parser.add_subparsers(dest="command", required=True)

    generate = commands.add_parser("generate", help="generate or expand the dataset")
    generate.add_argument("--digits", type=int, default=1_000_000, help="total decimals to store")
    generate.add_argument("--chunk-size", type=int, default=DEFAULT_CHUNK_SIZE)
    generate.add_argument("--reference-file", type=Path, help="published digit file to compare")
    generate.add_argument("--reference-source", help="URL or citation for the reference file")

    commands.add_parser("verify", help="recompute and check every chunk checksum")
    commands.add_parser("info", help="print a summary of the stored dataset")
    return parser


def _generate(args: argparse.Namespace) -> None:
    started = time.perf_counter()
    manifest = build_dataset(
        args.data_dir,
        args.digits,
        chunk_size=args.chunk_size,
        reference_file=args.reference_file,
        reference_source=args.reference_source,
    )
    elapsed = time.perf_counter() - started
    logger.info(
        "stored %d digits in %d chunk(s), verified by %s, in %.1fs",
        manifest.total_digits,
        len(manifest.chunks),
        ", ".join(record.method for record in manifest.verifications),
        elapsed,
    )


def _verify(args: argparse.Namespace) -> None:
    store = DigitStore(args.data_dir)
    store.verify_checksums()
    logger.info("all %d chunk checksum(s) match the manifest", store.chunk_count)


def _info(args: argparse.Namespace) -> None:
    store = DigitStore(args.data_dir)
    manifest = store.manifest
    logger.info("digits available: %d (positions 1..%d)", store.total_digits, store.total_digits)
    logger.info("chunks: %d x %d digits", store.chunk_count, store.chunk_size)
    logger.info("final chunk partial: %s", manifest.has_partial_chunk)
    logger.info("generator: %s", manifest.generator)
    logger.info("first 20 decimals: %s", store.get_text(1, min(20, store.total_digits)))


def main(argv: list[str] | None = None) -> int:
    """Run the CLI and return a process exit code."""
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    args = _build_parser().parse_args(argv)
    handlers = {"generate": _generate, "verify": _verify, "info": _info}
    try:
        handlers[args.command](args)
    except (PiScopeError, ValueError) as exc:
        logger.error("error: %s", exc)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
