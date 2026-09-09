"""Orchestration regressions: caps, deadlines, retries, halts, admission.

Every response is FABRICATED. Nothing here measures a price, a token count or
model behaviour; the tests assert control flow and accounting only.
"""

from __future__ import annotations

from fractions import Fraction

import httpx
import pytest

from counted_responses_provider import contract as C
from counted_responses_provider.ledger import MoneyLedger, decimal_text
from e9tests import support
from qbridge_e9 import mocks
from qbridge_e9.acceptance import evaluate_acceptance
from qbridge_e9.limits import E9_ARM, STUDY_ARM_LABELS, E9Limits


def run(tmp_path, handler, **kw):
    journal, provider, records, orch, clock, fs = support.build(tmp_path, handler, **kw)
    outcomes = orch.run()
    return journal, provider, orch, clock, fs, outcomes


def ledger_state(journal, ceiling="25"):
    return MoneyLedger(journal, scope="e9", ceiling=Fraction(ceiling)).state()


# --- nominal ---------------------------------------------------------------


def test_nominal_run_uses_one_attempt_per_class_per_fixture(tmp_path):
    journal, _p, orch, _clock, _fs, outcomes = run(tmp_path, mocks.derived_transport())
    assert [o.outcome for o in outcomes] == ["completed"] * 4
    assert orch.attempts_used("count") == 4
    assert orch.attempts_used("generation") == 4
    assert orch._stop_reason is None
    acceptance = evaluate_acceptance(journal, outcomes, reasoning_effort="medium")
    assert acceptance.passed, acceptance.as_dict()["failed_keys"]


def test_run_never_labels_records_with_a_study_arm(tmp_path):
    journal, *_ = run(tmp_path, mocks.derived_transport())
    arms = {e.get("arm") for e in journal.read_events() if "arm" in e}
    assert arms == {E9_ARM}
    assert not arms & set(STUDY_ARM_LABELS)


def test_separate_e9_records_are_written_outside_git(tmp_path):
    _j, _p, orch, *_ = run(tmp_path, mocks.derived_transport())
    files = sorted(p.name for p in orch.records_dir.iterdir())
    assert len(files) == 24  # request + response body + response meta per dispatch
    assert all(name.startswith("E9_b0_") for name in files)
    assert not (orch.records_dir / ".git").exists()


# --- count failure and admission ------------------------------------------


def test_count_failure_forfeits_only_that_fixture_and_sends_no_generation(tmp_path):
    calls = {"n": 0}

    def count(request):
        calls["n"] += 1
        if calls["n"] <= 3:
            return mocks.error_response(500, code="server_error")
        return mocks.derived_count(request)

    journal, _p, orch, _c, _fs, outcomes = run(
        tmp_path, mocks.ScriptedTransport([count], [mocks.derived_generation])
    )
    assert outcomes[0].outcome == "count_failed"
    assert [o.outcome for o in outcomes[1:]] == ["completed"] * 3
    assert orch.attempts_used("count") == 6
    assert orch.attempts_used("generation") == 3
    gen = [e for e in support.events(journal, "reserved") if e.get("request_class") == "generation"]
    assert all(e["logical"] != 1 for e in gen)


def test_admission_rejection_blocks_generation_and_is_only_a_finding(tmp_path):
    journal, _p, orch, _c, _fs, outcomes = run(
        tmp_path,
        mocks.ScriptedTransport([lambda r: mocks.count_response(272001)],
                                [mocks.derived_generation]),
    )
    assert all(o.admission == "admission_rejected" for o in outcomes)
    assert orch.attempts_used("generation") == 0
    assert {e["reason"] for e in support.events(journal, "request_not_sent")} == {
        "admission_rejected"
    }
    assert orch.limits.admission_limit == 272000


