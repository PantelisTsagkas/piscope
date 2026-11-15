"""Computed observations shown on the overview dashboard.

Every value is calculated from the digits passed in. Nothing here is a stored fact
about pi.
"""

import numpy as np
from numpy.typing import NDArray

from piscope_api.schemas.analysis import Observation
from piscope_engine.patterns.runs import longest_runs
from piscope_engine.statistics.hypothesis_tests import (
    MAX_ENTROPY_BITS,
    autocorrelation,
    chi_square_test,
    digit_counts,
    shannon_entropy,
)
from piscope_engine.statistics.ngrams import count_ngrams

type DigitArray = NDArray[np.uint8]

_AUTOCORRELATION_LAGS = 20


def build_observations(
    digits: DigitArray, first_position: int, max_ngram: int
) -> list[Observation]:
    """Compute dashboard observations for a digit range.

    Args:
        digits: The digits to describe.
        first_position: 1-based position of ``digits[0]``.
        max_ngram: Largest n-gram length to examine for coverage.
    """
    size = int(digits.size)
    counts = digit_counts(digits)
    observations: list[Observation] = []

    chi = chi_square_test(counts)
    observations.append(
        Observation(
            key="chi_square",
            title="Digit frequency fit",
            value=f"p = {chi.p_value:.3f}",
            detail=(
                f"Chi-square {chi.statistic:.2f} on 9 degrees of freedom against a uniform "
                "model. A single test on one range; not evidence of normality."
            ),
            kind="test",
            href="/statistics",
        )
    )

    expected = size / 10
    spread = (size * 0.09) ** 0.5
    z_scores = (counts - expected) / spread
    extreme = int(np.argmax(np.abs(z_scores)))
    observations.append(
        Observation(
            key="largest_deviation",
            title="Largest digit deviation",
            value=f"digit {extreme}: {z_scores[extreme]:+.2f} sd",
            detail=(
                f"Digit {extreme} occurs {int(counts[extreme]):,} times against {expected:,.1f} "
                "expected. The largest of ten deviations is usually between 1 and 2.5 sd by "
                "chance."
            ),
            kind="descriptive",
            href="/frequency",
        )
    )

    entropy = shannon_entropy(counts)
    observations.append(
        Observation(
            key="entropy",
            title="Shannon entropy",
            value=f"{entropy.statistic:.6f} bits",
            detail=(
                f"{entropy.statistic / MAX_ENTROPY_BITS * 100:.5f}% of the maximum "
                f"{MAX_ENTROPY_BITS:.6f} bits per digit. Measures single-digit balance only."
            ),
            kind="descriptive",
            href="/statistics",
        )
    )

    run = longest_runs(digits, top=1, first_position=first_position)[0]
    observations.append(
        Observation(
            key="longest_run",
            title="Longest repeated digit",
            value=f"{str(run.digit) * run.length}",
            detail=(
                f"{run.length} consecutive {run.digit}s starting at position {run.position:,}. "
                f"A run of about {_typical_longest_run(size)} is typical for {size:,} random "
                "digits."
            ),
            kind="descriptive",
            href=f"/explorer?position={run.position}&highlight={run.length}",
        )
    )

    if size > _AUTOCORRELATION_LAGS + 1 and int(counts.max()) < size:
        correlations = autocorrelation(digits, _AUTOCORRELATION_LAGS)
        strongest = int(np.argmax(np.abs(correlations)))
        band = 1.96 / size**0.5
        observations.append(
            Observation(
                key="autocorrelation",
                title="Strongest autocorrelation",
                value=f"{correlations[strongest]:+.5f} at lag {strongest + 1}",
                detail=(
                    f"Largest of lags 1 to {_AUTOCORRELATION_LAGS}. Values within "
                    f"{band:.5f} of zero are ordinary for this sample size, and the largest "
                    "of 20 lags often falls a little outside that band."
                ),
                kind="descriptive",
                href="/statistics",
            )
        )

    coverage = _ngram_coverage(digits, max_ngram)
    if coverage is not None:
        observations.append(coverage)
    return observations


def _typical_longest_run(size: int) -> int:
    """Approximate expected longest run of one digit in ``size`` random digits."""
    return max(1, round(float(np.log10(max(size * 0.9, 1.0))) + 1))


def _ngram_coverage(digits: DigitArray, max_ngram: int) -> Observation | None:
    """Find the shortest n-gram length for which some sequence is absent."""
    complete_up_to = 0
    for length in range(1, max_ngram + 1):
        if digits.size < length:
            break
        counts = count_ngrams(digits, length)
        missing = int(np.count_nonzero(counts == 0))
        if missing == 0:
            complete_up_to = length
            continue
        return Observation(
            key="ngram_coverage",
            title="Sequence coverage",
            value=f"all {complete_up_to}-digit, {10**length - missing:,} of {10**length:,} "
            f"{length}-digit",
            detail=(
                f"Every possible sequence of length {complete_up_to} occurs in this range; "
                f"{missing:,} sequences of length {length} do not. Missing sequences are "
                "expected whenever the range is short relative to the number of possibilities."
            )
            if complete_up_to
            else f"{missing:,} single digits do not occur in this range.",
            kind="descriptive",
            href=f"/frequency?n={length}",
        )
    if complete_up_to == 0:
        return None
    return Observation(
        key="ngram_coverage",
        title="Sequence coverage",
        value=f"all sequences up to {complete_up_to} digits",
        detail=f"Every possible sequence of length 1 to {complete_up_to} occurs in this range.",
        kind="descriptive",
        href="/frequency",
    )
