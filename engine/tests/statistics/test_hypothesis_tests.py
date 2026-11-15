"""Statistical tests checked against hand-computed values and closed forms."""

import math

import numpy as np
import pytest
from numpy.typing import NDArray
from scipy import stats

from piscope_engine.statistics.hypothesis_tests import (
    MAX_ENTROPY_BITS,
    autocorrelation,
    autocorrelation_test,
    chi_square_test,
    digit_counts,
    ngram_block_test,
    runs_test,
    shannon_entropy,
)
from piscope_engine.statistics.result import TestResult
from piscope_engine.statistics.simulation import random_digit_sequences

from engine_support import text_to_digits


def counts_of(values: list[int]) -> NDArray[np.int64]:
    return np.array(values, dtype=np.int64)


def p_of(result: TestResult) -> float:
    """Return a result's p-value, failing the test if it has none."""
    assert result.p_value is not None
    return result.p_value


def normal_two_sided_p(z: float) -> float:
    """Two-sided normal tail probability from the error function (independent of SciPy)."""
    return math.erfc(abs(z) / math.sqrt(2))


# --- chi-square -------------------------------------------------------------------


def test_chi_square_hand_computed_digits() -> None:
    # E = 2 per digit: ((10-2)^2 + 5*0 + 4*(0-2)^2) / 2 = (64 + 16) / 2 = 40
    result = chi_square_test(counts_of([10, 2, 2, 2, 2, 2, 0, 0, 0, 0]))
    assert result.statistic == pytest.approx(40.0)
    assert result.degrees_of_freedom == 9
    assert result.expected_statistic == 9.0
    assert result.sample_size == 20
    assert result.details["approximation_reliable"] is False
    assert "unreliable" in result.limitations[0]


def test_chi_square_p_value_matches_closed_form_for_two_degrees_of_freedom() -> None:
    # Three cells, E = 20: (100 + 0 + 100) / 20 = 10. For 2 d.f., p = exp(-x / 2).
    result = chi_square_test(counts_of([10, 20, 30]))
    assert result.statistic == pytest.approx(10.0)
    assert result.p_value == pytest.approx(math.exp(-5.0))


def test_chi_square_perfectly_uniform() -> None:
    result = chi_square_test(counts_of([100] * 10))
    assert result.statistic == 0.0
    assert result.p_value == pytest.approx(1.0)
    assert result.details["approximation_reliable"] is True


def test_chi_square_agrees_with_scipy_chisquare(reference_10k: NDArray[np.uint8]) -> None:
    counts = digit_counts(reference_10k)
    reference = stats.chisquare(counts)
    result = chi_square_test(counts)
    assert result.statistic == pytest.approx(float(reference.statistic))
    assert result.p_value == pytest.approx(float(reference.pvalue))


def test_chi_square_rejects_empty_input() -> None:
    with pytest.raises(ValueError, match="chi-square"):
        chi_square_test(counts_of([0] * 10))


# --- entropy ----------------------------------------------------------------------


@pytest.mark.parametrize(
    ("counts", "expected_bits"),
    [
        ([5] * 10, math.log2(10)),
        ([8, 8, 0, 0, 0, 0, 0, 0, 0, 0], 1.0),
        ([4, 2, 1, 1, 0, 0, 0, 0, 0, 0], 1.75),  # 0.5*1 + 0.25*2 + 2*0.125*3
        ([7, 0, 0, 0, 0, 0, 0, 0, 0, 0], 0.0),
    ],
)
def test_entropy_hand_computed(counts: list[int], expected_bits: float) -> None:
    result = shannon_entropy(counts_of(counts))
    assert result.statistic == pytest.approx(expected_bits)
    assert result.p_value is None
    assert result.statistic <= MAX_ENTROPY_BITS + 1e-12


def test_entropy_expected_value_includes_small_sample_bias() -> None:
    result = shannon_entropy(counts_of([100] * 10))
    assert result.expected_statistic == pytest.approx(math.log2(10) - 9 / (2 * 1000 * math.log(2)))


def test_entropy_bias_estimate_matches_simulation() -> None:
    sequences = random_digit_sequences(2_000, seed=11, count=400)
    mean_entropy = np.mean([shannon_entropy(digit_counts(s)).statistic for s in sequences])
    expected = shannon_entropy(digit_counts(sequences[0])).expected_statistic
    assert expected is not None
    assert mean_entropy == pytest.approx(expected, abs=2e-4)


# --- autocorrelation --------------------------------------------------------------


def test_autocorrelation_hand_computed() -> None:
    # x = 1..5, centred = [-2,-1,0,1,2], sum of squares = 10
    # lag 1: 2 + 0 + 0 + 2 = 4 -> 0.4 ; lag 2: 0 - 1 + 0 = -1 -> -0.1
    values = autocorrelation(np.array([1, 2, 3, 4, 5], dtype=np.uint8), 2)
    assert values.tolist() == pytest.approx([0.4, -0.1])


def test_ljung_box_hand_computed() -> None:
    result = autocorrelation_test(np.array([1, 2, 3, 4, 5], dtype=np.uint8), max_lag=2)
    expected_q = 5 * 7 * (0.4**2 / 4 + 0.1**2 / 3)
    assert result.statistic == pytest.approx(expected_q)
    assert result.p_value == pytest.approx(math.exp(-expected_q / 2))  # 2 d.f. closed form
    assert result.degrees_of_freedom == 2
    lags = result.details["lags"]
    assert isinstance(lags, list)
    assert len(lags) == 2
    first = lags[0]
    assert isinstance(first, dict)
    assert first["z"] == pytest.approx(0.4 * math.sqrt(5))
    assert first["p_value"] == pytest.approx(normal_two_sided_p(0.4 * math.sqrt(5)))


