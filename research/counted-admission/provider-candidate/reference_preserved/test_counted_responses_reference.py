"""Offline tests with fabricated values only. No network, no objective, no optimizer."""

import copy
import json
from datetime import datetime, timezone
from decimal import Decimal, getcontext, localcontext
from fractions import Fraction

import pytest

import counted_responses_reference as ref

SYS = "SYSTEM TEXT (fabricated)\n"
USR = "USER TEXT (fabricated) 0.5 0.25 1e-300\n"
EFF = "medium"
RATES = ref.rates_per_million("4", "0.4", "5", "20")
MTOK = Fraction(1, 1_000_000)


def gen():
    return ref.build_generation_body(SYS, USR, reasoning_effort=EFF)


def ok_response(input_tokens=777, output_tokens=10, status="completed", **over):
    p = {
        "object": "response",
        "status": status,
        "model": "gpt-5.6-sol",
        "service_tier": "default",
        "truncation": "disabled",
        "max_output_tokens": 8192,
        "store": False,
        "reasoning": {"effort": EFF, "mode": "standard"},
        "text": {"verbosity": "medium", "format": {"type": "text"}},
        "prompt_cache_options": {"mode": "explicit"},
        "temperature": None,
        "top_p": None,
        "tools": [],
        "usage": {
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": input_tokens + output_tokens,
            "input_tokens_details": {"cached_tokens": 0, "cache_write_tokens": 0},
            "output_tokens_details": {"reasoning_tokens": 0},
        },
    }
    p.update(over)
    return p


# ------------------------------------------------------------ bodies / pair
def test_projection_and_pair_are_exact_and_non_aliased():
    g = gen()
    c = ref.project_count_body(g, reasoning_effort=EFF)
    assert set(c) == {"model", "input", "reasoning", "text", "truncation"}
    assert c["input"] is not g["input"] and c["reasoning"] is not g["reasoning"]
    ref.verify_pair(g, c, reasoning_effort=EFF)
    b = ref.bind_pair(g, reasoning_effort=EFF)
    assert b["count_sha256"] == ref.sha256(ref.canonical_bytes(c))
    assert b["generation_sha256"] == ref.sha256(ref.canonical_bytes(g))
    # mutating the generation body after projection is detected
    g["reasoning"]["effort"] = "high"
    with pytest.raises(ref.ContractViolation):
        ref.verify_pair(g, c, reasoning_effort=EFF)


@pytest.mark.parametrize(
    "mutate",
    [
        lambda g: g.__setitem__("model", "gpt-5.6"),
        lambda g: g["reasoning"].__setitem__("effort", "high"),
        lambda g: g["reasoning"].__setitem__("mode", "pro"),
        lambda g: g["text"].__setitem__("verbosity", "low"),
        lambda g: g["text"].__setitem__("format", {"type": "text"}),
        lambda g: g.__setitem__("truncation", "auto"),
        lambda g: g.__setitem__("max_output_tokens", 8192.0),
        lambda g: g.__setitem__("max_output_tokens", True),
        lambda g: g.__setitem__("max_output_tokens", 8191),
        lambda g: g.__setitem__("store", 0),
        lambda g: g.__setitem__("store", True),
        lambda g: g.__setitem__("stream", None),
        lambda g: g.__setitem__("service_tier", "auto"),
        lambda g: g["prompt_cache_options"].__setitem__("ttl", "30m"),
        lambda g: g.__setitem__("prompt_cache_options", {"mode": "implicit"}),
        lambda g: g["input"].__setitem__(0, {"role": "system", "content": SYS}),
        lambda g: g["input"].append({"role": "user", "content": "x"}),
        lambda g: g["input"][1].__setitem__(
            "content", [{"type": "input_text", "text": "x"}]
        ),
        lambda g: g["input"][1].__setitem__("content", "non-ascii \u00e9"),
        lambda g: g["input"][1].__setitem__("phase", "x"),
        lambda g: g.__setitem__("personality", "pragmatic"),
        lambda g: g.__setitem__("instructions", "x"),
        lambda g: g.__setitem__("temperature", 0.0),
        lambda g: g.__setitem__("tools", []),
        lambda g: g.__setitem__("previous_response_id", "resp_1"),
        lambda g: g.__setitem__("prompt_cache_key", "k"),
        lambda g: g.__setitem__("context_management", []),
        lambda g: g.__setitem__("unknown_future_field", 1),
        lambda g: g.pop("store"),
    ],
)
def test_every_profile_mutation_is_rejected_before_projection(mutate):
    g = gen()
    mutate(g)
    with pytest.raises(ref.ContractViolation):
        ref.project_count_body(g, reasoning_effort=EFF)
    with pytest.raises(ref.ContractViolation):
        ref.validate_generation_body(g, reasoning_effort=EFF)


