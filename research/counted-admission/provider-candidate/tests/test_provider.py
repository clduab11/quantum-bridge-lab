"""Single-attempt provider under CountedArmRunner with fabricated MockTransport
responses and a constant objective. No network, no real credential, no study."""

import hashlib
import json

import httpx
import pytest
from support import (
    SYNTHETIC_KEY,
    Clock,
    Fabricated,
    count_ok,
    events,
    gen_ok,
    make_provider,
    make_runner,
    private_dir,
    response_object,
    run,
    synthetic_authority,
    usage,
)

from counted_responses_provider import contract as C
from counted_responses_provider.authority import parse_utc
from counted_responses_provider.provider import (
    ProviderRefused,
    SingleAttemptResponsesProvider,
    extract_output_text,
    seed_identity_baseline,
)
from counted_responses_provider.transport import RecordingTransport
from qbridge.counted_runner import CountReceipt, DispatchContext, RequestPair
from qbridge.journal import DurableJournal
from qbridge.request_records import RequestRecords

BASELINE = C.identity_vector(response_object())


def expiry_plus_one(authority):
    """One second after the earlier of the two validity endpoints (price, count fee)."""
    return (
        min(
            parse_utc(authority.price_valid_through_utc),
            parse_utc(authority.count_fee_valid_through_utc),
        )
        + 1.0
    )


def seeded(log):
    seed_identity_baseline(
        log,
        vector=BASELINE,
        source="FABRICATED E9 acceptance record (test only)",
        accepted_from_e9=True,
    )


def raw_names(tmp_path):
    return sorted(p.name for p in (tmp_path / "raw").iterdir())


def halts(log):
    return [(e["reason"], e["inferential_failure"]) for e in events(log, "provider_halted")]


def settlements(log):
    return [e["outcome"] for e in events(log, "money_settled")]


# ------------------------------------------------------------------ prepare


def test_prepare_is_pure_literal_and_canonical(tmp_path):
    with DurableJournal(tmp_path / "j") as log:
        provider, _, _ = make_provider(tmp_path, log, Fabricated())
        before = len(log.read_events())
        request = {"system": "S text", "user": "U text", "max_tokens": 8192}
        pair = provider.prepare(request)
        assert len(log.read_events()) == before
        count = json.loads(pair.count_body)
        gen = json.loads(pair.generation_body)
        assert set(count) == set(C.COUNT_PROJECTION_KEYS)
        assert set(gen) == set(C.COUNT_PROJECTION_KEYS | C.GENERATION_ONLY_ALLOWED)
        assert gen["input"] == [
            {"role": "developer", "content": "S text"},
            {"role": "user", "content": "U text"},
        ]
        assert gen["model"] == "gpt-5.6-sol" and gen["prompt_cache_options"] == {"mode": "explicit"}
        assert gen["store"] is False and gen["stream"] is False and gen["max_output_tokens"] == 8192
        assert pair.count_body == C.canonical_bytes(count)
        assert pair.generation_body == C.canonical_bytes(gen)
        for bad in (
            {"system": "S", "user": "U", "max_tokens": 4096},
            {"system": "S", "user": "U", "max_tokens": True},
            {"system": "S", "user": "U", "max_tokens": 8192, "tools": []},
            {"system": "", "user": "U", "max_tokens": 8192},
            {"system": "S", "user": "\u00e9", "max_tokens": 8192},
        ):
            with pytest.raises(C.ContractViolation):
                provider.prepare(bad)


# --------------------------------------------------------- happy path/study


def test_full_arm_one_http_per_attempt_and_durable_records(tmp_path):
    with DurableJournal(tmp_path / "j") as log:
        seeded(log)
        handler = Fabricated()
        provider, _, clock = make_provider(tmp_path, log, handler)
        result = run(make_runner(log, clock), provider)
        assert result["valid_evaluations"] == 200 and result["forfeits"] == 0
        assert len(handler.requests) == 38  # 19 count + 19 generation, one each
        names = raw_names(tmp_path)
        assert len(names) == 114 and len(set(names)) == 114
        assert all(
            n.endswith((".request.json", ".response.body", ".response.meta.json")) for n in names
        )
        attempts = events(log, "provider_attempt")
        assert [a["category"] for a in attempts] == ["count_ok", "received_completed"] * 19
        for attempt in attempts:
            meta = attempt["metadata"]
            assert meta["requests_seen"] == 1 and meta["dispatched"] is True
            assert meta["sent_sha256"] and meta["canonical_sha256"]
            assert "authorization" not in {h[0].lower() for h in meta["response_headers"]}
            assert meta["request_id"] and meta["received_utc"] and meta["started_utc"]
        assert set(settlements(log)) == {"retained_ceiling", "settled_actual"}
        summary = provider.ledger.summary()
        assert summary["attempts"] == {"count": 19, "generation": 19}
        assert summary["billing_reconciled"] is None
        assert not halts(log)
        # request bytes on disk are exactly what the SDK put on the wire
        for url, body in handler.requests[:2]:
            digest = hashlib.sha256(body).hexdigest()
            assert any(a["metadata"]["sent_sha256"] == digest for a in attempts), url


