"""Check exact reservation arithmetic against the staged patched dependency."""

import json
from fractions import Fraction

from counted_responses_provider import contract as C
from qbridge_e9.money import conservative_generation_reservation


def main():
    checks = 0
    scenarios = [("4", "0.4", "5", "20"), ("8", "0.8", "10", "30"), ("5", "9", "4", "20")]
    for rates_text in scenarios:
        rates = C.rates_per_million(*rates_text)
        for count in (0, 1, 17, 272000):
            reserved = conservative_generation_reservation(count, rates)
            assert reserved == C.reservation_for_generation(count, rates)
            for cached, written in ((0, 0), (count, 0), (0, count), (count // 3, count // 2)):
                actual = C.charge_from_usage(
                    {
                        "input_tokens": count,
                        "output_tokens": 8192,
                        "input_tokens_details": {
                            "cached_tokens": cached,
                            "cache_write_tokens": written,
                        },
                    },
                    rates,
                )
                assert actual <= reserved
                checks += 1
    generation = conservative_generation_reservation(
        272000, C.rates_per_million("4", "0.4", "5", "20")
    )
    print(
        json.dumps(
            {
                "arithmetic_checks": checks,
                "rates_are_arithmetic_inputs_not_billing_evidence": True,
                "short_generation_usd": C.money_str(generation),
                "generation_allowance_usd": C.money_str(12 * generation),
                "max_count_fee_if_32_has_zero_extras_and_taxes_exact": str(
                    (Fraction(32) - 12 * generation) / 12
                ),
                "all_activity_offline": True,
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
