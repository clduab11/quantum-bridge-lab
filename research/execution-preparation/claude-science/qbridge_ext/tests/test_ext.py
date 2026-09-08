"""Offline tests: mocked HTTP only, stub objective only, fabricated numbers only.

Nothing here contacts a provider or evaluates the study objective. Regression
checks for the 2026-09-08 review findings are grounded in the protocol v0.4
text (hash-verified) rather than in implementation constants.
"""

import decimal
import hashlib
import json
from decimal import Decimal
from pathlib import Path

import httpx
import numpy as np
import pytest

from qbridge.journal import DurableJournal
from qbridge.proposals import parse_response
from qbridge.runner import ArmRunner, InlineExecutor, TransportResponse
from qbridge_ext import e9_fixtures as fx
from qbridge_ext import sol_chat_adapter as sca
from qbridge_ext.study_coordinator import (
    ARM_ORDER,
    LedgerHalted,
    ReplayRefused,
    SpendLedger,
    StudyCoordinator,
    normative_schedule_from_protocol,
    validate_money,
)

PROTOCOL = Path(__file__).resolve().parents[2] / "protocol" / "ai_quantum_control_protocol_v0.4.md"
PROTOCOL_SHA256 = "0df9242fd2d0ad5d30b75ea91f498842ac68fe0df9616afd4c9c04518233eda5"

SYSTEM = "SYSTEM PROMPT BYTES\n"
USER = "USER BYTES\n"
REQ = {"system": SYSTEM, "user": USER, "max_tokens": 8192}
RATES = dict(input_token_ceiling=1000, input_usd_per_million="5", output_usd_per_million="20")
FULL_CAP = Decimal("0.16884")  # (1000*5 + 8192*20)/1e6


def ok_payload(
    *,
    content='```json\n{"proposals": []}\n```',
    fingerprint="fp_test",
    prompt=100,
    completion=50,
    reasoning=20,
    cached=0,
    write=0,
    finish="stop",
    model=sca.MODEL,
    tier="default",
):
    return {
        "id": "chatcmpl-test",
        "object": "chat.completion",
        "created": 1_700_000_000,
        "model": model,
        "service_tier": tier,
        "system_fingerprint": fingerprint,
        "choices": [
            {
                "index": 0,
                "finish_reason": finish,
                "message": {"role": "assistant", "content": content, "refusal": None},
                "logprobs": None,
            }
        ],
        "usage": {
            "prompt_tokens": prompt,
            "completion_tokens": completion,
            "total_tokens": prompt + completion,
            "prompt_tokens_details": {"cached_tokens": cached, "cache_write_tokens": write},
            "completion_tokens_details": {"reasoning_tokens": reasoning},
        },
    }


def authority(tmp_path, *, ceiling="10.00", cap=12, scope="e9", effort="medium", **override):
    data = {
        "usd_ceiling": ceiling,
        "attempt_cap": cap,
        "authorized_by": "TEST-ONLY synthetic record; not a real authority",
        "recorded_at": "1970-01-01T00:00:00Z",
        "purpose": "unit test",
        "scope": scope,
        "profile_sha256": sca.profile_sha256(effort),
        "price_valid_through_utc": "2026-11-21T00:00:00Z",
        "rate_source": "TEST-ONLY placeholder; documented minimum promo window is a scenario input",
        "input_token_ceiling": 1000,
        "input_usd_per_million": "5",
        "output_usd_per_million": "20",
    }
    data.update(override)
    path = tmp_path / "authority.json"
    path.write_text(json.dumps(data))
    return sca.AuthorityRecord.load(path)


def store(tmp_path):
    private = tmp_path / "private"
    private.mkdir(mode=0o700, exist_ok=True)
    public = tmp_path / "public_repo"
    public.mkdir(exist_ok=True)
    return sca.ProtectedStore(private, public_repo=public)


def make_transport(
    tmp_path,
    handler,
    *,
    ceiling="10.00",
    cap=12,
    policy=sca.E9_POLICY,
    effort="medium",
    client=None,
):
    tmp_path.mkdir(parents=True, exist_ok=True)
    auth = authority(tmp_path, ceiling=ceiling, cap=cap, effort=effort, scope=policy.name)
    journal = DurableJournal(tmp_path / "journal")
    led = auth.ledger(journal)
    if client is None:
        client = httpx.Client(transport=httpx.MockTransport(handler))
    t = sca.SolChatTransport(
        reasoning_effort=effort,
        authority=auth,
        ledger=led,
        store=store(tmp_path),
        policy=policy,
        http_client=client,
        api_key="sk-test-not-a-real-key",
    )
    return t, journal, led