def test_request_is_durable_before_mocked_dispatch(tmp_path):
    seen = {}

    def count(request):
        names = raw_names(tmp_path)
        seen["count"] = [n for n in names if n.endswith(".request.json")]
        return count_ok()

    with DurableJournal(tmp_path / "j") as log:
        seeded(log)
        provider, _, clock = make_provider(tmp_path, log, Fabricated(count=count))
        runner = make_runner(log, clock)
        request = {"system": "s", "user": "u", "max_tokens": 8192}
        runner.initialize([[0.0] * 20] * 10)
        runner._logical(provider, request, 1, 1)
        assert seen["count"] == ["AI_b0_bt1_l1_count_a1.request.json"]
        intents = events(log, "provider_dispatch_intent")
        assert [i["record_prefix"] for i in intents] == [
            "AI_b0_bt1_l1_count_a1",
            "AI_b0_bt1_l1_generation_a1",
        ]
        assert [i["transport_reservation"] for i in intents] == [
            "transport:AI:0:1:1:count:1",
            "transport:AI:0:1:1:generation:1",
        ]


def test_study_scope_refuses_dispatch_without_carried_baseline(tmp_path):
    with DurableJournal(tmp_path / "j") as log:
        handler = Fabricated()
        provider, _, clock = make_provider(tmp_path, log, handler)
        result = run(make_runner(log, clock), provider)
        assert not handler.requests and result["forfeits"] == 190
        assert halts(log) == [("study_baseline_missing_or_invalid:None", False)]
        assert not events(log, "money_reserved")


def test_study_scope_rejects_unaccepted_or_malformed_baseline(tmp_path):
    with DurableJournal(tmp_path / "j") as log:
        log.append(
            "identity_baseline", scope="study", vector=BASELINE, source="x"
        )  # no acceptance flag
        handler = Fabricated()
        provider, _, clock = make_provider(tmp_path, log, handler)
        run(make_runner(log, clock), provider)
        assert not handler.requests
        assert halts(log)[0][0] == "study_baseline_missing_or_invalid:invalid:not_accepted_from_e9"
    with pytest.raises(ValueError):
        seed_identity_baseline(log, vector=BASELINE, source="x", accepted_from_e9=False)
    with pytest.raises(C.ContractViolation):
        seed_identity_baseline(
            log, vector={"model": ["present", "x"]}, source="x", accepted_from_e9=True
        )


# --------------------------------------------------------- pre-send tamper


def test_tampered_wire_body_means_zero_dispatch_and_compatibility_halt(tmp_path, monkeypatch):
    import openai._base_client as base

    original = base.SyncAPIClient._prepare_options

    def tamper(self, options):
        options = original(self, options)
        if isinstance(options.json_data, dict):
            options.json_data["tools"] = []  # a field the bound body never contains
        return options

    monkeypatch.setattr(base.SyncAPIClient, "_prepare_options", tamper)
    with DurableJournal(tmp_path / "j") as log:
        seeded(log)
        handler = Fabricated()
        provider, _, clock = make_provider(tmp_path, log, handler)
        result = run(make_runner(log, clock), provider)
        assert not handler.requests  # inner MockTransport never invoked
        assert result["forfeits"] == 190 and not result["ivf"]
        assert halts(log) == [
            ("sent_bytes_violate_contract:sent_bytes_differ_from_bound_body", False)
        ]
        assert settlements(log) == ["released_not_dispatched"]
        assert raw_names(tmp_path) == ["AI_b0_bt1_l1_count_a1.rejected_request.json"]
        rejected = (tmp_path / "raw" / raw_names(tmp_path)[0]).read_bytes()
        assert json.loads(rejected)["tools"] == []


