"""Prospective count/generation cost scenarios, without dispatch or authorization.

This is arithmetic for an unadopted counted-admission design. A count result
describes the generation input; it is not evidence of the count request's own
bill. That separate fee must be supplied explicitly or remain unknown.
"""

from decimal import ROUND_CEILING, Context, Decimal, localcontext

from qbridge.budget import _count, _money, calculate_budget


def calculate_counted_budget(
    *,
    input_token_ceiling: int,
    input_usd_per_million: str,
    output_usd_per_million: str,
    count_attempt_fee_ceiling_usd: str | None,
    extra_usd_reserve: str,
    max_e9_count_attempts: int,
    max_e9_generation_attempts: int,
) -> dict:
    """Return separate exact costs and a nullable combined ceiling.

    Each request class has up to three attempts per logical call. The E9
    inputs are already attempt ceilings, not numbers to multiply by three.
    A supplied count fee is a conditional maximum for ONE count attempt,
    including failures; this function cannot verify that billing contract.
    None means unknown, including when an additional reserve is supplied.
    An explicit zero remains an assumption, never verified free counting.

    Input validation uses the existing budget tool's finite, bounded decimal
    grammar. Monetary arithmetic is independent of the caller's Decimal
    context. Only the final combined ceiling is rounded upward to cents.
    """
    _count(max_e9_count_attempts, "max_e9_count_attempts", 0, 1_000_000)
    count_fee = (
        None
        if count_attempt_fee_ceiling_usd is None
        else _money(count_attempt_fee_ceiling_usd, "count_attempt_fee_ceiling_usd")
    )
    generation = calculate_budget(
        input_token_ceiling=input_token_ceiling,
        input_usd_per_million=input_usd_per_million,
        output_usd_per_million=output_usd_per_million,
        extra_usd_reserve=extra_usd_reserve,
        max_e9_attempts=max_e9_generation_attempts,
    )
    study_generation = generation["retry_correction_ceiling"]["attempts"]
    study_count = generation["protocol"]["logical_call_ceiling"] * 3
    total_generation = study_generation + max_e9_generation_attempts
    total_count = study_count + max_e9_count_attempts

    with localcontext(Context(prec=100)):
        generation_usd = Decimal(generation["retry_correction_ceiling"]["token_usd"]) + Decimal(
            generation["e9"]["token_usd"]
        )
        reserve = Decimal(generation["assumptions"]["extra_usd_reserve"])
        count_usd = None if count_fee is None else total_count * count_fee
        exact_total = None if count_usd is None else generation_usd + count_usd + reserve
        ceiling = (
            None
            if exact_total is None
            else format(exact_total.quantize(Decimal("0.01"), rounding=ROUND_CEILING), "f")
        )

        return {
            "kind": "conditional_counted_admission_budget",
            "currency": "USD",
            "protocol_adopted": False,
            "billing_complete": False,
            "spending_authorized": False,
            "admission_enforcement_verified": False,
            "generation_assumptions": generation["assumptions"],
            "generation_requests": {
                "study_attempts": study_generation,
                "e9_attempts": max_e9_generation_attempts,
                "total_attempts": total_generation,
                "total_usd": format(generation_usd, "f"),
            },
            "count_requests": {
                "study_attempts": study_count,
                "e9_attempts": max_e9_count_attempts,
                "total_attempts": total_count,
                "attempt_fee_ceiling_usd": None if count_fee is None else format(count_fee, "f"),
                "total_usd": None if count_usd is None else format(count_usd, "f"),
            },
            "all_request_attempts": total_generation + total_count,
            "all_arms_allotted_objective_slots": generation["protocol"][
                "all_arms_allotted_objective_slots"
            ],
            "unpriced_request_classes": ["count"] if count_fee is None else [],
            "extra_usd_reserve": format(reserve, "f"),
            "combined_exact_usd": None if exact_total is None else format(exact_total, "f"),
            "combined_ceiling_usd": ceiling,
            "conditions": [
                "Unadopted prospective design; no provider or objective request is made.",
                "Generation rates must cover all applicable input/output token categories.",
                "The input limit is an admission choice, not proof all legal histories fit.",
                "A supplied count fee must bound one count attempt including failed attempts; "
                "the returned input count does not establish that fee.",
                "Unknown count fees remain unknown regardless of another reserve. "
                "A supplied zero is not evidence counting is free.",
                "Account charges, rate validity, enforcement and financial authority "
                "require separate evidence; a conditional total does not satisfy those gates.",
                "Attempt allowances are maxima; a shared deadline may forfeit work sooner.",
            ],
        }