# ---------------- finding 1: normative schedule from protocol text ----------------


def test_protocol_copy_is_the_operative_v04():
    assert hashlib.sha256(PROTOCOL.read_bytes()).hexdigest() == PROTOCOL_SHA256


def test_schedule_equals_protocol_8_1_independently():
    expected = normative_schedule_from_protocol(PROTOCOL)
    assert len(expected) == 120
    assert expected[:3] == [(1, 0, "RS"), (1, 0, "CMA"), (1, 0, "AI")]
    assert expected[-1] == (2, 39, "AI")
    assert list(StudyCoordinator.schedule()) == expected
    assert ARM_ORDER == ("RS", "CMA", "AI")


def test_coordinator_no_replay_follows_normative_order(tmp_path):
    journal = DurableJournal(tmp_path / "study")
    coord = StudyCoordinator(journal)
    assert coord.next_unit() == (1, 0, "RS")
    with pytest.raises(ReplayRefused):
        coord.begin(0, "AI")  # LLM arm before RS is out of order
    coord.begin(0, "RS")
    with pytest.raises(ReplayRefused):
        coord.begin(0, "RS")
    coord.close(0, "RS", reason="completed")
    coord.begin(0, "CMA")
    assert coord.abandoned() == [(0, "CMA")]  # never closed -> forfeited, not resumed
    assert coord.next_unit() == (1, 0, "AI")
    assert coord.status()["scheduled_units"] == 120


# ---------------- finding 2: ledger never clips, halts on overrun, unknown stays unknown ----


def ledger(tmp_path, ceiling="10.00"):
    journal = DurableJournal(tmp_path / "ledger")
    return journal, SpendLedger(journal, ceiling_usd=ceiling, scope="e9", **RATES)


def test_known_actual_above_cap_is_recorded_unclipped_and_halts(tmp_path):
    _, led = ledger(tmp_path)
    led.reserve_attempt()
    verdict = led.record_outcome(
        status="response",
        usage={
            "prompt_tokens": 50_000,
            "completion_tokens": 9_000,
            "cached_tokens": 0,
            "cache_write_tokens": 0,
        },
    )
    actual = (Decimal(50_000) * 5 + Decimal(9_000) * 20) / 1_000_000
    assert verdict["usage_known"] is True
    assert Decimal(str(verdict["usd"])) == actual and actual > FULL_CAP  # not clipped
    assert {
        "prompt_tokens_exceed_input_ceiling",
        "completion_tokens_exceed_output_cap",
        "priced_amount_exceeds_reservation",
    } <= set(verdict["overrun"])
    assert led.totals()["halted"] is True
    with pytest.raises(LedgerHalted):
        led.reserve_attempt()


def test_unknown_cache_category_retains_full_reservation_and_is_not_known(tmp_path):
    _, led = ledger(tmp_path)
    led.reserve_attempt()
    verdict = led.record_outcome(
        status="response",
        usage={
            "prompt_tokens": 100,
            "completion_tokens": 50,
            "cached_tokens": None,
            "cache_write_tokens": None,
        },
    )
    assert verdict["usage_known"] is False
    assert Decimal(str(verdict["usd"])) == FULL_CAP  # no refund on incomplete billing
    assert verdict["overrun"] == []  # None is not relabelled zero, nor treated as nonzero
    totals = led.totals()
    assert totals["unknown_usage_attempts"] == 1 and totals["halted"] is False


def test_nonzero_cache_category_is_an_overrun(tmp_path):
    _, led = ledger(tmp_path)
    led.reserve_attempt()
    verdict = led.record_outcome(
        status="response",
        usage={
            "prompt_tokens": 100,
            "completion_tokens": 50,
            "cached_tokens": 7,
            "cache_write_tokens": 0,
        },
    )
    assert verdict["overrun"] == ["cached_tokens_nonzero"]
    assert led.totals()["halted"] is True