def test_recording_transport_refuses_wrong_endpoint_and_second_request(tmp_path):
    records = RequestRecords(private_dir(tmp_path / "raw"), public_repo=tmp_path / "repo")
    inner_calls = []

    def inner(request):
        inner_calls.append(1)
        return httpx.Response(200, json={"ok": True})

    transport = RecordingTransport(httpx.MockTransport(inner), records)
    body = {"a": 1}
    transport.arm(
        method="POST",
        url=C.COUNT_ENDPOINT,
        bound_object=body,
        bound_canonical=C.canonical_bytes(body),
        name="n1",
    )
    client = httpx.Client(transport=transport, follow_redirects=False)
    with pytest.raises(C.ContractViolation):
        client.post(C.GENERATION_ENDPOINT, content=b'{"a":1}')
    assert not inner_calls and transport.refusal["reason"] == "endpoint_or_method_mismatch"
    transport.disarm()
    transport.arm(
        method="POST",
        url=C.COUNT_ENDPOINT,
        bound_object=body,
        bound_canonical=C.canonical_bytes(body),
        name="n2",
    )
    with pytest.raises(C.ContractViolation):
        client.post(C.COUNT_ENDPOINT, content=b'{"a":1,"a":1}')  # duplicate key
    assert not inner_calls
    transport.disarm()
    transport.arm(
        method="POST",
        url=C.COUNT_ENDPOINT,
        bound_object=body,
        bound_canonical=C.canonical_bytes(body),
        name="n3",
    )
    assert client.post(C.COUNT_ENDPOINT, content=b'{ "a" : 1 }').status_code == 200
    assert (
        inner_calls == [1] and transport.request_retained["bytes_identical_to_canonical"] is False
    )
    with pytest.raises(C.ContractViolation):
        client.post(C.COUNT_ENDPOINT, content=b'{"a":1}')
    assert inner_calls == [1] and transport.refusal["reason"] == "second_request_in_one_attempt"
    transport.disarm()
    with pytest.raises(C.ContractViolation):
        client.post(C.COUNT_ENDPOINT, content=b'{"a":1}')
    assert transport.refusal["reason"] == "request_while_disarmed"


# ------------------------------------------------- HTTP outcomes, one request


@pytest.mark.parametrize(
    "status,category,halt,retained",
    [
        (429, "count_retryable", None, "retained_ceiling"),
        (503, "count_retryable", None, "retained_ceiling"),
        (401, "count_halt_credential", "credential_halt:http_401", "retained_ceiling"),
        (402, "count_halt_credential", "credential_halt:http_402", "retained_ceiling"),
        (400, "count_terminal", None, "retained_ceiling"),
        (
            302,
            "count_contract_anomaly",
            "compatibility_halt:count_contract_anomaly:http_302",
            "retained_ceiling",
        ),
    ],
)
def test_count_http_statuses_never_retry_inside_provider(
    tmp_path, status, category, halt, retained
):
    def count(request):
        return httpx.Response(
            status, json={"error": {"message": "fabricated"}}, headers={"retry-after": "7"}
        )

    with DurableJournal(tmp_path / "j") as log:
        seeded(log)
        handler = Fabricated(count=count)
        provider, _, clock = make_provider(tmp_path, log, handler)
        runner = make_runner(log, clock)
        runner.initialize([[0.0] * 20] * 10)
        runner._logical(provider, {"system": "s", "user": "u", "max_tokens": 8192}, 1, 1)
        attempts = events(log, "provider_attempt")
        assert attempts[0]["category"] == category
        expected_calls = 3 if category == "count_retryable" else 1
        assert len(handler.requests) == expected_calls  # retries are the runner's, one HTTP each
        assert all(a["metadata"]["requests_seen"] == 1 for a in attempts)
        assert settlements(log)[0] == retained
        assert halts(log) == ([(halt, False)] if halt else [])
        if category == "count_retryable":
            assert attempts[0]["metadata"]["retry_after"]["retry_after_seconds"] == 7.0
            assert clock.waits == [7.0, 20.0]


@pytest.mark.parametrize(
    "header,seconds,valid",
    [
        ({"retry-after": "3"}, 3.0, True),
        (
            {
                "retry-after": "Wed, 09 Sep 2026 12:00:10 GMT",
                "date": "Wed, 09 Sep 2026 12:00:00 GMT",
            },
            10.0,
            True,
        ),
        ({"retry-after": "soon"}, None, False),
        ({"retry-after-ms": "2500"}, None, True),
    ],
)
def test_retry_after_parsed_never_slept_and_ms_retained(tmp_path, header, seconds, valid):
    def gen(request):
        return httpx.Response(429, json={"error": {"code": "rate_limit_exceeded"}}, headers=header)

    with DurableJournal(tmp_path / "j") as log:
        seeded(log)
        handler = Fabricated(generation=gen)
        provider, _, clock = make_provider(tmp_path, log, handler)
        runner = make_runner(log, clock)
        runner.initialize([[0.0] * 20] * 10)
        runner._logical(provider, {"system": "s", "user": "u", "max_tokens": 8192}, 1, 1)
        gens = [a for a in events(log, "provider_attempt") if a["request_class"] == "generation"]
        meta = gens[0]["metadata"]
        assert meta["retry_after"] == {
            "retry_after_seconds": seconds,
            "retry_after_valid": valid,
            "finding": None if valid else "retry_after_malformed",
        }
        assert meta["retry_after_ms_raw"] == header.get("retry-after-ms")
        assert len(gens) == (3 if valid else 1)
        assert all(s in ("retained_ceiling", "retained_unknown") for s in settlements(log))


