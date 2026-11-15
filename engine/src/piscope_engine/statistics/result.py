"""Common result type and wording helpers for statistical tests."""

from dataclasses import dataclass, field

type DetailValue = float | int | str | bool | list[DetailValue] | dict[str, DetailValue] | None


@dataclass(frozen=True, slots=True)
class TestResult:
    """Outcome of one statistical procedure.

    Attributes:
        key: Stable identifier, e.g. ``chi_square``.
        name: Human-readable test name.
        statistic_name: What the statistic is called (``chi-square``, ``z``...).
        statistic: Observed value.
        expected_statistic: Value expected under the null model, if meaningful.
        expected_description: What ``expected_statistic`` represents.
        p_value: Probability, *under the null model*, of a statistic at least as
            extreme as the one observed. None for purely descriptive measures.
        degrees_of_freedom: Degrees of freedom of the reference distribution, if any.
        sample_size: Number of digits (or blocks, as stated) the statistic is based on.
        null_hypothesis: The model being tested.
        interpretation: Plain-language reading of the result.
        assumptions: Conditions the p-value depends on.
        limitations: What the result cannot tell you.
        details: Test-specific numbers (per-lag values, counts and so on).
    """

    __test__ = False  # not a pytest test class

    key: str
    name: str
    statistic_name: str
    statistic: float
    expected_statistic: float | None
    expected_description: str
    p_value: float | None
    degrees_of_freedom: int | None
    sample_size: int
    null_hypothesis: str
    interpretation: str
    assumptions: list[str]
    limitations: list[str]
    details: dict[str, DetailValue] = field(default_factory=dict)


FINITE_SAMPLE_LIMITATION = (
    "Describes only the finite range analysed. It says nothing about digits outside it "
    "and cannot prove or disprove that pi is normal."
)
NOT_PROOF_LIMITATION = (
    "A large p-value is an absence of evidence against the model, not evidence that the "
    "digits are random."
)


def describe_p_value(p_value: float, model: str) -> str:
    """Explain a p-value without treating it as the probability of a hypothesis.

    Args:
        p_value: The p-value to describe.
        model: Short description of the null model, e.g. ``independent uniform digits``.
    """
    share = _format_share(p_value)
    opening = (
        f"If the digits behaved like {model}, a result at least this extreme would be "
        f"expected in about {share} of samples."
    )
    if p_value < 0.001:
        verdict = (
            "That would be rare under the model. Before reading anything into it, count how "
            "many tests, ranges and settings were tried: rare results are certain to appear "
            "somewhere in a large enough search."
        )
    elif p_value < 0.05:
        verdict = (
            "That is somewhat unusual, but results like this turn up routinely when several "
            "tests are run. Treat it as exploratory unless it survives multiple-testing "
            "correction and was predicted in advance."
        )
    else:
        verdict = "The data are compatible with the model on this measure."
    return f"{opening} {verdict}"


def _format_share(p_value: float) -> str:
    if p_value >= 0.995:
        return "more than 99%"
    if p_value >= 0.01:
        return f"{p_value * 100:.0f}%"
    if p_value >= 0.0001:
        return f"{p_value * 100:.2g}%"
    return "fewer than 1 in 10,000"