def test_verify_pair_rejects_altered_count_body_values():
    g = gen()
    c = ref.project_count_body(g, reasoning_effort=EFF)
    for k, v in [
        ("model", "gpt-5.6"),
        ("truncation", "auto"),
        ("reasoning", {"effort": "low"}),
    ]:
        c2 = copy.deepcopy(c)
        c2[k] = v
        with pytest.raises(ref.ContractViolation):
            ref.verify_pair(g, c2, reasoning_effort=EFF)
    c3 = copy.deepcopy(c)
    c3["personality"] = "friendly"
    with pytest.raises(ref.ContractViolation):
        ref.verify_pair(g, c3, reasoning_effort=EFF)


def test_unsupported_effort_including_undocumented_minimal_is_refused():
    for e in ("minimal", "MEDIUM", "", None):
        with pytest.raises(ref.ContractViolation):
            ref.build_generation_body(SYS, USR, reasoning_effort=e)


def test_sent_bytes_and_url_must_match_exactly():
    b = ref.bind_pair(gen(), reasoning_effort=EFF)
    ref.verify_sent_bytes(
        b["count_bytes"], b["count_bytes"], ref.COUNT_ENDPOINT, ref.COUNT_ENDPOINT
    )
    with pytest.raises(ref.ContractViolation):
        ref.verify_sent_bytes(
            b["count_bytes"] + b" ",
            b["count_bytes"],
            ref.COUNT_ENDPOINT,
            ref.COUNT_ENDPOINT,
        )
    with pytest.raises(ref.ContractViolation):
        ref.verify_sent_bytes(
            b["count_bytes"],
            b["count_bytes"],
            ref.GENERATION_ENDPOINT,
            ref.COUNT_ENDPOINT,
        )


# --------------------------------------------------------------- admission
def test_admission_strict_types_and_limit():
    assert ref.admit(272_000, 272_000) == "admitted"
    assert ref.admit(272_001, 272_000) == "admission_rejected"
    assert ref.admit(0, 1) == "admitted"
    for bad in (True, -1, 1.0, "5", None):
        with pytest.raises(ref.ContractViolation):
            ref.admit(bad, 272_000)
    for bad_limit in (True, 0, -5, 272000.0, "272000", None):
        with pytest.raises(ref.ContractViolation):
            ref.admit(5, bad_limit)


@pytest.mark.parametrize(
    "payload,expected_tokens,expected_findings",
    [
        ({"object": "response.input_tokens", "input_tokens": 12345}, 12345, []),
        ({"object": "response.input_tokens", "input_tokens": 0}, 0, []),
        (
            {"object": "response.input_tokens", "input_tokens": 5, "extra": 1},
            5,
            ["count_extra_fields:extra"],
        ),
        (
            {"object": "response.input_tokens", "input_tokens": True},
            None,
            ["count_input_tokens_invalid"],
        ),
        (
            {"object": "response.input_tokens", "input_tokens": -1},
            None,
            ["count_input_tokens_invalid"],
        ),
        ({"object": "response.input_tokens"}, None, ["count_input_tokens_invalid"]),
        ({"input_tokens": 5}, None, ["count_object_field_invalid"]),
        (
            {"object": "response", "input_tokens": 5},
            None,
            ["count_object_field_invalid"],
        ),
        ("not an object", None, ["count_payload_not_object"]),
        (None, None, ["count_payload_not_object"]),
        ([], None, ["count_payload_not_object"]),
    ],
)
def test_count_payload_validation(payload, expected_tokens, expected_findings):
    assert ref.validate_count_payload(payload) == (expected_tokens, expected_findings)


def test_strict_json_rejects_duplicate_keys_at_any_depth():
    obj, err = ref.parse_json_strict(
        b'{"object":"response.input_tokens","input_tokens":1,"input_tokens":2}'
    )
    assert obj is None and err.startswith("malformed_json")
    obj, err = ref.parse_json_strict(b'{"usage":{"input_tokens":1,"input_tokens":1}}')
    assert obj is None
    obj, err = ref.parse_json_strict(b"\xff\xfe")
    assert obj is None
    obj, err = ref.parse_json_strict(
        b'{"object":"response.input_tokens","input_tokens":1}'
    )
    assert err is None and obj["input_tokens"] == 1


# ----------------------------------------------------------- classification
@pytest.mark.parametrize(
    "status,payload,err,expected",
    [
        (
            200,
            {"object": "response.input_tokens", "input_tokens": 12345},
            None,
            ("count_ok", False),
        ),
        (
            200,
            {"object": "response.input_tokens", "input_tokens": True},
            None,
            ("count_contract_anomaly", False),
        ),
        (
            200,
            {"object": "response", "input_tokens": 5},
            None,
            ("count_contract_anomaly", False),
        ),
        (200, "not json", None, ("count_contract_anomaly", False)),
        (200, None, None, ("count_contract_anomaly", False)),
        (429, None, None, ("count_retryable", True)),
        (503, None, None, ("count_retryable", True)),
        (None, None, "timeout", ("count_retryable", True)),
        (None, None, "connection", ("count_retryable", True)),
        (None, None, "weird", ("count_contract_anomaly", False)),
        (None, None, None, ("count_contract_anomaly", False)),
        ("200", None, None, ("count_contract_anomaly", False)),
        (True, None, None, ("count_contract_anomaly", False)),
        (302, None, None, ("count_contract_anomaly", False)),
        (400, None, None, ("count_terminal", False)),
        (413, None, None, ("count_terminal", False)),
        (401, None, None, ("count_halt_credential", False)),
        (402, None, None, ("count_halt_credential", False)),
        (403, None, None, ("count_halt_credential", False)),
    ],
)
def test_count_classification(status, payload, err, expected):
    assert ref.classify_count_outcome(status, payload, err) == expected