def test_missing_usage_keeps_full_reservation(tmp_path):
    _, led = ledger(tmp_path)
    led.reserve_attempt()
    verdict = led.record_outcome(status="timeout", usage=None)
    assert verdict["usage_known"] is False and Decimal(str(verdict["usd"])) == FULL_CAP


# ---------------- finding 3: authority binding and input validation ----------------


@pytest.mark.parametrize("bad", ["Infinity", "NaN", "-1", "1e13", " 1", "1_000", "", "1.", True, 1])
def test_money_grammar_rejects_nonfinite_negative_and_nonstring(bad):
    with pytest.raises((ValueError, TypeError)):
        validate_money(bad, "x")


@pytest.mark.parametrize("bad", [True, False, 0, -5, 10**9 + 1, 1.0, "1000"])
def test_token_ceiling_rejects_bool_float_string_and_out_of_range(tmp_path, bad):
    journal = DurableJournal(tmp_path / "j")
    with pytest.raises(ValueError):
        SpendLedger(
            journal,
            ceiling_usd="1",
            input_token_ceiling=bad,
            input_usd_per_million="5",
            output_usd_per_million="20",
            scope="t",
        )


def test_ambient_decimal_precision_does_not_alter_ledger_arithmetic(tmp_path):
    _, led = ledger(tmp_path)
    saved = decimal.getcontext().prec
    decimal.getcontext().prec = 3
    try:
        assert led.full_attempt_cap() == FULL_CAP
        led.reserve_attempt()
        v = led.record_outcome(
            status="response",
            usage={
                "prompt_tokens": 123_456,
                "completion_tokens": 7_891,
                "cached_tokens": 0,
                "cache_write_tokens": 0,
            },
        )
        assert Decimal(str(v["usd"])) == Decimal("0.7751")  # exact: (123456*5 + 7891*20)/1e6
    finally:
        decimal.getcontext().prec = saved


def test_authority_record_validation(tmp_path):
    with pytest.raises(ValueError):
        authority(tmp_path, ceiling="NaN")
    with pytest.raises(ValueError):
        authority(tmp_path, cap=0)
    with pytest.raises(ValueError):
        authority(tmp_path, cap=True)
    with pytest.raises(ValueError):
        authority(tmp_path, authorized_by="  ")
    with pytest.raises(ValueError):
        authority(tmp_path, profile_sha256="abc")
    with pytest.raises(ValueError):
        authority(tmp_path, scope="test")  # scope must name a policy
    with pytest.raises(ValueError):
        authority(tmp_path, input_usd_per_million="0")  # zero rate: fail closed
    with pytest.raises(ValueError):
        authority(tmp_path, output_usd_per_million="NaN")
    with pytest.raises(ValueError):
        authority(tmp_path, input_token_ceiling=True)
    with pytest.raises(ValueError):  # direct construction is validated too (no .load bypass)
        sca.AuthorityRecord(
            usd_ceiling="1",
            attempt_cap=1,
            authorized_by="x",
            recorded_at="x",
            purpose="x",
            scope="e9",
            profile_sha256="0" * 64,
            price_valid_through_utc="2026-11-21T00:00:00Z",
            rate_source="x",
            input_token_ceiling=1,
            input_usd_per_million="0",
            output_usd_per_million="1",
        )
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps({"usd_ceiling": "1"}))
    with pytest.raises(ValueError):
        sca.AuthorityRecord.load(bad)


def test_price_validity_checked_before_every_dispatch_including_retries(tmp_path):
    calls = {"n": 0}

    def handler(request):
        calls["n"] += 1
        return httpx.Response(200, json=ok_payload())

    now = {"t": sca._parse_utc("2026-11-20T23:59:59Z")}
    tmp_path.mkdir(parents=True, exist_ok=True)
    auth = authority(tmp_path, scope="study")
    journal = DurableJournal(tmp_path / "journal")
    led = auth.ledger(journal)
    t = sca.SolChatTransport(
        reasoning_effort="medium",
        authority=auth,
        ledger=led,
        store=store(tmp_path),
        policy=sca.STUDY_POLICY,
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
        api_key="sk-test",
        wall_clock=lambda: now["t"],
    )
    t(REQ, 30.0)
    now["t"] += 2  # validity instant passes between two attempts of the same block
    with pytest.raises(sca.PriceValidityExpired):
        t(REQ, 30.0)
    assert calls["n"] == 1 and led.totals()["attempts"] == 1  # nothing reserved or sent
    with pytest.raises(ValueError):
        authority(tmp_path, price_valid_through_utc="2026-11-21")  # date without instant rejected