def test_timeout_and_connection_failures_keep_full_reservation(tmp_path):
    def gen(request):
        raise httpx.ReadTimeout("fabricated")

    with DurableJournal(tmp_path / "j") as log:
        seeded(log)
        provider, _, clock = make_provider(tmp_path, log, Fabricated(generation=gen))
        runner = make_runner(log, clock)
        runner.initialize([[0.0] * 20] * 10)
        runner._logical(provider, {"system": "s", "user": "u", "max_tokens": 8192}, 1, 1)
        gens = [a for a in events(log, "provider_attempt") if a["request_class"] == "generation"]
        assert [g["category"] for g in gens] == ["gen_retryable"] * 3
        assert all(g["metadata"]["outcome_kind"] == "timeout" for g in gens)
        assert settlements(log).count("retained_unknown") == 3
        state = provider.ledger.state()
        assert (
            state["committed"]
            == 3 * C.reservation_for_generation(42, provider.authority.rates())
            + provider.authority.count_fee_ceiling()
        )


# ------------------------------------------------ count payload anomalies


@pytest.mark.parametrize(
    "body",
    [
        b'{"object":"response.input_tokens","input_tokens":42,"input_tokens":43}',
        b'{"object":"response","input_tokens":42}',
        b'{"object":"response.input_tokens","input_tokens":true}',
        b'{"object":"response.input_tokens","input_tokens":-1}',
        b'{"object":"response.input_tokens","input_tokens":NaN}',
        b"not json",
    ],
)
def test_malformed_count_object_is_compatibility_halt_not_ivf(tmp_path, body):
    def count(request):
        return httpx.Response(200, content=body, headers={"content-type": "application/json"})

    with DurableJournal(tmp_path / "j") as log:
        seeded(log)
        handler = Fabricated(count=count)
        provider, _, clock = make_provider(tmp_path, log, handler)
        result = run(make_runner(log, clock), provider)
        assert len(handler.requests) == 1 and result["forfeits"] == 190 and not result["ivf"]
        reason, ivf = halts(log)[0]
        assert reason.startswith("compatibility_halt:count_contract_anomaly") and not ivf
        assert settlements(log) == ["retained_ceiling"]


def test_admission_rejection_consumes_count_only_and_keeps_fee_reservation(tmp_path):
    with DurableJournal(tmp_path / "j") as log:
        seeded(log)
        handler = Fabricated(count=lambda r: count_ok(101))
        provider, _, clock = make_provider(tmp_path, log, handler)
        result = run(make_runner(log, clock, admission_limit=100), provider)
        assert len(handler.requests) == 19 and result["forfeits"] == 190
        assert provider.ledger.summary()["attempts"] == {"count": 19, "generation": 0}
        assert set(settlements(log)) == {"retained_ceiling"}


# -------------------------------------------------------- receipt binding


def logical_once(tmp_path, log, handler, **kw):
    provider, _, clock = make_provider(tmp_path, log, handler, **kw)
    runner = make_runner(log, clock)
    runner.initialize([[0.0] * 20] * 10)
    return provider, runner, clock


def test_forged_receipt_tied_to_genuine_count_attempt_means_no_dispatch(tmp_path):
    with DurableJournal(tmp_path / "j") as log:
        seeded(log)
        handler = Fabricated()
        provider, runner, _ = logical_once(tmp_path, log, handler)
        request = {"system": "s", "user": "u", "max_tokens": 8192}
        runner._logical(provider, request, 1, 1)  # genuine count + generation
        assert len(handler.requests) == 2
        pair = provider.prepare(request)
        genuine = events(log, "count_receipt")[0]
        digest = hashlib.sha256(pair.count_body).hexdigest()
        context = DispatchContext(0, "AI", 1, 1, "generation", 2, "transport:AI:0:1:1:generation:2")
        forged = {
            "receipt_count_completion_mismatch": CountReceipt(
                genuine["logical_key"], digest, 7, genuine["reservation"]
            ),
            "receipt_logical_key_mismatch": CountReceipt(
                "AI:0:1:2", digest, genuine["counted_tokens"], genuine["reservation"]
            ),
            "receipt_count_digest_mismatch": CountReceipt(
                genuine["logical_key"], "0" * 64, genuine["counted_tokens"], genuine["reservation"]
            ),
            "receipt_reservation_unknown": CountReceipt(
                genuine["logical_key"],
                digest,
                genuine["counted_tokens"],
                "transport:AI:0:1:1:count:2",
            ),
        }
        for expected, receipt in forged.items():
            assert provider._receipt_valid(pair, receipt, context) == expected
        # a count_receipt row appended without any genuine count attempt behind it
        fake_pair = provider.prepare({"system": "s", "user": "other", "max_tokens": 8192})
        fake_digest = hashlib.sha256(fake_pair.count_body).hexdigest()
        log.append(
            "count_receipt",
            logical_key="AI:0:2:1",
            count_body_sha256=fake_digest,
            counted_tokens=5,
            reservation="transport:AI:0:2:1:count:1",
            block=0,
            arm="AI",
        )
        fake = CountReceipt("AI:0:2:1", fake_digest, 5, "transport:AI:0:2:1:count:1")
        fake_context = DispatchContext(
            0, "AI", 2, 1, "generation", 1, "transport:AI:0:2:1:generation:1"
        )
        assert (
            provider._receipt_valid(fake_pair, fake, fake_context) == "receipt_reservation_unknown"
        )
        # the genuine receipt with a forged token value is refused at dispatch: nothing leaves
        log.reserve("transport", "AI:0:1:1:generation:2", block=0, arm="AI")
        result = provider.generate(pair, forged["receipt_count_completion_mismatch"], context, 30.0)
        assert result.category == "gen_terminal"
        assert result.halt_reason == "receipt_count_completion_mismatch"
        assert result.metadata["dispatched"] is False and len(handler.requests) == 2
        assert halts(log) == [("receipt_count_completion_mismatch", False)]
        assert not [
            e for e in events(log, "money_reserved") if e["transport_reservation"].endswith(":2")
        ]


