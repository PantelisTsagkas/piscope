"""Time the main analytical operations on the stored digits.

Run with:  uv run python engine/benchmarks/analysis_operations.py [--data-dir data]
"""

import argparse
import time
from collections.abc import Callable
from pathlib import Path

from piscope_engine.digits.store import DigitStore
from piscope_engine.patterns.runs import longest_runs
from piscope_engine.patterns.windows import analyze_windows
from piscope_engine.search.sequence import search_sequence
from piscope_engine.statistics.battery import compare_with_random, run_battery
from piscope_engine.statistics.frequency import analyze_frequency
from piscope_engine.statistics.ngrams import count_ngrams


def best_of(operation: Callable[[], object], repeats: int) -> float:
    """Return the fastest wall-clock time of ``repeats`` runs, in milliseconds."""
    best = float("inf")
    for _ in range(repeats):
        started = time.perf_counter()
        operation()
        best = min(best, time.perf_counter() - started)
    return best * 1000


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", type=Path, default=Path("data"))
    parser.add_argument("--repeats", type=int, default=5)
    args = parser.parse_args()
    store = DigitStore(args.data_dir)
    size = min(store.total_digits, 1_000_000)
    digits = store.get_range(1, size)
    operations: dict[str, Callable[[], object]] = {
        "open store + verify checksums": lambda: DigitStore(args.data_dir).verify_checksums(),
        "get_range (10,000 digits)": lambda: store.get_range(size // 2, 10_000),
        "search '314159'": lambda: search_sequence(store, "314159", end=size),
        "search '7' (about n/10 matches)": lambda: search_sequence(store, "7", end=size),
        "digit frequency": lambda: analyze_frequency(store, 1, size),
        "2-gram counts": lambda: count_ngrams(digits, 2),
        "5-gram counts": lambda: count_ngrams(digits, 5),
        "full test battery (20 lags)": lambda: run_battery(digits),
        "longest runs": lambda: longest_runs(digits),
        "window analysis (100 windows)": lambda: analyze_windows(digits, 100),
        "compare with 20 simulations": lambda: compare_with_random(digits, seed=1, simulations=20),
    }
    print(f"{size:,} digits; best of {args.repeats} runs\n")
    for name, operation in operations.items():
        print(f"{name:<34} {best_of(operation, args.repeats):>10.2f} ms")


if __name__ == "__main__":
    main()
