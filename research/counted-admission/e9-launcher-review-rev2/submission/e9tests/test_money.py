"""Review finding 5: reserve conservatively for every applicable category.

Codex's reproduction: ``contract.reservation_for_generation(272000, rates)``
returns 1.251840 USD while ``charge_from_usage`` bills the same request
1.523840 USD when the provider reports cache writes. Recording an overrun after
settlement cannot repair the under-reservation - the money is already spent.

Two independent defences are tested:

* :mod:`qbridge_e9.money` computes the conservative figure, the gate requires
  the authority ceiling to cover it, and the orchestrator requires conservative
  headroom before every generation dispatch. None of that depends on the
  provider patch.
* ``patches/0002-conservative-generation-reservation.diff`` fixes the reserving
  function itself. The test that asserts the patched behaviour skips when the
  patch is not applied, and its companion asserts the unpatched behaviour, so
  exactly one of the pair runs and neither is silently vacuous.
"""

from __future__ import annotations

from fractions import Fraction

import pytest

from counted_responses_provider import contract as C
from e9tests import support
from qbridge_e9 import mocks
from qbridge_e9.limits import E9Limits
from qbridge_e9.money import (
    conservative_e9_ceiling,
    conservative_generation_reservation,
    worst_case_input_rate,
)

LIMITS = E9Limits()
PATCH_APPLIED = hasattr(C, "worst_case_input_rate")


def rates():
    return support.authority().rates()


def worst_case_charge(counted=272000):
    usage = {
        "input_tokens": counted,
        "output_tokens": C.MAX_OUTPUT_TOKENS,
        "input_tokens_details": {"cached_tokens": 0, "cache_write_tokens": counted},
    }
    return C.charge_from_usage(usage, rates())


# --- the launcher's own arithmetic ----------------------------------------


def test_the_worst_case_input_rate_is_the_cache_write_rate():
    r = C.validate_rates(rates())
    assert worst_case_input_rate(rates()) == r["cache_write"]
    assert r["cache_write"] > r["input"] > r["cached_input"]


def test_the_conservative_reservation_covers_the_worst_case_charge():
    conservative = conservative_generation_reservation(272000, rates())
    assert conservative == worst_case_charge()
    assert C.money_str(conservative) == "1.523840"
    # and it is strictly greater than what the dependency reserves as delivered
    assert conservative > C.reservation_for_generation(272000, rates()) or PATCH_APPLIED


def test_the_conservative_e9_ceiling_is_the_full_allowance(tmp_path):
    ceiling = conservative_e9_ceiling(support.authority(), LIMITS)
    expected = (
        Fraction(LIMITS.max_generation_attempts) * worst_case_charge()
        + Fraction(LIMITS.max_count_attempts)
        * C._to_fraction(support.authority().count_fee_ceiling_usd, "fee")
    )
    assert ceiling == expected
    assert C.money_str(ceiling) == "31.342080"
    assert float(ceiling) > 25, "25 USD does not fund the allowance under this assumption"


@pytest.mark.parametrize("bad", [-1, True, 1.5, "272000"])
def test_the_conservative_reservation_rejects_non_token_counts(bad):
    with pytest.raises(C.ContractViolation):
        conservative_generation_reservation(bad, rates())


# --- the orchestrator refuses to dispatch without conservative headroom ---


def test_generation_is_blocked_when_headroom_cannot_cover_the_worst_case(tmp_path):
    """A ceiling that covers the optimistic reservation but not the
    conservative one must block the dispatch, not discover it afterwards."""
    handler = mocks.derived_transport()
    fs = support.fixture_set()
    counted = mocks.fabricated_count_tokens(fs.by_name("F1_short"))
    optimistic = C.reservation_for_generation(counted, rates())
    conservative = conservative_generation_reservation(counted, rates())
    assert conservative >= optimistic
    fee = C._to_fraction(support.authority().count_fee_ceiling_usd, "fee")
    # One micro-dollar short of the conservative requirement, so the headroom
    # is insufficient whether or not patch 0002 has been applied.
    ceiling = fee + conservative - Fraction(1, 1_000_000)
    auth = support.authority(usd_ceiling=C.money_str(ceiling))

    journal, provider, _r, orch, _c, _fs = support.build(tmp_path, handler, auth=auth)
    outcomes = orch.run()
    assert outcomes[0].outcome == "generation_blocked"
    assert outcomes[0].reason == "insufficient_conservative_headroom"
    assert handler.generation_calls == [], "no generation may be dispatched"
    assert orch._stop_reason == "insufficient_conservative_headroom"
    not_sent = support.events(journal, "request_not_sent")
    assert not_sent[0]["reason"] == "insufficient_conservative_headroom"
    assert not_sent[0]["conservative_required_usd"] == C.money_str(conservative)
    journal.close()


def test_a_sufficient_ceiling_dispatches_normally(tmp_path):
    handler = mocks.derived_transport()
    journal, _provider, _records, orch, _clock, _fs = support.build(tmp_path, handler)
    outcomes = orch.run()
    assert [o.outcome for o in outcomes] == ["completed"] * 4
    assert len(handler.generation_calls) == 4
    journal.close()


# --- the dependency patch -------------------------------------------------


@pytest.mark.skipif(PATCH_APPLIED, reason="0002 is applied; the unpatched pair member")
def test_unpatched_the_dependency_under_reserves():
    reserved = C.reservation_for_generation(272000, rates())
    assert C.money_str(reserved) == "1.251840"
    assert reserved < worst_case_charge()
    assert C.money_str(worst_case_charge() - reserved) == "0.272000"


@pytest.mark.skipif(not PATCH_APPLIED, reason="requires 0002 to be applied")
def test_patched_the_dependency_reserves_the_worst_case():
    reserved = C.reservation_for_generation(272000, rates())
    assert C.money_str(reserved) == "1.523840"
    assert reserved == worst_case_charge()
    assert reserved == conservative_generation_reservation(272000, rates())