@pytest.mark.parametrize(
    "status,payload,err,expected",
    [
        (200, {"status": "completed"}, None, ("received_completed", False)),
        (
            200,
            {
                "status": "incomplete",
                "incomplete_details": {"reason": "max_output_tokens"},
            },
            None,
            ("received_incomplete", False),
        ),
        (
            200,
            {"status": "failed", "error": {"code": "server_error"}},
            None,
            ("gen_failed_retryable", True),
        ),
        (
            200,
            {"status": "failed", "error": {"code": "rate_limit_exceeded"}},
            None,
            ("gen_failed_retryable", True),
        ),
        (
            200,
            {"status": "failed", "error": {"code": "invalid_prompt"}},
            None,
            ("gen_failed_terminal", False),
        ),
        (
            200,
            {"status": "failed", "error": None},
            None,
            ("gen_failed_terminal", False),
        ),
        (
            200,
            {"status": "failed", "error": "oops"},
            None,
            ("gen_failed_terminal", False),
        ),
        (200, {"status": "failed"}, None, ("gen_failed_terminal", False)),
        (200, {"status": "in_progress"}, None, ("gen_contract_anomaly", False)),
        (200, {"status": "queued"}, None, ("gen_contract_anomaly", False)),
        (200, {"status": "cancelled"}, None, ("gen_contract_anomaly", False)),
        (200, {}, None, ("gen_contract_anomaly", False)),
        (200, None, None, ("gen_contract_anomaly", False)),
        (200, [], None, ("gen_contract_anomaly", False)),
        (500, None, None, ("gen_retryable", True)),
        (None, None, "connection", ("gen_retryable", True)),
        (None, None, "dns_mystery", ("gen_contract_anomaly", False)),
        (404, None, None, ("gen_terminal", False)),
        (403, None, None, ("gen_halt_credential", False)),
        (None, None, None, ("gen_contract_anomaly", False)),
    ],
)
def test_generation_classification(status, payload, err, expected):
    assert ref.classify_generation_outcome(status, payload, err) == expected


# -------------------------------------------------------------- Retry-After
T0 = datetime(2026, 9, 8, 12, 0, 0, tzinfo=timezone.utc)


def test_retry_after_parsing():
    assert ref.parse_retry_after(None, None, T0) == (None, None)
    assert ref.parse_retry_after("56", None, T0) == (56, None)
    assert ref.parse_retry_after(" 0 ", None, T0) == (0, None)
    assert ref.parse_retry_after("-5", None, T0) == (None, "retry_after_malformed")
    assert ref.parse_retry_after("5.5", None, T0) == (None, "retry_after_malformed")
    assert ref.parse_retry_after("soon", None, T0) == (None, "retry_after_malformed")
    # HTTP-date measured against the server Date header when present
    assert ref.parse_retry_after(
        "Tue, 08 Sep 2026 12:01:00 GMT", "Tue, 08 Sep 2026 12:00:00 GMT", T0
    ) == (60, None)
    # ... else against receipt time
    assert ref.parse_retry_after("Tue, 08 Sep 2026 12:00:30 GMT", None, T0) == (
        30,
        None,
    )
    # date in the past: minimum already satisfied, recorded as a finding
    assert ref.parse_retry_after("Tue, 08 Sep 2026 11:00:00 GMT", None, T0) == (
        0,
        "retry_after_date_in_past",
    )