def test_pair_violating_profile_is_refused_before_count(tmp_path):
    with DurableJournal(tmp_path / "j") as log:
        seeded(log)
        handler = Fabricated()
        provider, runner, _ = logical_once(tmp_path, log, handler)
        body = json.loads(
            provider.prepare({"system": "s", "user": "u", "max_tokens": 8192}).generation_body
        )
        body["tools"] = []
        bad = RequestPair(
            C.canonical_bytes({k: body[k] for k in C.COUNT_PROJECTION_KEYS}),
            C.canonical_bytes(body),
        )
        log.reserve("transport", "AI:0:1:1:count:1", block=0, arm="AI")
        result = provider.count(
            bad, DispatchContext(0, "AI", 1, 1, "count", 1, "transport:AI:0:1:1:count:1"), 30.0
        )
        assert result.category == "count_terminal" and result.halt_reason.startswith(
            "pair_violates_profile"
        )
        assert not handler.requests


# ------------------------------------------------ authority at dispatch time


def test_price_expiry_and_mutation_block_dispatch_including_retries(tmp_path):
    with DurableJournal(tmp_path / "j") as log:
        seeded(log)
        handler = Fabricated(count=lambda r: httpx.Response(500, json={"error": {}}))
        provider, runner, clock = logical_once(tmp_path, log, handler)
        clock.wall = expiry_plus_one(provider.authority)
        assert clock.wall > parse_utc(provider.authority.recorded_at_utc)
        runner._logical(provider, {"system": "s", "user": "u", "max_tokens": 8192}, 1, 1)
        assert not handler.requests
        assert halts(log) == [("price_validity_expired", False)]
    with DurableJournal(tmp_path / "j2") as log:
        seeded(log)
        handler = Fabricated()
        provider, runner, clock = (
            logical_once(tmp_path / "x", log, handler) if False else (None, None, None)
        )
        (tmp_path / "x").mkdir()
        provider, _, clock = make_provider(tmp_path / "x", log, handler)
        runner = make_runner(log, clock)
        runner.initialize([[0.0] * 20] * 10)
        object.__setattr__(provider.authority, "usd_ceiling", "5000")  # mutation after binding
        runner._logical(provider, {"system": "s", "user": "u", "max_tokens": 8192}, 1, 1)
        assert not handler.requests and halts(log) == [("authority_mismatch", False)]


def test_second_authority_for_same_scope_is_refused_and_synthetic_needs_mock(tmp_path):
    with DurableJournal(tmp_path / "j") as log:
        seeded(log)
        provider, records, clock = make_provider(tmp_path, log, Fabricated())
        with pytest.raises(ProviderRefused):
            SingleAttemptResponsesProvider(
                journal=log,
                records=records,
                authority=synthetic_authority(usd_ceiling="200"),
                transport_factory=lambda: httpx.MockTransport(Fabricated()),
                api_key_provider=lambda: SYNTHETIC_KEY,
                wall_clock=clock.time,
            )
        live_like = SingleAttemptResponsesProvider(
            journal=log,
            records=records,
            authority=synthetic_authority(),
            transport_factory=lambda: httpx.HTTPTransport(retries=0),  # never invoked
            api_key_provider=lambda: SYNTHETIC_KEY,
            wall_clock=clock.time,
        )
        runner = make_runner(log, clock)
        runner.initialize([[0.0] * 20] * 10)
        runner._logical(live_like, {"system": "s", "user": "u", "max_tokens": 8192}, 1, 1)
        assert halts(log) == [("authority_transport_class_mismatch", False)]
        assert not events(log, "provider_dispatch_intent")


def test_missing_credential_is_a_credential_halt_without_dispatch(tmp_path):
    with DurableJournal(tmp_path / "j") as log:
        seeded(log)
        handler = Fabricated()
        provider, runner, _ = logical_once(tmp_path, log, handler, api_key="")
        runner._logical(provider, {"system": "s", "user": "u", "max_tokens": 8192}, 1, 1)
        assert not handler.requests and halts(log) == [("credential_unavailable", False)]


