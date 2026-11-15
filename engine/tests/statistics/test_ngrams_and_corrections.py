from collections import Counter
from typing import Any

import numpy as np
import pytest
from numpy.typing import NDArray

from piscope_engine.digits.store import digits_to_text
from piscope_engine.statistics.multiple_testing import adjust_p_values
from piscope_engine.statistics.ngrams import count_ngrams, ngram_label, summarize_ngrams

from engine_support import text_to_digits


def test_overlapping_and_disjoint_counts_by_hand() -> None:
    digits = text_to_digits("1212121")
    overlapping = count_ngrams(digits, 2, overlapping=True)
    assert overlapping[12] == 3
    assert overlapping[21] == 3
    assert int(overlapping.sum()) == 6
    disjoint = count_ngrams(digits, 2, overlapping=False)  # 12 12 12, trailing 1 ignored
    assert disjoint[12] == 3
    assert int(disjoint.sum()) == 3


def test_labels_keep_leading_zeros() -> None:
    assert ngram_label(7, 3) == "007"
    assert ngram_label(0, 2) == "00"
    counts = count_ngrams(text_to_digits("0070"), 3)
    assert counts[7] == 1  # "007"
    assert counts[70] == 1  # "070"


@pytest.mark.parametrize("length", [1, 2, 3, 4, 5])
def test_counts_match_python_counter_on_pi(reference_10k: NDArray[np.uint8], length: int) -> None:
    text = digits_to_text(reference_10k)
    expected = Counter(text[i : i + length] for i in range(len(text) - length + 1))
    counts = count_ngrams(reference_10k, length)
    assert int(counts.sum()) == 10_000 - length + 1
    for value in range(10**length):
        assert counts[value] == expected.get(ngram_label(value, length), 0)


def test_summary(reference_10k: NDArray[np.uint8]) -> None:
    summary = summarize_ngrams(reference_10k, 2)
    assert summary.possible == 100
    assert summary.windows == 9_999
    assert summary.expected_count == pytest.approx(99.99)
    assert summary.observed_distinct == 100
    disjoint = summarize_ngrams(reference_10k, 3, overlapping=False)
    assert disjoint.windows == 3_333


def test_invalid_lengths() -> None:
    digits = text_to_digits("123")
    with pytest.raises(ValueError, match="between 1 and 7"):
        count_ngrams(digits, 0)
    with pytest.raises(ValueError, match="between 1 and 7"):
        count_ngrams(digits, 8)
    with pytest.raises(ValueError, match="at least 4 digits"):
        summarize_ngrams(digits, 4)


def test_bonferroni_by_hand() -> None:
    assert adjust_p_values([0.01, 0.04, 0.03], "bonferroni") == pytest.approx([0.03, 0.12, 0.09])
    assert adjust_p_values([0.5, 0.9], "bonferroni") == [1.0, 1.0]


def test_holm_by_hand() -> None:
    # sorted 0.01, 0.03, 0.04 -> 0.01*3, 0.03*2, 0.04*1 -> 0.03, 0.06, max(0.06, 0.04)
    assert adjust_p_values([0.01, 0.04, 0.03], "holm") == pytest.approx([0.03, 0.06, 0.06])
    assert adjust_p_values([0.2], "holm") == [0.2]
    assert adjust_p_values([], "holm") == []


def test_holm_is_never_larger_than_bonferroni() -> None:
    raw = np.random.default_rng(5).uniform(size=25).tolist()
    holm = adjust_p_values(raw, "holm")
    bonferroni = adjust_p_values(raw, "bonferroni")
    assert all(h <= b + 1e-15 for h, b in zip(holm, bonferroni, strict=True))
    assert all(h >= r for h, r in zip(holm, raw, strict=True))


def test_invalid_p_values() -> None:
    with pytest.raises(ValueError, match="p-values"):
        adjust_p_values([0.5, 1.2])
    unsupported: Any = "fdr"
    with pytest.raises(ValueError, match="unknown"):
        adjust_p_values([0.5], unsupported)