@pytest.mark.parametrize(
    "attempt,ra,finding,remaining,expected",
    [
        (1, None, None, 36000, (True, 5, "retry")),
        (2, None, None, 36000, (True, 20, "retry")),
        (3, None, None, 36000, (False, None, "attempts_exhausted")),
        (1, 56, None, 36000, (True, 56, "retry")),  # server minimum honoured in full
        (
            2,
            10,
            None,
            36000,
            (True, 20, "retry"),
        ),  # fixed backoff is the larger minimum
        (1, 300, None, 36000, (True, 300, "retry")),
        (
            1,
            301,
            None,
            36000,
            (False, None, "retry_after_exceeds_attempt_cap"),
        ),  # never capped downward
        (
            1,
            None,
            "retry_after_malformed",
            36000,
            (False, None, "retry_after_malformed"),
        ),
        (1, 0, "retry_after_date_in_past", 36000, (True, 5, "retry")),
        (
            1,
            50,
            None,
            50,
            (False, None, "deadline_insufficient"),
        ),  # wait + margin must fit
        (1, 50, None, 51, (True, 50, "retry")),
        (1, None, None, None, (False, None, "remaining_deadline_unknown")),
        (1, None, None, float("nan"), (False, None, "remaining_deadline_invalid")),
        (1, None, None, float("inf"), (False, None, "remaining_deadline_invalid")),
        (1, None, None, True, (False, None, "remaining_deadline_unknown")),
        (1, None, None, "36000", (False, None, "remaining_deadline_invalid")),
        (1, None, None, 36000.0, (True, 5, "retry")),
    ],
)
def test_retry_decision_is_predetermined(attempt, ra, finding, remaining, expected):
    assert ref.retry_decision(attempt, ra, finding, remaining) == expected


@pytest.mark.parametrize("attempt", [True, False, 0, -1, 1.0, "1", None])
def test_retry_decision_rejects_invalid_attempt_numbers(attempt):
    with pytest.raises(ref.ContractViolation):
        ref.retry_decision(attempt, None, None, 36000)


@pytest.mark.parametrize("ra", [True, -1, 5.0, "5"])
def test_retry_decision_rejects_invalid_retry_after_values(ra):
    with pytest.raises(ref.ContractViolation):
        ref.retry_decision(1, ra, None, 36000)


# -------------------------------------------------------- identity / usage
def test_expected_profile_validation_precedes_baseline():
    assert ref.validate_expected_profile(ok_response(), reasoning_effort=EFF) == []
    assert ref.validate_expected_profile(
        ok_response(model="gpt-5.6"), reasoning_effort=EFF
    ) == ["profile_echo_mismatch:model"]
    assert "profile_echo_mismatch:max_output_tokens" in ref.validate_expected_profile(
        ok_response(max_output_tokens=True), reasoning_effort=EFF
    )
    assert "profile_echo_mismatch:store" in ref.validate_expected_profile(
        ok_response(store=0), reasoning_effort=EFF
    )
    bad = ok_response()
    del bad["service_tier"]
    assert ref.validate_expected_profile(bad, reasoning_effort=EFF) == [
        "profile_echo_missing:service_tier"
    ]
    assert ref.validate_expected_profile(
        ok_response(reasoning={"effort": "high"}), reasoning_effort=EFF
    ) == ["profile_echo_mismatch:reasoning.effort"]
    assert ref.validate_expected_profile(
        ok_response(text={"format": {"type": "text"}}), reasoning_effort=EFF
    ) == ["profile_echo_missing:text.verbosity"]
    assert ref.validate_expected_profile(
        ok_response(reasoning="medium"), reasoning_effort=EFF
    ) == ["profile_echo_missing:reasoning.effort", "profile_echo_mismatch:reasoning"]
    assert ref.validate_expected_profile(None, reasoning_effort=EFF) == [
        "response_not_object"
    ]
    with pytest.raises(ref.ContractViolation):
        ref.validate_expected_profile(ok_response(), reasoning_effort="minimal")


@pytest.mark.parametrize(
    "over,finding",
    [
        ({"background": True}, "profile_unsafe_value:background"),
        ({"background": 0}, "profile_unsafe_value:background"),
        ({"tools": [{"type": "web_search"}]}, "profile_unsafe_value:tools"),
        ({"tools": None}, "profile_unsafe_value:tools"),
        ({"object": "chat.completion"}, "profile_echo_mismatch:object"),
    ],
)
def test_unsafe_optional_values_fail_even_on_first_baseline(over, finding):
    assert ref.validate_expected_profile(ok_response(**over), reasoning_effort=EFF) == [
        finding
    ]


def test_absent_optional_safe_fields_are_acceptable():
    p = ok_response()
    del p["tools"]
    assert ref.validate_expected_profile(p, reasoning_effort=EFF) == []
    assert ref.identity_vector(p)["tools"] == ("absent",)


