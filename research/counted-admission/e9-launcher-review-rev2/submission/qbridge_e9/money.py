"""Conservative money arithmetic for the E9 allowance.

Review finding 5. ``contract.reservation_for_generation`` reserves the counted
input at the *uncached* rate plus the full output cap, which is
1.251840 USD at the admission limit. But ``contract.charge_from_usage`` bills
written tokens at the cache-write rate, so the same request can charge
1.523840 USD. Recording an overrun afterwards cannot repair an
under-reservation: the money is already committed.

Everything here is exact ``Fraction`` arithmetic over the authority's recorded
per-token rates. Cache activity still fails E9 - reserving for it is a solvency
measure, not permission for it to happen.
"""

from __future__ import annotations

from fractions import Fraction

from counted_responses_provider import contract as C

# Categories that can apply to the INPUT tokens of one generation request. The
# output cap is always billed at the output rate.
INPUT_CATEGORIES = ("input", "cached_input", "cache_write")


def worst_case_input_rate(rates) -> Fraction:
    """The highest rate any input token can be billed at."""
    validated = C.validate_rates(rates)
    return max(validated[name] for name in INPUT_CATEGORIES)


def conservative_generation_reservation(counted_input_tokens, rates) -> Fraction:
    """Input at the worst applicable category rate + the full output cap."""
    validated = C.validate_rates(rates)
    if not isinstance(counted_input_tokens, int) or isinstance(counted_input_tokens, bool):
        raise C.ContractViolation("counted input tokens must be a native int")
    if counted_input_tokens < 0:
        raise C.ContractViolation("counted input tokens must be non-negative")
    return (
        Fraction(counted_input_tokens) * worst_case_input_rate(validated)
        + Fraction(C.MAX_OUTPUT_TOKENS) * validated["output"]
    )


def conservative_e9_ceiling(authority, limits) -> Fraction:
    """The smallest ceiling that every allowed E9 attempt can be funded from.

    Generation attempts are priced at the admission limit with the worst
    applicable input category; count attempts at the authority's recorded
    per-attempt count-fee ceiling, which by construction covers failed and
    rejected attempts.
    """
    rates = authority.rates()
    per_generation = conservative_generation_reservation(limits.admission_limit, rates)
    per_count = C._to_fraction(authority.count_fee_ceiling_usd, "count_fee_ceiling_usd")
    return (
        Fraction(limits.max_generation_attempts) * per_generation
        + Fraction(limits.max_count_attempts) * per_count
    )