def test_count_at_exactly_the_admission_limit_is_admitted(tmp_path):
    _j, provider, _orch, _c, _fs, outcomes = run(
        tmp_path,
        mocks.ScriptedTransport(
            [lambda r: mocks.count_response(272000)],
            [lambda r: mocks.derived_generation(r, counted_tokens=272000)],
        ),
        auth=support.authority(usd_ceiling="100"),
    )
    assert outcomes[0].admission == "admitted"
    assert outcomes[0].outcome == "completed"
    reserved = C.reservation_for_generation(272000, provider.authority.rates())
    # The reserved figure depends on whether patch 0002 is applied: 1.25184
    # reserves input at the uncached rate, 1.52384 at the worst applicable
    # category. Either way it must cover at least the uncached arithmetic.
    patched = hasattr(C, "worst_case_input_rate")
    assert decimal_text(reserved) == ("1.523840000000" if patched else "1.251840000000")


# --- retry rule -------------------------------------------------------------


def test_server_minimum_wait_is_honoured_in_full_never_shortened(tmp_path):
    calls = {"n": 0}

    def count(request):
        calls["n"] += 1
        if calls["n"] == 1:
            return mocks.error_response(
                429, code="rate_limit_exceeded", headers={"retry-after": "97"}
            )
        return mocks.derived_count(request)

    _j, _p, _o, clock, _fs, outcomes = run(
        tmp_path, mocks.ScriptedTransport([count], [mocks.derived_generation])
    )
    assert clock.waits[0] == 97  # fixed backoff is 5 s; the server minimum wins
    assert outcomes[0].outcome == "completed"


def test_malformed_retry_after_stops_the_class_without_retrying(tmp_path):
    journal, _p, orch, clock, _fs, outcomes = run(
        tmp_path,
        mocks.ScriptedTransport(
            [lambda r: mocks.error_response(
                429, code="rate_limit_exceeded", headers={"retry-after": "not-a-date"})],
            [mocks.derived_generation],
        ),
    )
    assert clock.waits == []
    assert orch.attempts_used("count") == 4
    assert {d["decision_reason"] for d in support.events(journal, "e9_retry_decision")} == {
        "retry_after_malformed"
    }


def test_retry_after_above_the_attempt_cap_is_not_retried(tmp_path):
    journal, *_ = run(
        tmp_path,
        mocks.ScriptedTransport(
            [lambda r: mocks.error_response(
                429, code="rate_limit_exceeded", headers={"retry-after": "301"})],
            [mocks.derived_generation],
        ),
    )
    assert {d["decision_reason"] for d in support.events(journal, "e9_retry_decision")} == {
        "retry_after_exceeds_attempt_cap"
    }


def test_deadline_exhaustion_stops_the_run(tmp_path):
    clock = support.Clock()

    def count(request):
        clock.advance(3700)
        return mocks.error_response(500, code="server_error")

    _j, _p, orch, _c, _fs, outcomes = run(
        tmp_path, mocks.ScriptedTransport([count], [mocks.derived_generation]), clock=clock
    )
    assert orch._stop_reason == "deadline_exhausted"
    assert orch.remaining_seconds() <= 0
    assert any(o.reason == "deadline_exhausted" for o in outcomes)
    assert orch.attempts_used("count") <= orch.limits.max_count_attempts


def test_retry_is_refused_when_wait_plus_margin_exceeds_the_deadline(tmp_path):
    clock = support.Clock()

    def count(request):
        clock.advance(7396)  # 4 s left: 5 s backoff + 1 s margin cannot fit
        return mocks.error_response(500, code="server_error")

    journal, *_ = run(
        tmp_path, mocks.ScriptedTransport([count], [mocks.derived_generation]), clock=clock
    )
    decisions = support.events(journal, "e9_retry_decision")
    assert decisions and decisions[0]["decision_reason"] == "deadline_insufficient"


# --- shared caps ------------------------------------------------------------