def test_identity_vector_is_presence_tagged_and_covers_whole_frozen_objects():
    base = ref.identity_vector(ok_response())
    assert base["temperature"] == ("present", "null")
    assert base["background"] == ("absent",)
    assert base["reasoning"] == ("present", '{"effort":"medium","mode":"standard"}')
    assert all(
        isinstance(v, tuple) and v[0] in ("present", "absent") for v in base.values()
    )
    assert ref.compare_identity(ref.identity_vector(ok_response()), base) == []
    # nested field changes inside frozen objects are detected without being enumerated
    changed = ref.identity_vector(ok_response(reasoning={"effort": EFF, "mode": "pro"}))
    assert ref.compare_identity(changed, base) == ["identity_change:reasoning"]
    novel = ref.identity_vector(
        ok_response(reasoning={"effort": EFF, "mode": "standard", "brand_new": 1})
    )
    assert ref.compare_identity(novel, base) == ["identity_change:reasoning"]
    vanished = ref.identity_vector(ok_response(reasoning={"effort": EFF}))
    assert ref.compare_identity(vanished, base) == ["identity_change:reasoning"]
    cache = ref.identity_vector(
        ok_response(prompt_cache_options={"mode": "explicit", "ttl": "30m"})
    )
    assert ref.compare_identity(cache, base) == ["identity_change:prompt_cache_options"]
    appeared = ref.identity_vector(ok_response(temperature=1.0))
    assert ref.compare_identity(appeared, base) == ["identity_change:temperature"]
    # "null" and absent are different states
    nulled = ok_response()
    del nulled["temperature"]
    assert ref.compare_identity(ref.identity_vector(nulled), base) == [
        "identity_change:temperature"
    ]
    # a key missing from either vector is a change
    assert ref.compare_identity(
        {k: v for k, v in base.items() if k != "model"}, base
    ) == ["identity_change:model"]
    with pytest.raises(ref.ContractViolation):
        ref.identity_vector("not an object")


def test_usage_checks_on_every_object_kind_and_unknowns():
    assert ref.usage_checks(ok_response(), 777) == []
    assert ref.usage_checks(ok_response(status="failed"), 777) == []
    assert ref.usage_checks(ok_response(), 778) == [
        "count_usage_mismatch:counted=778,usage=777"
    ]
    cached = ok_response()
    cached["usage"]["input_tokens_details"]["cached_tokens"] = 100
    assert ref.usage_checks(cached, 777) == ["cache_activity:cached_tokens=100"]
    over = ok_response()
    over["usage"]["input_tokens_details"]["cached_tokens"] = 1024
    assert ref.usage_checks(over, 777) == [
        "cache_activity:cached_tokens=1024",
        "cache_categories_exceed_input:cached=1024,written=0,input=777",
    ]
    missing = ok_response()
    del missing["usage"]["input_tokens_details"]
    assert ref.usage_checks(missing, 777) == ["input_tokens_details_unknown"]
    nou = ok_response()
    del nou["usage"]
    assert ref.usage_checks(nou, 777) == ["usage_missing_unknown"]
    boolish = ok_response()
    boolish["usage"]["output_tokens"] = True
    assert ref.usage_checks(boolish, 777) == ["output_tokens_unknown"]
    assert ref.usage_checks("x", 777) == ["response_not_object"]


# ------------------------------------------------------------------- money
def test_rate_grammar_rejects_nonfinite_float_bool_zero_and_unbounded():
    for bad in (
        "Infinity",
        "-Infinity",
        "NaN",
        Decimal("Infinity"),
        Decimal("NaN"),
        0,
        "0",
        "-4",
        True,
        4.0,
        "abc",
        None,
    ):
        with pytest.raises(ref.ContractViolation):
            ref.rates_per_million(bad, "0.4", "5", "20")
    with pytest.raises(ref.ContractViolation):
        ref.rates_per_million(
            "4", "0.4", "5", "2000000"
        )  # 2 USD per token: outside bounded grammar
    with pytest.raises(ref.ContractViolation):
        ref.validate_rates({"input": MTOK})  # missing categories
    with pytest.raises(ref.ContractViolation):
        ref.validate_rates({**RATES, "extra": MTOK})
    assert ref.validate_rates(RATES) == RATES


def test_money_is_independent_of_ambient_decimal_context():
    expected = Fraction(272_000) * 4 * MTOK + Fraction(8192) * 20 * MTOK
    assert expected == Fraction(125184, 100000)
    saved = getcontext().prec
    try:
        with localcontext() as ctx:
            ctx.prec = 2
            r = ref.reservation_for_generation(272_000, RATES)
            assert r == expected
            assert ref.money_str(r) == "1.251840"
            assert (
                ref.money_str(ref.reservation_for_generation(200_000, RATES))
                == "0.963840"
            )
            c = ref.charge_from_usage(
                ok_response(input_tokens=1000, output_tokens=100)["usage"], RATES
            )
            assert c == Fraction(1000) * 4 * MTOK + Fraction(100) * 20 * MTOK
            assert ref.money_str(c) == "0.006000"
    finally:
        assert getcontext().prec == saved
    with pytest.raises(ref.ContractViolation):
        ref.money_str(Fraction(1, 3))  # non-terminating: never silently rounded
    with pytest.raises(ref.ContractViolation):
        ref.money_str(Decimal("1.0"))


