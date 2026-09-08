"""Prospective resource arithmetic; no network or experimental objective calls."""

from decimal import Decimal, Inexact, localcontext

import pytest

from qbridge.count_budget import calculate_counted_budget


def scenario(**changes):
    inputs = {
        "input_token_ceiling": 200_000,
        "input_usd_per_million": "5",
        "output_usd_per_million": "20",
        "count_attempt_fee_ceiling_usd": None,
        "extra_usd_reserve": "0",
        "max_e9_count_attempts": 12,
        "max_e9_generation_attempts": 12,
    }
    return calculate_counted_budget(**(inputs | changes))


def test_unknown_count_fee_does_not_become_zero_even_with_extra_reserve():
    result = scenario(extra_usd_reserve="500")
    assert result["combined_ceiling_usd"] is None
    assert result["count_requests"]["total_usd"] is None
    assert result["count_requests"]["study_attempts"] == 4560
    assert result["all_request_attempts"] == 9144
    assert Decimal(result["generation_requests"]["total_usd"]) == Decimal("5321.07648")
    assert result["unpriced_request_classes"] == ["count"]


def test_supplied_count_fee_is_priced_separately_and_rounded_up_once():
    result = scenario(count_attempt_fee_ceiling_usd="0.10")
    assert Decimal(result["count_requests"]["total_usd"]) == Decimal("457.2")
    assert result["combined_ceiling_usd"] == "5778.28"
    assert result["unpriced_request_classes"] == []
    assert result["billing_complete"] is False
    assert result["spending_authorized"] is False
    assert result["protocol_adopted"] is False


def test_count_only_e9_allowance_does_not_add_generation_attempts():
    result = scenario(
        count_attempt_fee_ceiling_usd="2",
        max_e9_count_attempts=5,
        max_e9_generation_attempts=0,
    )
    assert result["all_request_attempts"] == 9125
    assert result["count_requests"]["total_attempts"] == 4565
    assert result["generation_requests"]["total_attempts"] == 4560
    assert result["combined_ceiling_usd"] == "14437.12"


def test_explicit_zero_fee_is_a_conditional_assumption_not_verified_free_counting():
    result = scenario(count_attempt_fee_ceiling_usd="0")
    assert result["count_requests"]["total_usd"] == "0"
    assert result["combined_ceiling_usd"] == "5321.08"
    assert result["billing_complete"] is False


def test_ambient_decimal_precision_and_traps_cannot_change_the_ceiling():
    with localcontext() as context:
        context.prec = 2
        context.traps[Inexact] = True
        result = scenario(count_attempt_fee_ceiling_usd="0.10")
    assert result["combined_ceiling_usd"] == "5778.28"


@pytest.mark.parametrize("fee", [False, "NaN", "-1", "1e9999"])
def test_invalid_count_fee_cannot_supply_a_reservation(fee):
    with pytest.raises(ValueError):
        scenario(count_attempt_fee_ceiling_usd=fee)


@pytest.mark.parametrize("count", [True, -1, 1_000_001, 1.5])
def test_invalid_count_attempt_allowance_is_rejected(count):
    with pytest.raises(ValueError):
        scenario(max_e9_count_attempts=count)