def test_e9_class_caps_stop_the_thirteenth_attempt(tmp_path):
    with DurableJournal(tmp_path / "j") as log:
        handler = Fabricated(count=lambda r: count_ok(101))  # admission rejected: count only
        authority = synthetic_authority(scope="e9", count_attempt_cap=12, generation_attempt_cap=12)
        provider, _, clock = make_provider(tmp_path, log, handler, authority=authority)
        result = run(make_runner(log, clock, admission_limit=100), provider)
        assert len(handler.requests) == 12 and result["forfeits"] == 190
        assert halts(log) == [("count_attempt_cap_reached", False)]


def test_monetary_ceiling_refuses_reservation_before_dispatch(tmp_path):
    with DurableJournal(tmp_path / "j") as log:
        seeded(log)
        handler = Fabricated()
        authority = synthetic_authority(usd_ceiling="0.18")  # 0.01 + 0.164008 fits once
        provider, runner, _ = logical_once(tmp_path, log, handler, authority=authority)
        runner._logical(provider, {"system": "s", "user": "u", "max_tokens": 8192}, 1, 1)
        runner._logical(provider, {"system": "s", "user": "u", "max_tokens": 8192}, 2, 1)
        assert len(handler.requests) == 3  # count, generation, count; second generation refused
        assert halts(log) == [("monetary_ceiling_reached", False)]


# --------------------------------------------------- 2xx generation objects


def one_generation(tmp_path, log, gen, *, scope="study", text_out=None):
    handler = Fabricated(generation=gen)
    authority = (
        synthetic_authority(scope=scope)
        if scope == "study"
        else synthetic_authority(scope="e9", count_attempt_cap=12, generation_attempt_cap=12)
    )
    provider, _, clock = make_provider(tmp_path, log, handler, authority=authority)
    runner = make_runner(log, clock)
    runner.initialize([[0.0] * 20] * 10)
    text = runner._logical(provider, {"system": "s", "user": "u", "max_tokens": 8192}, 1, 1)
    gens = [a for a in events(log, "provider_attempt") if a["request_class"] == "generation"]
    return text, gens, handler, provider


def test_accounting_halt_on_received_text_is_evaluated_but_suppresses_new_calls(tmp_path):
    with DurableJournal(tmp_path / "j") as log:
        seeded(log)
        bad_total = usage(total=1)
        provider, _, clock = make_provider(
            tmp_path, log, Fabricated(generation=lambda r: gen_ok(usage_obj=bad_total))
        )
        result = run(make_runner(log, clock), provider)
        assert result["valid_evaluations"] == 20 and result["forfeits"] == 180 and not result["ivf"]
        assert halts(log) == [("accounting_halt", False)]
        assert settlements(log) == ["retained_ceiling", "retained_unreconciled"]
        meta = events(log, "provider_attempt")[1]["metadata"]
        assert meta["reconciled_usage"] is False and meta["computed_charge_usd"] is not None


def test_simultaneous_ivf_and_accounting_findings_rank_ivf_and_discard_text(tmp_path):
    """Integration note (Codex runner delta): validity findings outrank accounting."""
    with DurableJournal(tmp_path / "j") as log:
        seeded(log)
        both = usage(total=1, cached=5)  # inconsistent total AND cache activity
        text, gens, _, _ = one_generation(tmp_path, log, lambda r: gen_ok(usage_obj=both))
        assert text is None  # proposal forfeited, not evaluated
        assert halts(log) == [("ivf_halt:cache_activity:cached_tokens=5", True)]
        meta = gens[0]["metadata"]
        assert any(f.startswith("total_tokens_inconsistent") for f in meta["usage_findings"])


def test_count_usage_mismatch_is_ivf_with_charge_recorded_unclipped(tmp_path):
    with DurableJournal(tmp_path / "j") as log:
        seeded(log)
        text, gens, _, provider = one_generation(
            tmp_path, log, lambda r: gen_ok(usage_obj=usage(inp=43))
        )
        assert text is None and halts(log) == [
            ("ivf_halt:count_usage_mismatch:counted=42,usage=43", True)
        ]
        assert gens[0]["metadata"]["computed_charge_usd"] is not None
        assert settlements(log)[-1] == "retained_unreconciled"


def test_overrun_is_recorded_unclipped_and_halts_accounting(tmp_path):
    with DurableJournal(tmp_path / "j") as log:
        seeded(log)
        text, gens, _, provider = one_generation(
            tmp_path, log, lambda r: gen_ok(usage_obj=usage(out=20000))
        )
        assert text == "good"  # received text still evaluated under the accounting exception
        assert halts(log) == [("accounting_halt", False)]
        assert settlements(log)[-1] == "overrun_recorded"
        state = provider.ledger.state()
        assert state["overrun_recorded"] and state["halted"]
        assert state["committed"] > C.reservation_for_generation(42, provider.authority.rates())