def test_twelve_count_attempts_are_the_total_allowance(tmp_path):
    _j, _p, orch, _c, _fs, outcomes = run(
        tmp_path,
        mocks.ScriptedTransport(
            [lambda r: mocks.error_response(500, code="server_error")],
            [mocks.derived_generation],
        ),
    )
    assert orch.attempts_used("count") == 12
    assert orch.attempts_used("generation") == 0
    assert all(o.reason in ("count_exhausted", "attempts_exhausted") for o in outcomes)


def test_attempt_cap_is_enforced_at_a_shorter_authority_cap(tmp_path):
    _j, _p, orch, _c, _fs, _o = run(
        tmp_path,
        mocks.ScriptedTransport(
            [lambda r: mocks.error_response(500, code="server_error")],
            [mocks.derived_generation],
        ),
        auth=support.authority(count_attempt_cap=2, generation_attempt_cap=2),
        limits=E9Limits(max_count_attempts=2, max_generation_attempts=2),
    )
    assert orch.attempts_used("count") == 2
    assert orch._stop_reason == "count_attempt_cap_reached"


def test_monetary_ceiling_halts_before_dispatch(tmp_path):
    journal, _p, orch, _c, _fs, outcomes = run(
        tmp_path,
        mocks.derived_transport(),
        auth=support.authority(usd_ceiling="0.5", count_fee_ceiling_usd="1.088"),
    )
    assert orch.attempts_used("generation") == 0
    assert any("monetary_ceiling_reached" in (o.reason or "") for o in outcomes)
    halts = support.events(journal, "provider_halted")
    assert halts and "monetary_ceiling_reached" in halts[0]["reason"]


# --- usage, profile and identity anomalies ---------------------------------


def test_cache_activity_fails_e9_and_stops_all_further_dispatch(tmp_path):
    journal, _p, orch, _c, _fs, outcomes = run(
        tmp_path,
        mocks.ScriptedTransport(
            [mocks.derived_count], [lambda r: mocks.derived_generation(r, cached=17)]
        ),
    )
    assert orch._stop_reason.startswith("e9_fail:cache_activity")
    assert orch.attempts_used("generation") == 1
    acceptance = evaluate_acceptance(journal, outcomes, reasoning_effort="medium")
    assert not acceptance.passed
    assert "a1.4.no_cache_activity" in acceptance.as_dict()["failed_keys"]


def test_count_usage_mismatch_fails_e9(tmp_path):
    journal, _p, orch, _c, _fs, outcomes = run(
        tmp_path,
        mocks.ScriptedTransport(
            [mocks.derived_count],
            [lambda r: mocks.derived_generation(
                r, counted_tokens=mocks.count_from_request(r) + 1)],
        ),
    )
    assert orch._stop_reason.startswith("e9_fail:count_usage_mismatch")
    acceptance = evaluate_acceptance(journal, outcomes, reasoning_effort="medium")
    assert "a1.3.usage_equals_count" in acceptance.as_dict()["failed_keys"]


def test_unknown_mandatory_usage_cannot_become_zero(tmp_path):
    def generation(request):
        response = mocks.derived_generation(request)
        body = response.json()
        del body["usage"]["total_tokens"]
        return httpx.Response(200, json=body, headers=response.headers)

    journal, _p, orch, _c, _fs, outcomes = run(
        tmp_path, mocks.ScriptedTransport([mocks.derived_count], [generation])
    )
    assert orch._stop_reason.startswith("e9_fail")
    assert ledger_state(journal)["unresolved_or_retained"] >= 1
    acceptance = evaluate_acceptance(journal, outcomes, reasoning_effort="medium")
    assert "a1.3.usage_equals_count" in acceptance.as_dict()["failed_keys"]


def test_profile_mismatch_before_a_baseline_fails_e9(tmp_path):
    journal, _p, orch, _c, _fs, outcomes = run(
        tmp_path,
        mocks.ScriptedTransport(
            [mocks.derived_count],
            [lambda r: mocks.derived_generation(r, overrides={"service_tier": "fast"})],
        ),
    )
    assert orch._stop_reason.startswith("e9_fail:profile_echo_mismatch:service_tier")
    acceptance = evaluate_acceptance(journal, outcomes, reasoning_effort="medium")
    assert "a1.2.profile_echo" in acceptance.as_dict()["failed_keys"]