def test_transport_refuses_ledger_profile_or_policy_mismatch(tmp_path):
    def handler(request):
        raise AssertionError("no request may be sent")

    client = httpx.Client(transport=httpx.MockTransport(handler))
    journal = DurableJournal(tmp_path / "journal")
    auth = authority(tmp_path, ceiling="10.00", scope="e9")
    kw = dict(store=store(tmp_path), http_client=client, api_key="sk-test")
    bigger = SpendLedger(journal, ceiling_usd="1000.00", scope="e9", **RATES)
    with pytest.raises(ValueError, match="do not match the authority"):
        sca.SolChatTransport(
            reasoning_effort="medium", authority=auth, ledger=bigger, policy=sca.E9_POLICY, **kw
        )
    cheap = SpendLedger(
        journal,
        ceiling_usd="10.00",
        scope="e9",
        input_token_ceiling=1000,
        input_usd_per_million="0.001",
        output_usd_per_million="20",
    )
    with pytest.raises(ValueError, match="do not match the authority"):
        sca.SolChatTransport(
            reasoning_effort="medium", authority=auth, ledger=cheap, policy=sca.E9_POLICY, **kw
        )
    bound = auth.ledger(journal)
    with pytest.raises(ValueError, match="different request profile"):
        sca.SolChatTransport(
            reasoning_effort="high", authority=auth, ledger=bound, policy=sca.E9_POLICY, **kw
        )
    with pytest.raises(ValueError, match="preset named by the authority scope"):
        sca.SolChatTransport(
            reasoning_effort="medium", authority=auth, ledger=bound, policy=sca.STUDY_POLICY, **kw
        )


def test_mutated_ledger_values_are_caught_before_dispatch(tmp_path):
    def handler(request):
        raise AssertionError("no request may be sent")

    t, journal, led = make_transport(tmp_path, handler)
    led.R_in = Decimal("0.0001")  # divergence after construction
    with pytest.raises(sca.LiveHalted, match="ledger_diverged"):
        t(REQ, 30.0)
    assert any(e["kind"] == "live_halt" for e in journal.read_events())


def test_transport_refuses_without_key_store_or_policy(tmp_path, monkeypatch):
    monkeypatch.delenv("QBRIDGE_OPENAI_API_KEY", raising=False)
    journal = DurableJournal(tmp_path / "journal")
    auth = authority(tmp_path)
    led = auth.ledger(journal)
    with pytest.raises(RuntimeError, match="no API key"):
        sca.SolChatTransport(
            reasoning_effort="medium",
            authority=auth,
            ledger=led,
            store=store(tmp_path),
            policy=sca.E9_POLICY,
        )
    with pytest.raises(ValueError, match="HaltPolicy"):
        sca.SolChatTransport(
            reasoning_effort="medium",
            authority=auth,
            ledger=led,
            store=store(tmp_path),
            policy=None,
            api_key="sk-test",
        )
    with pytest.raises(ValueError):
        sca.HaltPolicy(**{k: ("x" if k == "name" else "maybe") for k in sca.E9_POLICY.__dict__})


# ---------------- finding 4: retention before parse, exact sent bytes, halt transitions ---


def test_protected_store_requires_owner_only_dir_outside_public_repo(tmp_path):
    public = tmp_path / "repo"
    public.mkdir()
    loose = tmp_path / "loose"
    loose.mkdir(mode=0o755)
    with pytest.raises(ValueError, match="owner-only"):
        sca.ProtectedStore(loose, public_repo=public)
    inside = public / "private"
    inside.mkdir(mode=0o700)
    with pytest.raises(ValueError, match="outside the public repository"):
        sca.ProtectedStore(inside, public_repo=public)
    good = tmp_path / "private"
    good.mkdir(mode=0o700)
    st = sca.ProtectedStore(good, public_repo=public)
    st.write("a.bin", b"x")
    with pytest.raises(FileExistsError):
        st.write("a.bin", b"y")  # never overwritten


