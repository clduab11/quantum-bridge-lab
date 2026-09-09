"""Spending-limit rejections must never be treated as retryable throughput.

Documentation evidence (retrieved 2026-09-09, hashes in
billing_source_register_2026-09-09.json):

* developers.openai.com/api/docs/guides/spend-limits.md - reaching an enforced
  organization or project hard limit returns a `429` with
  `organization_spend_limit_exceeded` / `project_spend_limit_exceeded`;
  enforcement is not instantaneous.
* developers.openai.com/api/docs/guides/error-codes.md - `429` also carries
  `credit_balance_exhausted` and `organization_usage_limit_exceeded`; the
  guide states that retrying billing, spend or quota errors will not restore
  access, and that `error.type` can still be `insufficient_quota`.
* The same page documents genuine throughput `429`s (rate limit reached, and
  the `rate_limit_error` / `slow_down` pair) which SHOULD follow `Retry-After`.

The reviewed `contract._status_bucket` maps every `429` to "retryable", so the
orchestrator classifies billing rejections itself. See
patches/0001-spend-limit-not-retryable.diff for the minimal upstream fix.
"""

from __future__ import annotations

import pytest

from counted_responses_provider import contract as C
from e9tests import support
from qbridge_e9 import mocks
from qbridge_e9.orchestrator import SPEND_LIMIT_ERROR_CODES

DOCUMENTED_BILLING_CODES = (
    "organization_spend_limit_exceeded",
    "project_spend_limit_exceeded",
    "organization_usage_limit_exceeded",
    "credit_balance_exhausted",
)


def run(tmp_path, handler, **kw):
    journal, provider, records, orch, clock, fs = support.build(tmp_path, handler, **kw)
    return journal, orch, clock, orch.run()


def test_documented_codes_are_exactly_the_orchestrator_set():
    assert set(DOCUMENTED_BILLING_CODES) == SPEND_LIMIT_ERROR_CODES


@pytest.mark.parametrize("code", DOCUMENTED_BILLING_CODES)
def test_billing_429_is_not_retried_and_halts_the_run(tmp_path, code):
    journal, orch, clock, outcomes = run(
        tmp_path,
        mocks.ScriptedTransport(
            [lambda r, code=code: mocks.error_response(
                429, code=code, kind="insufficient_quota", headers={"retry-after": "5"})],
            [mocks.derived_generation],
        ),
    )
    assert orch._stop_reason == f"spend_limit_halt:{code}"
    assert orch.attempts_used("count") == 1  # one attempt, no retry
    assert orch.attempts_used("generation") == 0
    assert clock.waits == []  # the 5 s Retry-After was NOT slept on
    rejections = support.events(journal, "e9_spend_limit_rejection")
    assert len(rejections) == 1 and rejections[0]["error_code"] == code
    assert [o.outcome for o in outcomes[1:]] == ["not_started"] * 3


def test_insufficient_quota_type_without_a_known_code_still_halts(tmp_path):
    journal, orch, clock, _o = run(
        tmp_path,
        mocks.ScriptedTransport(
            [lambda r: mocks.error_response(429, kind="insufficient_quota")],
            [mocks.derived_generation],
        ),
    )
    assert orch._stop_reason == "spend_limit_halt:type:insufficient_quota"
    assert clock.waits == []


def test_a_billing_429_on_the_generation_class_also_halts(tmp_path):
    journal, orch, clock, outcomes = run(
        tmp_path,
        mocks.ScriptedTransport(
            [mocks.derived_count],
            [lambda r: mocks.error_response(429, code="project_spend_limit_exceeded")],
        ),
    )
    assert orch._stop_reason == "spend_limit_halt:project_spend_limit_exceeded"
    assert orch.attempts_used("generation") == 1
    assert clock.waits == []


def test_genuine_throughput_429_is_still_retried(tmp_path):
    calls = {"n": 0}

    def count(request):
        calls["n"] += 1
        if calls["n"] == 1:
            return mocks.error_response(
                429, code="slow_down", kind="rate_limit_error", headers={"retry-after": "12"}
            )
        return mocks.derived_count(request)

    journal, orch, clock, outcomes = run(
        tmp_path, mocks.ScriptedTransport([count], [mocks.derived_generation])
    )
    assert clock.waits[0] == 12
    assert outcomes[0].outcome == "completed"
    assert support.events(journal, "e9_spend_limit_rejection") == []
    assert orch._stop_reason is None


def test_a_429_without_a_retained_body_is_treated_as_throughput(tmp_path):
    """No evidence of a billing code is not evidence of one: it stays retryable."""
    calls = {"n": 0}

    def count(request):
        calls["n"] += 1
        if calls["n"] == 1:
            return mocks.error_response(429, headers={"retry-after": "7"})
        return mocks.derived_count(request)

    _j, orch, clock, outcomes = run(
        tmp_path, mocks.ScriptedTransport([count], [mocks.derived_generation])
    )
    assert clock.waits[0] == 7
    assert outcomes[0].outcome == "completed"


# --- the upstream defect, with reproducing evidence ------------------------

PATCH_APPLIED = hasattr(C, "SPEND_LIMIT_ERROR_CODES")


@pytest.mark.skipif(PATCH_APPLIED, reason="the minimal patch has been applied upstream")
@pytest.mark.parametrize("code", DOCUMENTED_BILLING_CODES)
def test_defect_unpatched_contract_calls_a_billing_429_retryable(code):
    """Reproducing evidence for patches/0001-spend-limit-not-retryable.diff.

    On the reviewed baseline commit a8c3e1e8, a documented billing rejection is
    classified as retryable throughput for BOTH request classes.
    """
    payload = {"error": {"code": code, "type": "insufficient_quota"}}
    assert C._status_bucket(429, None) == "retryable"
    assert C.classify_count_outcome(429, payload) == ("count_retryable", True)
    assert C.classify_generation_outcome(429, payload) == ("gen_retryable", True)
    assert C.attempt_consequence("count_retryable", None, policy="e9")["retry_allowed"] is True


@pytest.mark.skipif(not PATCH_APPLIED, reason="the minimal patch is not applied")
@pytest.mark.parametrize("code", DOCUMENTED_BILLING_CODES)
def test_patched_contract_classifies_a_billing_429_as_a_credential_halt(code):
    payload = {"error": {"code": code, "type": "insufficient_quota"}}
    assert C.classify_count_outcome(429, payload)[0] == "count_halt_credential"
    assert C.classify_generation_outcome(429, payload)[0] == "gen_halt_credential"


@pytest.mark.skipif(not PATCH_APPLIED, reason="the minimal patch is not applied")
def test_patched_contract_leaves_throughput_429s_retryable():
    assert C.classify_count_outcome(429, {"error": {"code": "slow_down"}})[0] == "count_retryable"
    assert C.classify_count_outcome(429, None)[0] == "count_retryable"