def test_total_tokens_is_mandatory_and_must_reconcile():
    ok = ok_response(input_tokens=777, output_tokens=10)
    assert ok["usage"]["total_tokens"] == 787 and ref.usage_checks(ok, 777) == []
    missing = ok_response()
    del missing["usage"]["total_tokens"]
    assert ref.usage_checks(missing, 777) == ["total_tokens_unknown"]
    for bad in (True, -1, 787.0, "787", None):
        p = ok_response()
        p["usage"]["total_tokens"] = bad
        assert ref.usage_checks(p, 777) == ["total_tokens_unknown"]
    inconsistent = ok_response()
    inconsistent["usage"]["total_tokens"] = 800
    assert ref.usage_checks(inconsistent, 777) == [
        "total_tokens_inconsistent:total=800,input=777,output=10"
    ]
    neg = ok_response()
    neg["usage"]["input_tokens"] = -1
    assert "input_tokens_unknown" in ref.usage_checks(neg, 777)
    # reasoning tokens are informational: consistent values add nothing, impossible values are recorded only
    r = ok_response()
    r["usage"]["output_tokens_details"]["reasoning_tokens"] = 10
    assert ref.usage_checks(r, 777) == []
    r["usage"]["output_tokens_details"]["reasoning_tokens"] = 11
    assert ref.usage_checks(r, 777) == ["reasoning_tokens_informational_inconsistent"]
    del r["usage"]["output_tokens_details"]
    assert ref.usage_checks(r, 777) == []


def test_missing_or_inconsistent_total_is_an_accounting_halt_without_zero_substitution():
    res = ref.reservation_for_generation(777, RATES)
    expected_charge = Fraction(777) * 4 * MTOK + Fraction(10) * 20 * MTOK
    # inconsistent total: category-based charge preserved, raw report preserved, NOT reconciled, accounting halt
    p = ok_response()
    p["usage"]["total_tokens"] = 9999
    s = ref.settle_response(p, 777, res, RATES, policy="study")
    assert s["halt"] == "accounting_halt" and s["reconciled"] is False
    assert s["charge"] == expected_charge and s["reservation_retained"] is True
    assert s["usage"]["total_tokens"] == 9999
    assert s["findings"] == ["total_tokens_inconsistent:total=9999,input=777,output=10"]
    assert ref.settle_response(p, 777, res, RATES, policy="e9")["halt"] == "e9_fail"
    # missing total: same, no zero substituted
    m = ok_response()
    del m["usage"]["total_tokens"]
    s = ref.settle_response(m, 777, res, RATES, policy="study")
    assert (
        s["halt"] == "accounting_halt"
        and s["reconciled"] is False
        and s["charge"] == expected_charge
    )
    assert "total_tokens" not in s["usage"]
    # reasoning tokens never change the charge (inclusive output)
    r = ok_response()
    r["usage"]["output_tokens_details"]["reasoning_tokens"] = 10
    s = ref.settle_response(r, 777, res, RATES, policy="study")
    assert (
        s["halt"] is None and s["reconciled"] is True and s["charge"] == expected_charge
    )
    r["usage"]["output_tokens_details"]["reasoning_tokens"] = (
        11  # informational inconsistency only
    )
    s = ref.settle_response(r, 777, res, RATES, policy="study")
    assert (
        s["halt"] is None
        and s["reconciled"] is True
        and s["findings"] == ["reasoning_tokens_informational_inconsistent"]
    )
    # IVF finding outranks an accounting finding in halt class; both findings preserved
    both = ok_response(input_tokens=778)
    both["usage"]["total_tokens"] = 1
    s = ref.settle_response(both, 777, res, RATES, policy="study")
    assert (
        s["halt"] == "ivf_halt" and len(s["findings"]) == 2 and s["reconciled"] is False
    )
    # fully consistent report is reconciled and releases the reservation
    s = ref.settle_response(ok_response(), 777, res, RATES, policy="study")
    assert s["reconciled"] is True and s["reservation_retained"] is False


def test_charges_are_exact_unclipped_and_unknown_when_categories_missing():
    u = ok_response(input_tokens=1000, output_tokens=100)["usage"]
    u2 = json.loads(json.dumps(u))
    u2["input_tokens_details"] = {"cached_tokens": 200, "cache_write_tokens": 300}
    assert (
        ref.charge_from_usage(u2, RATES)
        == (
            Fraction(500) * 4
            + Fraction(200) * Fraction(4, 10)
            + Fraction(300) * 5
            + Fraction(100) * 20
        )
        * MTOK
    )
    u3 = json.loads(json.dumps(u))
    del u3["input_tokens_details"]
    assert ref.charge_from_usage(u3, RATES) is None
    u4 = json.loads(json.dumps(u))
    u4["input_tokens_details"] = {"cached_tokens": 900, "cache_write_tokens": 900}
    assert ref.charge_from_usage(u4, RATES) is None
    u5 = json.loads(json.dumps(u))
    u5["output_tokens"] = -1
    assert ref.charge_from_usage(u5, RATES) is None
    assert ref.charge_from_usage(None, RATES) is None
    with pytest.raises(ref.ContractViolation):
        ref.charge_from_usage(u, {**RATES, "output": Fraction(0)})
    with pytest.raises(ref.ContractViolation):
        ref.charge_from_usage(u, {**RATES, "output": float("inf")})