def test_identity_drift_between_f2_and_f3_fails_e9(tmp_path):
    calls = {"n": 0}

    def generation(request):
        calls["n"] += 1
        if calls["n"] == 3:  # F3, the byte-identical repeat of F2
            return mocks.derived_generation(request, overrides={"temperature": 0.7})
        return mocks.derived_generation(request)

    journal, _p, orch, _c, _fs, outcomes = run(
        tmp_path, mocks.ScriptedTransport([mocks.derived_count], [generation])
    )
    assert orch._stop_reason.startswith("e9_fail:identity_change:temperature")
    assert orch.attempts_used("generation") == 3
    acceptance = evaluate_acceptance(journal, outcomes, reasoning_effort="medium")
    failed = acceptance.as_dict()["failed_keys"]
    assert "a1.5b.f2_f3_identity_identical" in failed or "run.no_halt" in failed


def test_credential_status_halts_the_run(tmp_path):
    _j, _p, orch, _c, _fs, outcomes = run(
        tmp_path,
        mocks.ScriptedTransport(
            [lambda r: mocks.error_response(401, code="invalid_api_key")],
            [mocks.derived_generation],
        ),
    )
    assert orch._stop_reason == "credential_halt:http_401"
    assert orch.attempts_used("count") == 1
    assert orch.attempts_used("generation") == 0
    assert [o.outcome for o in outcomes[1:]] == ["not_started"] * 3


def test_incomplete_status_is_preserved_but_does_not_pass_e9(tmp_path):
    journal, _p, _o, _c, _fs, outcomes = run(
        tmp_path,
        mocks.ScriptedTransport(
            [mocks.derived_count],
            [lambda r: mocks.derived_generation(r, status="incomplete")],
        ),
    )
    assert [o.outcome for o in outcomes] == ["incomplete"] * 4
    acceptance = evaluate_acceptance(journal, outcomes, reasoning_effort="medium")
    assert "fixtures.all_four_completed" in acceptance.as_dict()["failed_keys"]


def test_parse_result_is_logged_for_every_received_text(tmp_path):
    journal, *_ = run(tmp_path, mocks.derived_transport())
    parses = support.events(journal, "e9_parse_result")
    assert len(parses) == 4
    by_fixture = {p["fixture"]: p for p in parses}
    assert by_fixture["F1_short"]["valid_count"] == 10
    assert by_fixture["F4_correction_no_valid_vectors"]["valid_count"] == 0
    assert by_fixture["F4_correction_no_valid_vectors"]["reason"] == "no_valid_vectors"


def test_no_study_baseline_is_ever_seeded_by_the_launcher(tmp_path):
    journal, _p, _o, _c, _fs, outcomes = run(tmp_path, mocks.derived_transport())
    assert support.events(journal, "identity_baseline") == []
    observations = support.events(journal, "identity_observation")
    assert len(observations) == 4
    assert all(o["provisional"] is True and o["accepted"] is False for o in observations)
    record = evaluate_acceptance(journal, outcomes, reasoning_effort="medium").as_dict()
    assert record["identity_baseline_candidate"] is not None
    assert record["identity_baseline_accepted"] is False


def test_f2_f3_timing_is_recorded_and_no_cache_window_is_claimed(tmp_path):
    clock = support.Clock()

    def generation(request):
        clock.advance(11.0)
        return mocks.derived_generation(request)

    journal, _p, _o, _c, _fs, outcomes = run(
        tmp_path, mocks.ScriptedTransport([mocks.derived_count], [generation]), clock=clock
    )
    record = evaluate_acceptance(journal, outcomes, reasoning_effort="medium").as_dict()
    assert record["f2_f3_gap_seconds"] == pytest.approx(11.0)
    assert record["cache_window_coverage_demonstrated"] is False
