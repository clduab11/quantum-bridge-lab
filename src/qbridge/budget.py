"""Conditional protocol v0.4 budget scenarios; no provider or objective calls.

This tool does not verify tokenization, prices, complete billing, cap enforcement,
or spending authorization. Rates and caps require external verification. Input
rates must conservatively include all applicable additive input/cache costs.
Output rates must cover all billable output categories, and every such category
(including reasoning where applicable) must fit within the 8,192-token cap for
these ceilings to hold. E9 uses the same per-attempt assumptions as the study.

Other costs require a sufficient explicit reserve. Zero reserve does not establish
that other charges are absent. Scenario ceilings are not expected spending.
"""

import argparse
import json
import re
from decimal import ROUND_CEILING, Context, Decimal, InvalidOperation, localcontext

CONDITIONS = (
    "Conditional scenario only, not expected spending or spending authorization. "
    "The tokenizer cap, prices, billing completeness and cap enforcement are not verified.",
    "Externally verify a conservative combined input rate including every applicable "
    "additive input/cache cost.",
    "Externally verify that the output rate covers all billable output categories and "
    "that the 8192-token cap includes them all, including reasoning where applicable.",
    "E9 uses the same per-attempt input/output caps and rates as the study; its supplied "
    "count is already a transport-attempt ceiling, not a logical-call count.",
    "Unpriced costs require a sufficient explicit reserve. Zero reserve does not establish "
    "that additional costs are absent. Objective slots are counts, not priced evaluations.",
)


def _count(value, name, minimum, maximum):
    if type(value) is not int or not minimum <= value <= maximum:
        raise ValueError(f"{name} must be a native integer from {minimum} through {maximum}")
    return value


def _money(value, name):
    message = (
        f"{name} must be a nonnegative decimal string of at most 64 characters, "
        "value <= 1e12 and decimal exponent from -12 through 12"
    )
    if type(value) is not str or len(value) > 64:
        raise ValueError(message)
    if re.fullmatch(r"[0-9]+(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?", value) is None:
        raise ValueError(message)
    try:
        amount = Decimal(value)
    except InvalidOperation as exc:
        raise ValueError(message) from exc
    if not amount.is_finite() or amount > Decimal("1e12"):
        raise ValueError(message)
    if not -12 <= amount.as_tuple().exponent <= 12:
        raise ValueError(message)
    return amount


def calculate_budget(
    *,
    input_token_ceiling: int,
    input_usd_per_million: str,
    output_usd_per_million: str,
    extra_usd_reserve: str,
    max_e9_attempts: int,
) -> dict:
    """Return exact token-cost subtotals and combined ceilings rounded up to cents.

    Tool limits (not provider capabilities): 1..1e9 input tokens, 0..1e6 E9
    attempts, and nonnegative monetary strings <=1e12 with decimal exponent
    -12..12 and at most 64 characters. Money uses digits, an optional decimal
    fraction and optional scientific exponent; whitespace/sign prefixes are
    rejected. All five inputs are mandatory. Unknown keywords are errors.
    """
    _count(input_token_ceiling, "input_token_ceiling", 1, 1_000_000_000)
    _count(max_e9_attempts, "max_e9_attempts", 0, 1_000_000)
    input_rate = _money(input_usd_per_million, "input_usd_per_million")
    output_rate = _money(output_usd_per_million, "output_usd_per_million")
    reserve = _money(extra_usd_reserve, "extra_usd_reserve")

    # Bounded values fit exactly within 100 digits; caller context cannot alter them.
    with localcontext(Context(prec=100)):

        def subtotal(attempts):
            inputs = attempts * input_token_ceiling
            outputs = attempts * 8192
            input_usd = Decimal(inputs) * input_rate / 1_000_000
            output_usd = Decimal(outputs) * output_rate / 1_000_000
            return {
                "attempts": attempts,
                "input_tokens": inputs,
                "output_tokens": outputs,
                "input_usd": format(input_usd, "f"),
                "output_usd": format(output_usd, "f"),
                "token_usd": format(input_usd + output_usd, "f"),
            }

        scheduled = subtotal(40 * 19)
        maximum = subtotal(40 * 19 * 2 * 3)
        e9 = subtotal(max_e9_attempts)

        def combined(study):
            total = Decimal(study["token_usd"]) + Decimal(e9["token_usd"]) + reserve
            return format(total.quantize(Decimal("0.01"), rounding=ROUND_CEILING), "f")

        return {
            "kind": "conditional_budget_scenario",
            "currency": "USD",
            "tokenizer_cap_verified": False,
            "spending_authorized": False,
            "billing_complete": False,
            "conditions": list(CONDITIONS),
            "assumptions": {
                "input_token_ceiling": input_token_ceiling,
                "output_token_ceiling": 8192,
                "input_usd_per_million": format(input_rate, "f"),
                "output_usd_per_million": format(output_rate, "f"),
                "extra_usd_reserve": format(reserve, "f"),
                "max_e9_attempts": max_e9_attempts,
            },
            "protocol": {
                "stages": 2,
                "blocks": 40,
                "all_arms_allotted_objective_slots": 40 * 3 * 200,
                "scheduled_calls": 40 * 19,
                "logical_call_ceiling": 40 * 19 * 2,
                "transport_attempt_ceiling": 40 * 19 * 2 * 3,
            },
            "scheduled_no_retry": scheduled,
            "retry_correction_ceiling": maximum,
            "e9": e9,
            "combined_totals_usd": {
                "scheduled_plus_e9_and_reserve": combined(scheduled),
                "retry_correction_plus_e9_and_reserve": combined(maximum),
            },
        }


def main(argv=None):
    """Print one validated scenario as JSON to stdout; never write a result file."""
    parser = argparse.ArgumentParser(
        description="Conditional protocol v0.4 budget scenario; not spending authorization.",
        epilog=" ".join(CONDITIONS),
        allow_abbrev=False,
    )
    parser.add_argument("--input-token-ceiling", type=int, required=True, help="1..1e9 tokens")
    parser.add_argument("--input-usd-per-million", required=True, help="conservative combined rate")
    parser.add_argument("--output-usd-per-million", required=True, help="all billable output rate")
    parser.add_argument(
        "--extra-usd-reserve", required=True, help="explicit nonnegative USD reserve"
    )
    parser.add_argument("--max-e9-attempts", type=int, required=True, help="0..1e6 attempts")
    options = parser.parse_args(argv)
    try:
        result = calculate_budget(**vars(options))
    except ValueError as exc:
        parser.error(str(exc))
    print(json.dumps(result, sort_keys=True, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