def test_reservation_validation():
    assert ref.reservation_for_generation(272_000, RATES) == Fraction(125184, 100000)
    for bad in (True, -1, 1.0, "5"):
        with pytest.raises(ref.ContractViolation):
            ref.reservation_for_generation(bad, RATES)
    with pytest.raises(ref.ContractViolation):
        ref.reservation_for_generation(5, {**RATES, "input": "Infinity"})


def test_settlement_semantics_e9_vs_study_and_entry_validation():
    res = ref.reservation_for_generation(777, RATES)
    s = ref.settle_response(ok_response(), 777, res, RATES, policy="study")
    assert (
        s["halt"] is None
        and s["overrun"] is False
        and s["reservation_retained"] is False
    )
    assert s["charge"] == Fraction(777) * 4 * MTOK + Fraction(10) * 20 * MTOK
    assert s["usage"]["input_tokens"] == 777  # received usage preserved
    s = ref.settle_response(
        ok_response(input_tokens=778), 777, res, RATES, policy="study"
    )
    assert s["halt"] == "ivf_halt" and s["charge"] is not None
    assert (
        ref.settle_response(
            ok_response(input_tokens=778), 777, res, RATES, policy="e9"
        )["halt"]
        == "e9_fail"
    )
    c = ok_response(input_tokens=777)
    c["usage"]["input_tokens_details"]["cache_write_tokens"] = 777
    s = ref.settle_response(c, 777, res, RATES, policy="study")
    assert s["halt"] == "ivf_halt" and s["charge"] > Fraction(777) * 4 * MTOK
    m = ok_response()
    del m["usage"]
    s = ref.settle_response(m, 777, res, RATES, policy="study")
    assert (
        s["halt"] == "accounting_halt"
        and s["reservation_retained"] is True
        and s["charge"] is None
        and s["usage"] is None
    )
    assert ref.settle_response(m, 777, res, RATES, policy="e9")["halt"] == "e9_fail"
    o = ok_response(output_tokens=9000)
    s = ref.settle_response(o, 777, res, RATES, policy="study")
    assert s["overrun"] is True and s["halt"] == "accounting_halt" and s["charge"] > res
    f = ok_response(status="failed", error={"code": "server_error"}, output_tokens=0)
    s = ref.settle_response(f, 777, res, RATES, policy="study")
    assert s["halt"] is None and s["charge"] == Fraction(777) * 4 * MTOK
    for bad_policy in ("prod", "", None, "E9"):
        with pytest.raises(ref.ContractViolation):
            ref.settle_response(ok_response(), 777, res, RATES, policy=bad_policy)
    for bad_res in (Decimal("1.0"), 1.0, Fraction(0), Fraction(-1), None):
        with pytest.raises(ref.ContractViolation):
            ref.settle_response(ok_response(), 777, bad_res, RATES, policy="study")
    with pytest.raises(ref.ContractViolation):
        ref.settle_response(ok_response(), True, res, RATES, policy="study")
    with pytest.raises(ref.ContractViolation):
        ref.settle_response(
            ok_response(), 777, res, {**RATES, "input": "NaN"}, policy="study"
        )


def _raw(p):
    return json.dumps(p).encode()


def test_handle_generation_response_settles_before_classifying():
    res = ref.reservation_for_generation(777, RATES)
    kw = {"policy": "study", "reasoning_effort": EFF}
    # a 2xx failed object with retryable code: usage charged and preserved, then classified retryable
    f = ok_response(status="failed", error={"code": "server_error"}, output_tokens=0)
    rec = ref.handle_generation_response(200, _raw(f), None, 777, res, RATES, **kw)
    assert rec["settlement"]["charge"] == Fraction(777) * 4 * MTOK
    assert rec["settlement"]["usage"]["input_tokens"] == 777
    assert rec["profile_findings"] == []
    assert rec["classification"] == ("gen_failed_retryable", True)
    # same but with unknown usage: accounting halt overrides retry
    f2 = ok_response(status="failed", error={"code": "server_error"})
    del f2["usage"]
    rec = ref.handle_generation_response(200, _raw(f2), None, 777, res, RATES, **kw)
    assert rec["settlement"]["halt"] == "accounting_halt" and rec["classification"] == (
        "gen_failed_retryable",
        False,
    )
    # mismatch on a completed object: IVF recorded with charge; classification still 'received'
    rec = ref.handle_generation_response(
        200, _raw(ok_response(input_tokens=778)), None, 777, res, RATES, **kw
    )
    assert rec["settlement"]["halt"] == "ivf_halt" and rec["classification"] == (
        "received_completed",
        False,
    )
    # duplicate keys in the body: anomaly, nothing settled
    rec = ref.handle_generation_response(
        200, b'{"status":"completed","status":"completed"}', None, 777, res, RATES, **kw
    )
    assert rec["parse_error"].startswith("malformed_json") and rec["settlement"] is None
    assert rec["classification"] == ("gen_contract_anomaly", False)
    # non-2xx: no settlement, ordinary classification
    rec = ref.handle_generation_response(503, b"", None, 777, res, RATES, **kw)
    assert rec["settlement"] is None and rec["classification"] == (
        "gen_retryable",
        True,
    )
    rec = ref.handle_generation_response(None, None, "timeout", 777, res, RATES, **kw)
    assert rec["settlement"] is None and rec["classification"] == (
        "gen_retryable",
        True,
    )
    # body not bytes on a 2xx: anomaly
    rec = ref.handle_generation_response(
        200, {"status": "completed"}, None, 777, res, RATES, **kw
    )
    assert rec["parse_error"] == "body_not_bytes" and rec["classification"] == (
        "gen_contract_anomaly",
        False,
    )
    # entry validation
    with pytest.raises(ref.ContractViolation):
        ref.handle_generation_response(
            200,
            _raw(ok_response()),
            None,
            777,
            res,
            RATES,
            policy="x",
            reasoning_effort=EFF,
        )
    with pytest.raises(ref.ContractViolation):
        ref.handle_generation_response(
            200, _raw(ok_response()), None, 777, Decimal(1), RATES, **kw
        )


