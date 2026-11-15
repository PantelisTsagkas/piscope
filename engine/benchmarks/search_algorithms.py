"""Compare single-pattern search algorithms on the stored digits of pi.

Run with:  uv run python engine/benchmarks/search_algorithms.py [--data-dir data]

All candidates find every (overlapping) occurrence inside one in-memory buffer of
digit bytes. Results are checked against each other before timings are printed.
"""

import argparse
import re
import time
from collections.abc import Callable
from pathlib import Path

import numpy as np

from piscope_engine.digits.store import DigitStore
from piscope_engine.search.sequence import encode_pattern

type Finder = Callable[[bytes, bytes], list[int]]


def find_bytes(haystack: bytes, needle: bytes) -> list[int]:
    """CPython bytes.find (two-way / fastsearch in C), advancing by one for overlaps."""
    found: list[int] = []
    index = haystack.find(needle)
    while index != -1:
        found.append(index)
        index = haystack.find(needle, index + 1)
    return found


def find_regex(haystack: bytes, needle: bytes) -> list[int]:
    """Regex with a lookahead so overlapping matches are reported."""
    pattern = re.compile(b"(?=" + re.escape(needle) + b")")
    return [match.start() for match in pattern.finditer(haystack)]


def find_numpy(haystack: bytes, needle: bytes) -> list[int]:
    """Vectorised: candidates where the first digit matches, narrowed digit by digit."""
    data = np.frombuffer(haystack, dtype=np.uint8)
    limit = data.size - len(needle) + 1
    if limit <= 0:
        return []
    candidates = np.flatnonzero(data[:limit] == needle[0])
    for offset in range(1, len(needle)):
        candidates = candidates[data[candidates + offset] == needle[offset]]
    return candidates.tolist()


def find_kmp(haystack: bytes, needle: bytes) -> list[int]:
    """Knuth-Morris-Pratt in pure Python."""
    failure = [0] * len(needle)
    k = 0
    for i in range(1, len(needle)):
        while k and needle[i] != needle[k]:
            k = failure[k - 1]
        if needle[i] == needle[k]:
            k += 1
        failure[i] = k
    found: list[int] = []
    k = 0
    for i, value in enumerate(haystack):
        while k and value != needle[k]:
            k = failure[k - 1]
        if value == needle[k]:
            k += 1
        if k == len(needle):
            found.append(i - k + 1)
            k = failure[k - 1]
    return found


FINDERS: dict[str, Finder] = {
    "bytes.find": find_bytes,
    "numpy": find_numpy,
    "regex": find_regex,
    "kmp (pure python)": find_kmp,
}
PATTERNS = ["7", "14", "999", "1234", "314159", "999999", "14159265358979"]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", type=Path, default=Path("data"))
    parser.add_argument("--repeats", type=int, default=3)
    args = parser.parse_args()
    store = DigitStore(args.data_dir)
    haystack = store.get_range(1, min(store.total_digits, 1_000_000)).tobytes()
    print(f"haystack: {len(haystack):,} digits; best of {args.repeats} runs, milliseconds\n")
    header = f"{'pattern':>16} {'matches':>8} " + " ".join(f"{name:>18}" for name in FINDERS)
    print(header)
    for text in PATTERNS:
        needle = encode_pattern(text)
        timings: list[float] = []
        results: list[list[int]] = []
        for finder in FINDERS.values():
            best = float("inf")
            found: list[int] = []
            for _ in range(args.repeats):
                started = time.perf_counter()
                found = finder(haystack, needle)
                best = min(best, time.perf_counter() - started)
            timings.append(best * 1000)
            results.append(found)
        assert all(result == results[0] for result in results), f"finders disagree on {text}"
        cells = " ".join(f"{timing:>18.2f}" for timing in timings)
        print(f"{text:>16} {len(results[0]):>8} {cells}")


if __name__ == "__main__":
    main()