def test_alternating_sequence_has_strong_negative_lag_one() -> None:
    digits = np.tile(np.array([0, 9], dtype=np.uint8), 500)
    values = autocorrelation(digits, 2)
    assert values[0] == pytest.approx(-0.999, abs=1e-3)
    assert values[1] == pytest.approx(0.998, abs=1e-3)
    assert autocorrelation_test(digits, 5).p_value == pytest.approx(0.0, abs=1e-12)


def test_autocorrelation_rejects_bad_input() -> None:
    digits = np.array([1, 2, 3, 4], dtype=np.uint8)
    with pytest.raises(ValueError, match="max_lag"):
        autocorrelation(digits, 4)
    with pytest.raises(ValueError, match="max_lag"):
        autocorrelation(digits, 0)
    with pytest.raises(ValueError, match="constant"):
        autocorrelation(np.full(10, 3, dtype=np.uint8), 2)


# --- runs test --------------------------------------------------------------------


def test_runs_hand_computed_balanced() -> None:
    # H H L L H L H H L L -> 6 runs; n1 = n2 = 5: E = 2*25/10 + 1 = 6, so z = 0.
    result = runs_test(text_to_digits("9900909900"))
    assert result.details["runs"] == 6
    assert result.details["expected_runs"] == pytest.approx(6.0)
    assert result.statistic == pytest.approx(0.0)
    assert result.p_value == pytest.approx(1.0)


def test_runs_hand_computed_clustered() -> None:
    # HHHHH LLLLL -> 2 runs; Var = 50*(50-10)/(100*9) = 20/9.
    result = runs_test(text_to_digits("9999900000"))
    expected_z = (2 - 6) / math.sqrt(20 / 9)
    assert result.statistic == pytest.approx(expected_z)
    assert result.p_value == pytest.approx(normal_two_sided_p(expected_z))


def test_runs_parity_dichotomy() -> None:
    # odd/even: 1 3 | 2 4 | 5 | 6 -> O O E E O E : 4 runs
    result = runs_test(text_to_digits("132456"), dichotomy="parity")
    assert result.details["runs"] == 4
    assert result.details["count_first_symbol"] == 3
    assert "odd digits" in result.assumptions[0]


def test_runs_rejects_single_symbol() -> None:
    with pytest.raises(ValueError, match="both kinds"):
        runs_test(text_to_digits("5678956789"))


# --- n-gram block test ------------------------------------------------------------


def test_ngram_block_test_uses_disjoint_blocks() -> None:
    digits = text_to_digits("0123456789" * 100)  # blocks: 01 23 45 67 89 repeated
    result = ngram_block_test(digits, 2)
    assert result.sample_size == 500
    assert result.degrees_of_freedom == 99
    # five block values hold 100 each, 95 hold 0; E = 5:
    assert result.statistic == pytest.approx((5 * 95**2 + 95 * 5**2) / 5)
    assert result.details["digits_used"] == 1_000


def test_ngram_block_test_rejects_short_input() -> None:
    with pytest.raises(ValueError, match="at least 3 digits"):
        ngram_block_test(text_to_digits("12"), 3)


# --- behaviour on structured and random data -----------------------------------------


def test_periodic_sequence_fools_frequency_measures_but_not_order_tests() -> None:
    digits = text_to_digits("0123456789" * 1_000)
    counts = digit_counts(digits)
    assert chi_square_test(counts).p_value == pytest.approx(1.0)
    assert shannon_entropy(counts).statistic == pytest.approx(MAX_ENTROPY_BITS)
    assert p_of(autocorrelation_test(digits, 10)) < 1e-12
    assert p_of(runs_test(digits)) < 1e-12
    assert p_of(ngram_block_test(digits, 2)) < 1e-12


def test_biased_digits_are_detected() -> None:
    rng = np.random.default_rng(3)
    weights = [0.09] * 10
    weights[7] = 0.19
    digits = rng.choice(10, size=20_000, p=weights).astype(np.uint8)
    assert p_of(chi_square_test(digit_counts(digits))) < 1e-12


@pytest.mark.parametrize("test_name", ["chi_square", "autocorrelation", "runs", "ngram_blocks"])
def test_p_values_are_calibrated_on_random_digits(test_name: str) -> None:
    """Under the null model about 5% of p-values should fall below 0.05."""
    sequences = random_digit_sequences(5_000, seed=2026, count=400)
    p_values: list[float] = []
    for digits in sequences:
        if test_name == "chi_square":
            result = chi_square_test(digit_counts(digits))
        elif test_name == "autocorrelation":
            result = autocorrelation_test(digits, 10)
        elif test_name == "runs":
            result = runs_test(digits)
        else:
            result = ngram_block_test(digits, 2)
        assert result.p_value is not None
        p_values.append(result.p_value)
    rejected = np.mean(np.array(p_values) < 0.05)
    assert 0.02 <= rejected <= 0.09, rejected
    assert 0.4 <= float(np.mean(p_values)) <= 0.6


def test_results_never_claim_proof(reference_10k: NDArray[np.uint8]) -> None:
    for result in [
        chi_square_test(digit_counts(reference_10k)),
        shannon_entropy(digit_counts(reference_10k)),
        autocorrelation_test(reference_10k, 5),
        runs_test(reference_10k),
        ngram_block_test(reference_10k, 2),
    ]:
        text = " ".join([result.interpretation, *result.assumptions, *result.limitations]).lower()
        assert "cannot prove" in text
        assert "proves" not in text
        assert "is random" not in text.replace("are random", "")
        assert result.assumptions
        assert result.sample_size > 0