def test_r1_contradictory_total_with_categories_above_reservation_halts_ledger(tmp_path):
    with DurableJournal(tmp_path / "j") as log:
        seeded(log)
        text, gens, handler, provider = one_generation(
            tmp_path, log, lambda r: gen_ok(usage_obj=usage(out=20000, total=1))
        )
        assert halts(log) == [("accounting_halt", False)]
        assert settlements(log)[-1] == "retained_unreconciled"
        state = provider.ledger.state()
        assert state["overrun_recorded"] and state["halted"]
        assert (
            state["committed"]
            == C.charge_from_usage(usage(out=20000, total=1), provider.authority.rates())
            + provider.authority.count_fee_ceiling()
        )


def test_unknown_usage_is_accounting_halt_with_full_reservation(tmp_path):
    with DurableJournal(tmp_path / "j") as log:
        seeded(log)
        obj = response_object()
        del obj["usage"]
        text, gens, _, provider = one_generation(
            tmp_path, log, lambda r: httpx.Response(200, json=obj)
        )
        assert text == "good" and halts(log) == [("accounting_halt", False)]
        assert settlements(log)[-1] == "retained_unknown"
        assert gens[0]["metadata"]["computed_charge_usd"] is None


def test_profile_drift_after_baseline_is_ivf_and_absent_field_is_change(tmp_path):
    with DurableJournal(tmp_path / "j") as log:
        seeded(log)
        text, _, _, _ = one_generation(tmp_path, log, lambda r: gen_ok(store=True))
        assert text is None and halts(log) == [("ivf_halt:profile_echo_mismatch:store", True)]
    with DurableJournal(tmp_path / "j2") as log:
        seeded(log)
        (tmp_path / "y").mkdir()
        text, _, _, _ = one_generation(tmp_path / "y", log, lambda r: gen_ok(temperature=1.0))
        assert text is None and halts(log) == [("ivf_halt:identity_change:temperature", True)]


def test_identical_repeated_responses_never_false_halt_after_reopen(tmp_path):
    with DurableJournal(tmp_path / "j") as log:
        seeded(log)
        provider, _, clock = make_provider(tmp_path, log, Fabricated())
        runner = make_runner(log, clock)
        runner.initialize([[0.0] * 20] * 10)
        runner._logical(provider, {"system": "s", "user": "u", "max_tokens": 8192}, 1, 1)
    with DurableJournal(tmp_path / "j") as log:  # close/reopen: baseline read back from JSON
        (tmp_path / "z").mkdir()
        provider, _, clock = make_provider(tmp_path / "z", log, Fabricated())
        runner = make_runner(log, clock, block=1)
        runner.initialize([[0.0] * 20] * 10)
        assert (
            runner._logical(provider, {"system": "s", "user": "u", "max_tokens": 8192}, 1, 1)
            == "good"
        )
        assert not halts(log)


def test_e9_scope_records_provisional_observation_never_baseline(tmp_path):
    with DurableJournal(tmp_path / "j") as log:
        text, gens, handler, provider = one_generation(
            tmp_path, log, lambda r: gen_ok(), scope="e9"
        )
        assert text == "good"
        obs = events(log, "identity_observation")
        assert len(obs) == 1 and obs[0]["provisional"] is True and obs[0]["accepted"] is False
        assert not events(log, "identity_baseline")
        # a later E9 response with a different frozen object is an e9_fail (drift within E9)
        runner = make_runner(log, Clock(), block=1)
        runner.initialize([[0.0] * 20] * 10)
        handler.generation = lambda r: gen_ok(
            text={"verbosity": "medium", "format": {"type": "json"}}
        )
        runner._logical(provider, {"system": "s", "user": "u", "max_tokens": 8192}, 1, 1)
        assert halts(log) == [("e9_fail:identity_change:text", True)]


def test_e9_profile_anomaly_before_any_observation_is_compatibility_not_ivf(tmp_path):
    with DurableJournal(tmp_path / "j") as log:
        text, _, _, _ = one_generation(tmp_path, log, lambda r: gen_ok(background=True), scope="e9")
        assert text is None
        assert halts(log) == [("e9_fail:profile_unsafe_value:background", False)]
        assert not events(log, "identity_observation")


def test_failed_objects_settle_before_classification(tmp_path):
    def failed(code):
        obj = response_object(status="failed", error={"code": code, "message": "fabricated"})
        obj["output"] = []
        return lambda r: httpx.Response(200, json=obj)

    with DurableJournal(tmp_path / "j") as log:
        seeded(log)
        text, gens, handler, provider = one_generation(tmp_path, log, failed("server_error"))
        assert text is None and [g["category"] for g in gens] == ["gen_failed_retryable"] * 3
        assert settlements(log).count("settled_actual") == 3 and not halts(log)
    with DurableJournal(tmp_path / "j2") as log:
        seeded(log)
        (tmp_path / "w").mkdir()
        text, gens, _, _ = one_generation(tmp_path / "w", log, failed("invalid_prompt"))
        assert text is None and [g["category"] for g in gens] == ["gen_failed_terminal"]
        assert not halts(log)


