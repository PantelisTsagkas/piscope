"""Statistical tests on sequences of decimal digits.

Every function takes plain arrays, so the same code analyses digits of pi and simulated
random digits. The shared null model is "independent digits, each uniform on 0-9".
"""

from typing import Literal

import numpy as np
from numpy.typing import NDArray
from scipy import stats

from piscope_engine.statistics.multiple_testing import adjust_p_values
from piscope_engine.statistics.ngrams import count_ngrams
from piscope_engine.statistics.result import (
    FINITE_SAMPLE_LIMITATION,
    NOT_PROOF_LIMITATION,
    DetailValue,
    TestResult,
    describe_p_value,
)

type DigitArray = NDArray[np.uint8]
type CountArray = NDArray[np.int64]
type Dichotomy = Literal["high_low", "parity"]

NULL_MODEL = "independent digits, each equally likely to be 0-9"
MIN_EXPECTED_COUNT = 5.0
MAX_ENTROPY_BITS = float(np.log2(10))


def digit_counts(digits: DigitArray) -> CountArray:
    """Count occurrences of each digit 0-9."""
    return np.bincount(digits, minlength=10).astype(np.int64)


def _require_digits(digits: DigitArray, minimum: int) -> None:
    if digits.size < minimum:
        raise ValueError(f"need at least {minimum} digits, got {digits.size}")


def chi_square_test(counts: CountArray, cell_description: str = "digits") -> TestResult:
    """Pearson chi-square goodness-of-fit test against a uniform distribution.

    Args:
        counts: Observed count for every cell (ten digits, or 10**n n-gram blocks).
        cell_description: What was counted, for the wording of the result.

    Raises:
        ValueError: If there are fewer than two cells or no observations.
    """
    cells = int(counts.size)
    total = int(counts.sum())
    if cells < 2 or total == 0:
        raise ValueError("chi-square needs at least two cells and one observation")
    expected = total / cells
    statistic = float(((counts - expected) ** 2).sum() / expected)
    degrees = cells - 1
    p_value = float(stats.chi2.sf(statistic, degrees))
    limitations = [FINITE_SAMPLE_LIMITATION, NOT_PROOF_LIMITATION]
    if expected < MIN_EXPECTED_COUNT:
        limitations.insert(
            0,
            f"Expected count per cell is {expected:.2f}, below the usual minimum of "
            f"{MIN_EXPECTED_COUNT:.0f}; the chi-square approximation is unreliable here.",
        )
    return TestResult(
        key="chi_square",
        name="Chi-square goodness of fit",
        statistic_name="chi-square",
        statistic=statistic,
        expected_statistic=float(degrees),
        expected_description="mean of the chi-square distribution (its degrees of freedom)",
        p_value=p_value,
        degrees_of_freedom=degrees,
        sample_size=total,
        null_hypothesis=f"all {cells} {cell_description} are equally likely",
        interpretation=describe_p_value(p_value, NULL_MODEL),
        assumptions=[
            "Observations are independent.",
            f"Expected count per cell is at least {MIN_EXPECTED_COUNT:.0f}.",
        ],
        limitations=limitations,
        details={
            "cells": cells,
            "expected_count_per_cell": expected,
            "approximation_reliable": expected >= MIN_EXPECTED_COUNT,
        },
    )


def shannon_entropy(counts: CountArray) -> TestResult:
    """Shannon entropy of the observed digit distribution, in bits per digit.

    Entropy is a descriptive measure and has no p-value here. The "expected" value is
    the maximum ``log2(10)`` minus the first-order (Miller-Madow) small-sample bias
    ``(k - 1) / (2 n ln 2)`` for ``k = 10`` equally likely symbols.

    Raises:
        ValueError: If there are no observations.
    """
    total = int(counts.sum())
    if total == 0:
        raise ValueError("entropy needs at least one observation")
    probabilities = counts[counts > 0] / total
    entropy = float(-(probabilities * np.log2(probabilities)).sum())
    expected = MAX_ENTROPY_BITS - (counts.size - 1) / (2 * total * np.log(2))
    return TestResult(
        key="shannon_entropy",
        name="Shannon entropy",
        statistic_name="bits per digit",
        statistic=entropy,
        expected_statistic=float(expected),
        expected_description=(
            "log2(10) minus the small-sample bias expected for uniform digits; "
            f"the maximum possible value is {MAX_ENTROPY_BITS:.6f}"
        ),
        p_value=None,
        degrees_of_freedom=None,
        sample_size=total,
        null_hypothesis="none (descriptive measure)",
        interpretation=(
            f"The digit distribution carries {entropy:.6f} bits per digit, "
            f"{entropy / MAX_ENTROPY_BITS * 100:.4f}% of the maximum for ten symbols. Entropy "
            "close to the maximum means single digits are close to equally frequent."
        ),
        assumptions=["Entropy is computed from single-digit frequencies only."],
        limitations=[
            "First-order entropy ignores order: 0123456789 repeated forever also reaches "
            "the maximum.",
            "The plug-in estimate is biased slightly downward in finite samples.",
            FINITE_SAMPLE_LIMITATION,
        ],
        details={
            "maximum_bits": MAX_ENTROPY_BITS,
            "ratio_to_maximum": entropy / MAX_ENTROPY_BITS,
            "deficit_bits": MAX_ENTROPY_BITS - entropy,
        },
    )


