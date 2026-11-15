"""Decimal digit generation for pi.

Two independent algorithms live here on purpose:

* :func:`chudnovsky_digits` is the production generator (Chudnovsky series evaluated
  by binary splitting, about 14.18 digits per term).
* :func:`gauss_legendre_digits` is the verifier (Gauss-Legendre / Brent-Salamin
  arithmetic-geometric mean iteration). It shares no series, constants or code path
  with Chudnovsky beyond big-integer arithmetic, so agreement between the two is
  meaningful evidence that the digits are right.

Both work in fixed-point integer arithmetic with extra guard digits and *truncate*
(never round) to the requested length.

Requires the optional ``gmpy2`` dependency (``piscope-engine[generate]``).
"""

import logging
import math
from typing import Any

import numpy as np
from numpy.typing import NDArray

from piscope_engine.errors import GenerationError

logger = logging.getLogger(__name__)

DEFAULT_GUARD_DIGITS = 64
DIGITS_PER_CHUDNOVSKY_TERM = math.log10(640320**3 / (24 * 6 * 2 * 6))

_CHUDNOVSKY_A = 13591409
_CHUDNOVSKY_B = 545140134
_CHUDNOVSKY_C = 640320
_CHUDNOVSKY_C3_OVER_24 = _CHUDNOVSKY_C**3 // 24

type DigitArray = NDArray[np.uint8]


def _gmpy2() -> Any:
    try:
        import gmpy2
    except ImportError as exc:
        raise GenerationError(
            "digit generation needs gmpy2; install with 'piscope-engine[generate]'"
        ) from exc
    return gmpy2


def _validate_request(digits: int, guard_digits: int) -> None:
    if digits < 1:
        raise ValueError(f"digits must be >= 1, got {digits}")
    if guard_digits < 16:
        raise ValueError(f"guard_digits must be >= 16, got {guard_digits}")


def _scaled_pi_to_digits(scaled_pi: Any, digits: int, guard_digits: int) -> DigitArray:
    """Turn ``floor(pi * 10**(digits + guard_digits))`` into the first ``digits`` decimals.

    The low ``guard_digits`` digits absorb accumulated truncation error. If they are all
    0 or all 9, an error of a few units in the last place could carry into the digits we
    keep, so the result is rejected rather than trusted.
    """
    text: str = scaled_pi.digits(10)
    expected_length = 1 + digits + guard_digits
    if len(text) != expected_length or text[0] != "3":
        raise GenerationError("computed value does not have the shape of pi")
    guard = text[1 + digits :]
    if guard == "0" * guard_digits or guard == "9" * guard_digits:
        raise GenerationError(
            "guard digits are all 0 or all 9, truncation is ambiguous; "
            "retry with a different guard_digits value"
        )
    decimals = text[1 : 1 + digits].encode("ascii")
    return (np.frombuffer(decimals, dtype=np.uint8) - ord("0")).astype(np.uint8)


def chudnovsky_term_count(digits: int, guard_digits: int = DEFAULT_GUARD_DIGITS) -> int:
    """Return the number of Chudnovsky series terms used for a request."""
    return int((digits + guard_digits) / DIGITS_PER_CHUDNOVSKY_TERM) + 2


def chudnovsky_digits(digits: int, guard_digits: int = DEFAULT_GUARD_DIGITS) -> DigitArray:
    """Compute the first ``digits`` decimal digits of pi after the decimal point.

    Args:
        digits: How many decimals to return (position 1 up to ``digits``).
        guard_digits: Extra working digits discarded at the end.

    Returns:
        A uint8 array of length ``digits`` with values 0-9. Index 0 holds position 1.

    Raises:
        GenerationError: If gmpy2 is missing or the result fails its sanity checks.
    """
    _validate_request(digits, guard_digits)
    gmpy2 = _gmpy2()
    mpz = gmpy2.mpz
    precision = digits + guard_digits
    terms = chudnovsky_term_count(digits, guard_digits)
    logger.info("chudnovsky: %d digits, %d guard, %d terms", digits, guard_digits, terms)

    def split(a: int, b: int) -> tuple[Any, Any, Any]:
        """Binary splitting over terms [a, b): returns (P, Q, T)."""
        if b - a == 1:
            if a == 0:
                p = mpz(1)
                q = mpz(1)
            else:
                p = mpz(6 * a - 5) * (2 * a - 1) * (6 * a - 1)
                q = mpz(a) ** 3 * _CHUDNOVSKY_C3_OVER_24
            t = p * (_CHUDNOVSKY_A + _CHUDNOVSKY_B * a)
            if a % 2 == 1:
                t = -t
            return p, q, t
        middle = (a + b) // 2
        p_left, q_left, t_left = split(a, middle)
        p_right, q_right, t_right = split(middle, b)
        return p_left * p_right, q_left * q_right, q_right * t_left + p_left * t_right

    _, q, t = split(0, terms)
    one = mpz(10) ** precision
    sqrt_10005 = gmpy2.isqrt(mpz(10005) * one * one)
    scaled_pi = (q * 426880 * sqrt_10005) // t
    return _scaled_pi_to_digits(scaled_pi, digits, guard_digits)


def gauss_legendre_digits(digits: int, guard_digits: int = DEFAULT_GUARD_DIGITS) -> DigitArray:
    """Compute the first ``digits`` decimals of pi with the Gauss-Legendre iteration.

    Used only to verify :func:`chudnovsky_digits`. The iteration converges
    quadratically, so about ``log2(digits)`` rounds are enough.

    Args:
        digits: How many decimals to return.
        guard_digits: Extra working digits discarded at the end.

    Returns:
        A uint8 array of length ``digits`` with values 0-9.

    Raises:
        GenerationError: If gmpy2 is missing or the result fails its sanity checks.
    """
    _validate_request(digits, guard_digits)
    gmpy2 = _gmpy2()
    mpz = gmpy2.mpz
    precision = digits + guard_digits
    scale = mpz(10) ** precision
    iterations = max(4, precision.bit_length() + 1)
    logger.info("gauss-legendre: %d digits, %d iterations", digits, iterations)

    a = scale
    b = gmpy2.isqrt(scale * scale // 2)
    t = scale // 4
    p = mpz(1)
    for _ in range(iterations):
        a_next = (a + b) // 2
        b = gmpy2.isqrt(a * b)
        difference = a - a_next
        t -= p * difference * difference // scale
        a = a_next
        p *= 2
    total = a + b
    scaled_pi = total * total // (4 * t)
    return _scaled_pi_to_digits(scaled_pi, digits, guard_digits)