def test_incomplete_object_is_received_with_reason_and_text(tmp_path):
    with DurableJournal(tmp_path / "j") as log:
        seeded(log)
        text, gens, _, _ = one_generation(
            tmp_path,
            log,
            lambda r: gen_ok(
                "bad", status="incomplete", incomplete_details={"reason": "max_output_tokens"}
            ),
        )
        assert text == "bad" and gens[0]["category"] == "received_incomplete"
        assert gens[0]["metadata"]["incomplete_reason"] == "max_output_tokens"


@pytest.mark.parametrize("status", ["in_progress", "queued", "cancelled", None])
def test_unexpected_response_status_is_compatibility_halt(tmp_path, status):
    obj = response_object(status=status)
    if status is None:
        del obj["status"]
    with DurableJournal(tmp_path / "j") as log:
        seeded(log)
        text, gens, _, _ = one_generation(tmp_path, log, lambda r: httpx.Response(200, json=obj))
        assert text is None and gens[0]["category"] == "gen_contract_anomaly"
        reason, ivf = halts(log)[0]
        assert reason.startswith("compatibility_halt:unexpected_response_status") and not ivf


def test_duplicate_key_generation_body_is_compatibility_halt_with_retained_reservation(tmp_path):
    body = json.dumps(response_object()).encode()[:-1] + b',"status":"completed"}'
    with DurableJournal(tmp_path / "j") as log:
        seeded(log)
        text, gens, _, _ = one_generation(
            tmp_path,
            log,
            lambda r: httpx.Response(
                200, content=body, headers={"content-type": "application/json"}
            ),
        )
        assert text is None and halts(log)[0][0].startswith(
            "compatibility_halt:gen_body_unparseable"
        )
        assert settlements(log)[-1] == "retained_unknown"


def test_refusal_or_reasoning_only_output_is_zero_valid_text(tmp_path):
    refusal = response_object()
    refusal["output"][1]["content"] = [
        {"type": "refusal", "refusal": "no"},
        {"type": "output_text", "text": "good"},
    ]
    assert extract_output_text(refusal)[0] == ""
    reasoning_only = response_object()
    reasoning_only["output"] = [
        {"type": "reasoning", "summary": [{"type": "summary_text", "text": "good"}]}
    ]
    assert extract_output_text(reasoning_only)[0] == ""
    with DurableJournal(tmp_path / "j") as log:
        seeded(log)
        provider, _, clock = make_provider(
            tmp_path, log, Fabricated(generation=lambda r: httpx.Response(200, json=refusal))
        )
        result = run(make_runner(log, clock), provider)
        assert result["logical_calls"] == 38 and result["forfeits"] == 190 and not halts(log)


def test_generation_http_statuses(tmp_path):
    for status, category, halt in [
        (401, "gen_halt_credential", "credential_halt:http_401"),
        (403, "gen_halt_credential", "credential_halt:http_403"),
        (400, "gen_terminal", None),
        (307, "gen_contract_anomaly", "compatibility_halt:unexpected_http_status:307"),
    ]:
        base = tmp_path / str(status)
        base.mkdir()
        with DurableJournal(base / "j") as log:
            seeded(log)
            text, gens, handler, _ = one_generation(
                base, log, lambda r, s=status: httpx.Response(s, json={"error": {"message": "x"}})
            )
            assert text is None and gens[0]["category"] == category
            assert len(handler.requests) == 2
            assert settlements(log)[-1] == "retained_unknown"
            assert halts(log) == ([(halt, False)] if halt else [])


def test_response_retention_failure_after_dispatch_halts_and_keeps_reservation(
    tmp_path, monkeypatch
):
    calls = {"n": 0}
    original = RequestRecords.write

    def flaky(self, name, data):
        if name.endswith(".response.body"):
            calls["n"] += 1
            raise OSError("fabricated disk failure")
        return original(self, name, data)

    monkeypatch.setattr(RequestRecords, "write", flaky)
    with DurableJournal(tmp_path / "j") as log:
        seeded(log)
        handler = Fabricated()
        provider, runner, _ = logical_once(tmp_path, log, handler)
        runner._logical(provider, {"system": "s", "user": "u", "max_tokens": 8192}, 1, 1)
        assert len(handler.requests) == 1 and calls["n"] == 1
        assert halts(log) == [("response_retention_failed:OSError", False)]
        assert settlements(log) == ["retained_ceiling"]
        assert events(log, "provider_attempt")[0]["category"] == "count_terminal"