def autocorrelation(digits: DigitArray, max_lag: int) -> NDArray[np.float64]:
    """Sample autocorrelation of digit values at lags ``1..max_lag``.

    ``r_k = sum((x_i - mean)(x_{i+k} - mean)) / sum((x_i - mean)^2)``.

    Raises:
        ValueError: If ``max_lag`` is not in ``1..len(digits) - 1`` or digits are constant.
    """
    if not 1 <= max_lag < digits.size:
        raise ValueError(f"max_lag must be between 1 and {digits.size - 1}")
    centred = digits.astype(np.float64) - float(digits.mean())
    variance_sum = float(np.dot(centred, centred))
    if variance_sum == 0.0:
        raise ValueError("autocorrelation is undefined for a constant sequence")
    result = np.empty(max_lag, dtype=np.float64)
    for lag in range(1, max_lag + 1):
        result[lag - 1] = float(np.dot(centred[:-lag], centred[lag:])) / variance_sum
    return result


def autocorrelation_test(digits: DigitArray, max_lag: int = 20) -> TestResult:
    """Ljung-Box test that autocorrelations at lags ``1..max_lag`` are jointly zero.

    Per-lag z-scores and p-values are reported in ``details`` together with
    Holm-adjusted p-values, because inspecting many lags is itself multiple testing.

    Raises:
        ValueError: If ``max_lag`` is invalid for the sequence length.
    """
    _require_digits(digits, 3)
    size = int(digits.size)
    correlations = autocorrelation(digits, max_lag)
    lags = np.arange(1, max_lag + 1)
    statistic = float(size * (size + 2) * (correlations**2 / (size - lags)).sum())
    p_value = float(stats.chi2.sf(statistic, max_lag))
    z_scores = correlations * np.sqrt(size)
    lag_p_values = (2 * stats.norm.sf(np.abs(z_scores))).tolist()
    adjusted = adjust_p_values(lag_p_values, "holm")
    per_lag: list[DetailValue] = [
        {
            "lag": int(lag),
            "autocorrelation": float(correlations[index]),
            "z": float(z_scores[index]),
            "p_value": float(lag_p_values[index]),
            "p_value_holm": float(adjusted[index]),
        }
        for index, lag in enumerate(lags.tolist())
    ]
    strongest = int(np.argmax(np.abs(correlations)))
    return TestResult(
        key="autocorrelation",
        name="Autocorrelation (Ljung-Box)",
        statistic_name="Ljung-Box Q",
        statistic=statistic,
        expected_statistic=float(max_lag),
        expected_description="mean of the chi-square distribution (number of lags)",
        p_value=p_value,
        degrees_of_freedom=max_lag,
        sample_size=size,
        null_hypothesis=f"digit values are uncorrelated at lags 1 to {max_lag}",
        interpretation=describe_p_value(p_value, NULL_MODEL)
        + f" The largest single autocorrelation is {correlations[strongest]:+.5f} at lag "
        f"{strongest + 1}; for this sample size values within about "
        f"{1.96 / np.sqrt(size):.5f} of zero are ordinary.",
        assumptions=[
            "Under the null model each autocorrelation is approximately normal with "
            "standard deviation 1/sqrt(n).",
            "Digits are treated as numbers 0-9, so only linear dependence is measured.",
        ],
        limitations=[
            "Only linear dependence between digit values at the tested lags is detected.",
            FINITE_SAMPLE_LIMITATION,
            NOT_PROOF_LIMITATION,
        ],
        details={
            "max_lag": max_lag,
            "confidence_band_95": float(1.96 / np.sqrt(size)),
            "lags": per_lag,
            "smallest_holm_adjusted_p_value": float(min(adjusted)),
        },
    )