def test_raw_bodies_and_exact_sent_bytes_are_retained_before_parse(tmp_path):
    seen = {}

    def handler(request: httpx.Request):
        seen["body"] = bytes(request.content)
        seen["url"] = str(request.url)
        return httpx.Response(200, json=ok_payload(), headers={"x-request-id": "req_1"})

    t, journal, led = make_transport(tmp_path, handler)
    response = t(REQ, 300.0)
    assert seen["url"] == sca.ENDPOINT
    sca.verify_serialized_body(seen["body"], sca.build_request_body(REQ, reasoning_effort="medium"))
    private = tmp_path / "private"
    req_file = private / "e9_1.request.json"
    body_file = private / "e9_1.response.body"
    assert req_file.read_bytes() == seen["body"]  # the bytes that actually left the process
    assert (
        hashlib.sha256(body_file.read_bytes()).hexdigest()
        == response.metadata["response_body_sha256"]
    )
    assert json.loads(body_file.read_bytes())["id"] == "chatcmpl-test"
    assert (private / "e9_1.response.headers.json").exists()
    assert response.metadata["retained_before_parse"] is True
    assert response.metadata["sent_request_sha256"] == hashlib.sha256(seen["body"]).hexdigest()
    for path in private.iterdir():
        assert oct(path.stat().st_mode & 0o777) == "0o600"
    assert "sk-test" not in json.dumps(response.metadata)
    assert isinstance(response, TransportResponse) and response.status == 200
    assert response.metadata["findings"] == ["effective_decoding_not_echoed:medium"]
    assert response.metadata["sent_request_verified_pre_send"] is True
    assert response.metadata["halted_after_this_attempt"] is None
    assert t.client.max_retries == 0
    assert Decimal(led.totals()["reconciled_usd"]) == Decimal("0.0015")


def test_error_bodies_are_retained_and_sdk_makes_one_attempt(tmp_path):
    calls = {"n": 0}

    def handler(request):
        calls["n"] += 1
        return httpx.Response(429, json={"error": {"message": "slow down", "type": "rate_limit"}})

    t, _, led = make_transport(tmp_path, handler)
    response = t(REQ, 300.0)
    assert calls["n"] == 1
    assert response.status == 429 and response.text == "" and response.usage is None
    assert (
        json.loads((tmp_path / "private" / "e9_1.response.body").read_bytes())["error"]["type"]
        == "rate_limit"
    )
    assert response.metadata["halted_after_this_attempt"] is None  # 429 is retryable, not a halt
    assert (
        Decimal(led.totals()["reconciled_usd"]) == FULL_CAP
    )  # unknown usage: full reservation kept


def test_other_4xx_halts_under_e9_policy_but_not_under_study_policy(tmp_path):
    def handler(request):
        return httpx.Response(
            400, json={"error": {"message": "unsupported", "type": "invalid_request_error"}}
        )

    t, _, _ = make_transport(tmp_path / "e9", handler, policy=sca.E9_POLICY)
    response = t(REQ, 30.0)
    assert response.status == 400 and response.metadata["halted_after_this_attempt"] == "http_400"
    with pytest.raises(sca.LiveHalted):
        t(REQ, 30.0)
    t2, _, _ = make_transport(tmp_path / "study", handler, policy=sca.STUDY_POLICY)
    assert t2(REQ, 30.0).metadata["halted_after_this_attempt"] is None


def test_connection_and_timeout_map_to_runner_exceptions_and_retain_request(tmp_path):
    def conn(request):
        raise httpx.ConnectError("refused", request=request)

    def slow(request):
        raise httpx.ReadTimeout("timeout", request=request)

    t, _, _ = make_transport(tmp_path / "a", conn)
    with pytest.raises(ConnectionError):
        t(REQ, 30.0)
    assert (tmp_path / "a" / "private" / "e9_1.request.json").exists()
    t, _, _ = make_transport(tmp_path / "b", slow)
    with pytest.raises(TimeoutError):
        t(REQ, 30.0)