def test_dispatch_margin_is_fixed_at_one_second():
    assert ref.DISPATCH_MARGIN_S == 1
    with pytest.raises(TypeError):
        ref.retry_decision(1, None, None, 36000, 5)  # margin is not a parameter


@pytest.mark.parametrize(
    "category,shalt,policy,expected",
    [
        ("count_retryable", None, "study", (None, True, False, "none")),
        ("gen_failed_retryable", None, "study", (None, True, False, "none")),
        ("count_terminal", None, "study", (None, False, False, "batch")),
        ("gen_failed_terminal", None, "study", (None, False, False, "batch")),
        ("admission_rejected", None, "study", (None, False, False, "batch")),
        (
            "count_halt_credential",
            None,
            "study",
            ("credential_halt", False, False, "run"),
        ),
        (
            "count_contract_anomaly",
            None,
            "study",
            ("compatibility_halt", False, False, "run"),
        ),
        (
            "gen_contract_anomaly",
            None,
            "study",
            ("compatibility_halt", False, False, "run"),
        ),
        (
            "contract_violation",
            None,
            "study",
            ("compatibility_halt", False, False, "run"),
        ),
        ("received_completed", None, "study", (None, False, True, "none")),
        ("received_incomplete", None, "study", (None, False, True, "none")),
        # accounting halt on a received text: evaluate it, suppress further calls, forfeit the rest
        (
            "received_completed",
            "accounting_halt",
            "study",
            ("accounting_halt", False, True, "run"),
        ),
        (
            "received_incomplete",
            "accounting_halt",
            "study",
            ("accounting_halt", False, True, "run"),
        ),
        # accounting halt on a failed-retryable object: no retry, nothing to evaluate
        (
            "gen_failed_retryable",
            "accounting_halt",
            "study",
            ("accounting_halt", False, False, "run"),
        ),
        # IVF discards the current proposal from evaluation
        ("received_completed", "ivf_halt", "study", ("ivf_halt", False, False, "run")),
        (
            "gen_failed_retryable",
            "ivf_halt",
            "study",
            ("ivf_halt", False, False, "run"),
        ),
        # E9: any settlement halt fails the preflight and evaluates nothing
        ("received_completed", "e9_fail", "e9", ("e9_fail", False, False, "run")),
        (
            "received_completed",
            "accounting_halt",
            "e9",
            ("e9_fail", False, False, "run"),
        ),
    ],
)
def test_attempt_consequences_are_predetermined(category, shalt, policy, expected):
    c = ref.attempt_consequence(category, shalt, policy=policy)
    assert (
        c["halt"],
        c["retry_allowed"],
        c["evaluate_received_text"],
        c["forfeit_batch_scope"],
    ) == expected
    assert c["raw_retained"] is True


def test_attempt_consequence_rejects_unknown_inputs():
    with pytest.raises(ref.ContractViolation):
        ref.attempt_consequence("something_new", None, policy="study")
    with pytest.raises(ref.ContractViolation):
        ref.attempt_consequence("received_completed", "soft_halt", policy="study")
    with pytest.raises(ref.ContractViolation):
        ref.attempt_consequence("received_completed", None, policy="prod")


def test_no_generation_without_count_evidence_admission_pair_and_profile():
    ok = {
        "count_category": "count_ok",
        "admission": "admitted",
        "pair_bound": True,
        "profile_valid": True,
        "halted": False,
    }
    assert ref.may_dispatch_generation(**ok)
    for k, v in [
        ("count_category", "count_contract_anomaly"),
        ("admission", "admission_rejected"),
        ("pair_bound", False),
        ("profile_valid", False),
        ("halted", True),
    ]:
        assert not ref.may_dispatch_generation(**{**ok, k: v})