def runs_test(digits: DigitArray, dichotomy: Dichotomy = "high_low") -> TestResult:
    """Wald-Wolfowitz runs test on a two-valued recoding of the digits.

    Args:
        digits: Sequence to test.
        dichotomy: ``high_low`` recodes digits 5-9 as high and 0-4 as low; ``parity``
            recodes odd and even digits. A run is a maximal block of equal symbols.

    Raises:
        ValueError: If the sequence is too short or contains only one of the two symbols.
    """
    _require_digits(digits, 2)
    if dichotomy == "high_low":
        symbols = digits >= 5
        labels = ("digits 5-9", "digits 0-4")
    elif dichotomy == "parity":
        symbols = (digits % 2) == 1
        labels = ("odd digits", "even digits")
    else:
        raise ValueError(f"unknown dichotomy: {dichotomy}")
    size = int(symbols.size)
    first_kind = int(symbols.sum())
    second_kind = size - first_kind
    if first_kind == 0 or second_kind == 0:
        raise ValueError("runs test needs both kinds of symbol to be present")
    runs = int(np.count_nonzero(symbols[1:] != symbols[:-1])) + 1
    product = 2.0 * first_kind * second_kind
    expected_runs = product / size + 1
    variance = product * (product - size) / (size**2 * (size - 1.0))
    if variance <= 0:
        raise ValueError("sequence is too short for the runs test")
    z_score = (runs - expected_runs) / float(np.sqrt(variance))
    p_value = float(2 * stats.norm.sf(abs(z_score)))
    direction = "more" if runs > expected_runs else "fewer"
    return TestResult(
        key="runs",
        name="Runs test (Wald-Wolfowitz)",
        statistic_name="z",
        statistic=float(z_score),
        expected_statistic=0.0,
        expected_description="z-score expected when the order of symbols is random",
        p_value=p_value,
        degrees_of_freedom=None,
        sample_size=size,
        null_hypothesis=f"the order of {labels[0]} and {labels[1]} is random",
        interpretation=describe_p_value(p_value, NULL_MODEL)
        + f" There are {runs:,} runs, {direction} than the {expected_runs:,.1f} expected.",
        assumptions=[
            f"Digits are recoded into two symbols: {labels[0]} versus {labels[1]}.",
            "The number of runs is approximately normal, which needs a large sample.",
        ],
        limitations=[
            "Recoding to two symbols discards most of the information in the digits.",
            FINITE_SAMPLE_LIMITATION,
            NOT_PROOF_LIMITATION,
        ],
        details={
            "dichotomy": dichotomy,
            "runs": runs,
            "expected_runs": float(expected_runs),
            "standard_deviation": float(np.sqrt(variance)),
            "count_first_symbol": first_kind,
            "count_second_symbol": second_kind,
            "first_symbol": labels[0],
            "second_symbol": labels[1],
        },
    )


def ngram_block_test(digits: DigitArray, length: int = 2) -> TestResult:
    """Chi-square test on *non-overlapping* blocks of ``length`` digits.

    Overlapping n-grams share digits and are not independent, so a Pearson chi-square
    on overlapping counts is invalid. Cutting the sequence into disjoint blocks restores
    independence under the null model at the cost of using ``1/length`` as many blocks.

    Raises:
        ValueError: If ``length`` is below 1 or the sequence is shorter than one block.
    """
    counts = count_ngrams(digits, length, overlapping=False)
    blocks = int(counts.sum())
    if blocks == 0:
        raise ValueError(f"need at least {length} digits for blocks of length {length}")
    base = chi_square_test(counts, cell_description=f"{length}-digit blocks")
    details = dict(base.details)
    details.update({"block_length": length, "blocks": blocks, "digits_used": blocks * length})
    return TestResult(
        key="ngram_blocks",
        name=f"N-gram distribution ({length}-digit blocks)",
        statistic_name=base.statistic_name,
        statistic=base.statistic,
        expected_statistic=base.expected_statistic,
        expected_description=base.expected_description,
        p_value=base.p_value,
        degrees_of_freedom=base.degrees_of_freedom,
        sample_size=blocks,
        null_hypothesis=f"all {10**length:,} possible {length}-digit blocks are equally likely",
        interpretation=base.interpretation,
        assumptions=[
            f"The sequence is cut into {blocks:,} non-overlapping blocks of {length} digits, "
            "which are independent under the null model.",
            f"Expected count per block value is at least {MIN_EXPECTED_COUNT:.0f}.",
        ],
        limitations=base.limitations,
        details=details,
    )