def test_model_mismatch_halts_e9_and_only_records_for_study(tmp_path):
    def handler(request):
        return httpx.Response(200, json=ok_payload(model="gpt-5.6-terra"))

    t, _, _ = make_transport(tmp_path / "e9", handler, policy=sca.E9_POLICY)
    r = t(REQ, 30.0)
    assert "model_mismatch" in r.metadata["findings"]
    assert r.metadata["halted_after_this_attempt"] == "model_mismatch"
    with pytest.raises(sca.LiveHalted):
        t(REQ, 30.0)
    t2, _, _ = make_transport(tmp_path / "study", handler, policy=sca.STUDY_POLICY)
    r2 = t2(REQ, 30.0)
    assert r2.metadata["policy_actions"]["model_mismatch"] == "record"
    assert r2.metadata["halted_after_this_attempt"] is None


def test_fingerprint_absent_is_recorded_not_halted_and_change_halts(tmp_path):
    payloads = iter(
        [
            ok_payload(fingerprint=None),
            ok_payload(fingerprint="fp_a"),
            ok_payload(fingerprint="fp_b"),
        ]
    )

    def handler(request):
        return httpx.Response(200, json=next(payloads))

    t, _, _ = make_transport(tmp_path, handler)
    r1 = t(REQ, 30.0)
    assert "system_fingerprint_absent" in r1.metadata["findings"]
    assert r1.metadata["halted_after_this_attempt"] is None
    t(REQ, 30.0)
    r3 = t(REQ, 30.0)
    assert r3.metadata["halted_after_this_attempt"] == "system_fingerprint_changed"


def test_cache_activity_halts_and_keeps_full_reservation(tmp_path):
    def handler(request):
        return httpx.Response(200, json=ok_payload(cached=1024))

    t, _, led = make_transport(tmp_path, handler)
    r = t(REQ, 30.0)
    assert "cached_tokens_nonzero" in r.metadata["findings"]
    assert r.metadata["halted_after_this_attempt"] == "cached_tokens_nonzero"
    assert (
        Decimal(led.totals()["reconciled_usd"]) == (Decimal(100) * 5 + Decimal(50) * 20) / 1_000_000
    )
    assert led.totals()["halted"] is True
    with pytest.raises(sca.LiveHalted):
        t(REQ, 30.0)


def test_incomplete_usage_is_unknown_and_recorded_without_refund(tmp_path):
    payload = ok_payload(fingerprint=None)
    payload["usage"].pop("prompt_tokens_details")

    def handler(request):
        return httpx.Response(200, json=payload)

    t, _, led = make_transport(tmp_path, handler)
    r = t(REQ, 30.0)
    assert r.usage["cached_tokens"] is None and r.usage["cache_write_tokens"] is None
    assert "usage_incomplete" in r.metadata["findings"]
    assert Decimal(led.totals()["reconciled_usd"]) == FULL_CAP


# ---------------- R5: durable halt state across ProcessExecutor forks ----------------


def test_halt_state_survives_process_executor_forks(tmp_path):
    """Each attempt runs in a forked child (real ProcessExecutor); the halt written by
    attempt 1 must stop attempt 2 in a fresh child. Dispatches are counted via a file
    because the mock handler runs inside the child process."""
    from qbridge.runner import ProcessExecutor

    counter = tmp_path / "dispatches"
    counter.write_bytes(b"")

    def handler(request):
        with open(counter, "ab") as f:
            f.write(b"x")
        return httpx.Response(200, json=ok_payload(model="wrong-model"))

    t, journal, led = make_transport(tmp_path, handler, policy=sca.E9_POLICY)
    executor = ProcessExecutor()
    first = executor.call(lambda: t(REQ, 30.0), timeout=30.0)
    assert first.metadata["halted_after_this_attempt"] == "model_mismatch"
    assert any(e["kind"] == "live_halt" for e in journal.read_events())  # durable, parent sees it
    assert t.halted_reason() == "model_mismatch"  # re-read from journal in the parent
    with pytest.raises(Exception) as info:  # LiveHalted crosses the pipe as RemoteError
        executor.call(lambda: t(REQ, 30.0), timeout=30.0)
    assert "model_mismatch" in str(info.value)
    assert counter.read_bytes() == b"x"  # exactly one dispatch ever happened
    assert led.totals()["attempts"] == 1


def test_fingerprint_baseline_survives_process_executor_forks(tmp_path):
    from qbridge.runner import ProcessExecutor

    counter = tmp_path / "dispatches"
    counter.write_bytes(b"")
    fps = tmp_path / "fps"
    fps.write_text("fp_a\nfp_a\nfp_b\n")

    def handler(request):
        with open(counter, "ab") as f:
            f.write(b"x")
        n = len(counter.read_bytes())
        return httpx.Response(200, json=ok_payload(fingerprint=fps.read_text().split()[n - 1]))

    t, journal, _ = make_transport(tmp_path, handler, policy=sca.E9_POLICY)
    executor = ProcessExecutor()
    executor.call(lambda: t(REQ, 30.0), timeout=30.0)
    assert t.fingerprint_baseline() == "fp_a"
    second = executor.call(lambda: t(REQ, 30.0), timeout=30.0)
    assert second.metadata["halted_after_this_attempt"] is None
    third = executor.call(lambda: t(REQ, 30.0), timeout=30.0)
    assert third.metadata["halted_after_this_attempt"] == "system_fingerprint_changed"
    assert counter.read_bytes() == b"xxx"


# ---------------- R6: exact outgoing request enforced BEFORE dispatch ----------------


class _Tamper(httpx.Auth):
    """Simulates any layer that alters allowed fields between the SDK and the wire."""

    def auth_flow(self, request):
        body = json.loads(request.content)
        body["reasoning_effort"] = "low"
        body["messages"][1]["content"] = "ALTERED"
        altered = json.dumps(body).encode()
        headers = dict(request.headers)
        headers["content-length"] = str(len(altered))
        yield httpx.Request(request.method, request.url, headers=headers, content=altered)


def test_altered_allowed_fields_are_rejected_before_any_dispatch(tmp_path):
    dispatched = {"n": 0}

    def handler(request):
        dispatched["n"] += 1
        return httpx.Response(200, json=ok_payload())

    client = httpx.Client(transport=httpx.MockTransport(handler), auth=_Tamper())
    t, journal, led = make_transport(tmp_path, handler, client=client)
    with pytest.raises(sca.ContractViolation, match="serialized_request_mismatch"):
        t(REQ, 30.0)
    assert dispatched["n"] == 0  # zero network dispatches
    events = journal.read_events()
    rejected = [e for e in events if e["kind"] == "request_rejected_before_dispatch"]
    assert len(rejected) == 1
    attempted = tmp_path / "private" / "e9_1.rejected_request.json"
    assert hashlib.sha256(attempted.read_bytes()).hexdigest() == rejected[0]["attempted_sha256"]
    assert json.loads(attempted.read_bytes())["reasoning_effort"] == "low"  # bytes preserved
    assert t.halted_reason() == "sent_bytes_violate_contract"
    with pytest.raises(sca.LiveHalted):
        t(REQ, 30.0)
    assert dispatched["n"] == 0
    assert led.totals()["attempts"] == 1 and led.totals()["unknown_usage_attempts"] == 1


def test_wrong_endpoint_is_rejected_before_dispatch(tmp_path):
    class Redirect(httpx.Auth):
        def auth_flow(self, request):
            yield httpx.Request(
                request.method,
                "https://example.invalid/v1/chat/completions",
                headers=request.headers,
                content=request.content,
            )

    dispatched = {"n": 0}

    def handler(request):
        dispatched["n"] += 1
        return httpx.Response(200, json=ok_payload())

    client = httpx.Client(transport=httpx.MockTransport(handler), auth=Redirect())
    t, _, _ = make_transport(tmp_path, handler, client=client)
    with pytest.raises(sca.ContractViolation, match="endpoint_or_method_mismatch"):
        t(REQ, 30.0)
    assert dispatched["n"] == 0


# ---------------- request contract ----------------


def test_body_matches_contract_and_omits_forbidden_fields():
    body = sca.build_request_body(REQ, reasoning_effort="medium")
    assert body["model"] == "gpt-5.6-sol"
    assert body["messages"] == [
        {"role": "developer", "content": SYSTEM},
        {"role": "user", "content": USER},
    ]
    assert body["max_completion_tokens"] == 8192 and body["n"] == 1
    assert body["store"] is False and body["stream"] is False
    assert body["service_tier"] == "default"
    assert body["prompt_cache_options"] == {"mode": "explicit"}
    assert not (sca.FORBIDDEN_FIELDS & body.keys())
    assert set(body) == {
        "model",
        "messages",
        "reasoning_effort",
        "max_completion_tokens",
        "n",
        "stream",
        "store",
        "service_tier",
        "prompt_cache_options",
    }


@pytest.mark.parametrize(
    "bad",
    [
        {"system": SYSTEM, "user": USER, "max_tokens": 4096},
        {"system": SYSTEM, "user": USER},
        {"system": SYSTEM, "user": USER, "max_tokens": 8192, "seed": 1},
        {"system": "", "user": USER, "max_tokens": 8192},
        {"system": SYSTEM, "user": "caf\u00e9", "max_tokens": 8192},
    ],
)
def test_contract_violations_raise(bad):
    with pytest.raises((sca.ContractViolation, UnicodeEncodeError)):
        sca.build_request_body(bad, reasoning_effort="medium")


def test_unknown_effort_and_alias_are_refused():
    with pytest.raises(sca.ContractViolation):
        sca.build_request_body(REQ, reasoning_effort="minimal")
    assert sca.MODEL != "gpt-5.6"


def test_usage_and_identity_finding_functions():
    meta = sca.metadata_from_response(
        ok_payload(finish="length", model="gpt-5.6-terra"), {}, status=200, raw_body=b"{}"
    )
    meta["refusal"] = "no"
    assert {"model_mismatch", "truncated_at_cap", "refusal_returned"} <= set(
        sca.identity_checks(meta, expected_effort="medium")
    )
    usage = sca.usage_from_payload(ok_payload(completion=9000, reasoning=9500, cached=7))
    assert {
        "completion_tokens_exceed_cap",
        "reasoning_not_subset_of_completion",
        "cached_tokens_nonzero",
    } <= set(sca.usage_checks(usage))


# ---------------- runner integration with stub objective ----------------


class Clock:
    def __init__(self):
        self.now = 0.0

    def __call__(self):
        return self.now

    def sleep(self, s):
        self.now += s


def test_runner_uses_adapter_and_attempt_cap_forfeits_without_dispatch(tmp_path):
    """Stub objective (constant 0.5), fabricated initial vectors; NOT the study objective."""
    calls = {"n": 0}
    good = json.dumps({"proposals": [[0.0] * 20 for _ in range(10)]})

    def handler(request):
        calls["n"] += 1
        return httpx.Response(
            200, json=ok_payload(content=f"```json\n{good}\n```", prompt=500, completion=300)
        )

    t, journal, led = make_transport(
        tmp_path, handler, ceiling="10.00", cap=12, policy=sca.STUDY_POLICY
    )
    clock = Clock()
    arm = ArmRunner(
        journal,
        block=0,
        arm="AI",
        objective=lambda theta: 0.5,
        map_action=lambda raw: np.asarray(raw, dtype=float),
        clock=clock,
        sleep=clock.sleep,
        executor=InlineExecutor(),
        input_token_limit=10_000,
        count_input_tokens=lambda r: 1,
        expected_identity={"model": "gpt-5.6-sol"},
    )
    arm.initialize([[0.0] * 20 for _ in range(10)])
    summary = arm.run_llm(
        t,
        parse_response=parse_response,
        render_user=lambda h, b: "U\n",
        system_prompt=lambda: "S\n",
    )
    assert calls["n"] == 12  # attempts 13.. refused BEFORE dispatch
    client_errors = [e for e in journal.read_events() if e.get("status") == "client_error"]
    assert len(client_errors) == 7 and all(
        e["error"] == "MonetaryCeilingReached" for e in client_errors
    )
    assert summary["valid_evaluations"] == 130
    assert led.totals()["attempts"] == 12
    assert len(list((tmp_path / "private").iterdir())) == 36  # 12 x (request, body, headers)


# ---------------- E9 fixtures ----------------


def test_fixtures_are_legal_and_match_recorded_bounds():
    fixtures = fx.build_fixtures()
    d = fx.describe(fixtures)
    assert d["F2_maximal_renderer"]["combined_text_bytes"] == 103_146
    assert d["F2_maximal_renderer"]["combined_text_bytes"] <= 103_449
    assert d["F3_repeat_of_F2"]["user_sha256"] == d["F2_maximal_renderer"]["user_sha256"]
    assert d["F4_correction_no_valid_vectors"]["combined_text_bytes"] == 103_146 + 96
    assert len("no_valid_vectors") == len("invalid_envelope") == 16  # equally maximal reasons
    for req in fixtures.values():
        sca.build_request_body(req, reasoning_effort="medium")
