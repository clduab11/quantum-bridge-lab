"""Operational-copy fixes F1-F7, AuthorityRecord fail-closed rules, MoneyLedger."""

import json
from datetime import datetime, timezone
from fractions import Fraction

import pytest
from support import FAKE_HASH, response_object, synthetic_authority

from counted_responses_provider import contract as C
from counted_responses_provider.authority import AuthorityRecord, profile_sha256
from counted_responses_provider.ledger import LedgerHalted, MoneyLedger, fraction_from_text
from qbridge.journal import DurableJournal

# ----------------------------------------------------------------- F1..F7


def test_f1_canonical_bytes_refuses_nan_and_infinity():
    for bad in (float("nan"), float("inf")):
        with pytest.raises(ValueError):
            C.canonical_bytes({"x": bad})


def test_f2_strict_parse_rejects_nan_infinity_and_duplicates():
    assert C.parse_json_strict(b'{"input_tokens": NaN}')[0] is None
    assert C.parse_json_strict(b'{"a": Infinity}')[0] is None
    assert C.parse_json_strict(b'{"a": 1, "a": 2}')[0] is None
    assert C.parse_json_strict(b'{"a": {"b": 1, "b": 2}}')[0] is None
    assert C.parse_json_strict(b'{"a": 1}') == ({"a": 1}, None)


def test_f3_non_ascii_text_is_a_contract_violation():
    with pytest.raises(C.ContractViolation):
        C.build_generation_body("s", "caf\u00e9", reasoning_effort="medium")


@pytest.mark.parametrize(
    "value,expected",
    [
        ("7", (7, None)),
        ("\u0663", (None, "retry_after_malformed")),  # Arabic-Indic digit 3
        ("9" * 16, (None, "retry_after_malformed")),
        ("+5", (None, "retry_after_malformed")),
    ],
)
def test_f4_retry_after_ascii_bounded(value, expected):
    now = datetime(2026, 9, 9, tzinfo=timezone.utc)
    assert C.parse_retry_after(value, None, now) == expected


def test_f4_http_date_is_ceiled_against_date_header():
    now = datetime(2026, 9, 9, 12, 0, 0, tzinfo=timezone.utc)
    when = "Wed, 09 Sep 2026 12:00:03 GMT"
    assert C.parse_retry_after(when, "Wed, 09 Sep 2026 12:00:00 GMT", now) == (3, None)
    assert C.parse_retry_after(when, None, now) == (3, None)


@pytest.mark.parametrize(
    "bad", ["1e999999999", "1E5", "-4", "+4", " 4", "NaN", "Infinity", "4.", ".5"]
)
def test_f5_money_string_grammar_is_bounded(bad):
    with pytest.raises(C.ContractViolation):
        C._to_fraction(bad, "rate")


def test_f5_accepts_plain_decimals_exactly():
    assert C._to_fraction("0.4", "r") == Fraction(2, 5)
    assert C._to_fraction("20", "r") == Fraction(20)


def test_f7_identity_vector_survives_json_round_trip():
    vector = C.identity_vector(response_object())
    round_trip = json.loads(json.dumps(vector))
    assert vector == round_trip
    assert C.compare_identity(vector, round_trip) == []
    # tuple-form baselines (the reference representation) still compare equal
    tupled = {k: tuple(v) for k, v in vector.items()}
    assert C.compare_identity(vector, tupled) == []


def test_f7_real_changes_are_still_detected():
    base = C.identity_vector(response_object())
    changed = C.identity_vector(response_object(reasoning={"effort": "medium", "summary": "auto"}))
    assert C.compare_identity(changed, base) == ["identity_change:reasoning"]
    appeared = C.identity_vector(response_object(temperature=1.0))
    assert C.compare_identity(appeared, base) == ["identity_change:temperature"]
    vanished = json.loads(json.dumps(base))
    vanished["store"] = ["absent"]
    assert C.compare_identity(base, vanished) == ["identity_change:store"]


def test_f7_validate_identity_vector_rejects_malformed_tags():
    vector = C.identity_vector(response_object())
    for bad in (
        {**vector, "model": ["present"]},
        {**vector, "model": ["maybe"]},
        {**vector, "model": ["present", "{not json"]},
    ):
        with pytest.raises(C.ContractViolation):
            C.validate_identity_vector(bad)
    with pytest.raises(C.ContractViolation):
        C.validate_identity_vector({k: v for k, v in vector.items() if k != "model"})


# ------------------------------------------------------------- authority


def test_synthetic_authority_constructs_and_hashes_deterministically():
    a, b = synthetic_authority(), synthetic_authority()
    assert a.sha256() == b.sha256()
    assert a.profile_sha256 == profile_sha256("medium")
    assert AuthorityRecord.from_dict(a.as_dict()) == a


@pytest.mark.parametrize(
    "override",
    [
        {"profile_sha256": FAKE_HASH},
        {"model": "gpt-5.6"},
        {"reasoning_effort": "minimal"},
        {"input_token_ceiling": 272001},
        {"max_output_tokens": 8191},
        {"count_attempt_cap": 4561},
        {"generation_attempt_cap": 0},
        {"scope": "e9", "count_attempt_cap": 13},
        {"usd_ceiling": "0"},
        {"usd_ceiling": "1e3"},
        {"input_usd_per_million": "0"},
        {"billing_categories": ("input", "output")},
        {"rate_source_sha256": "abc"},
        {"price_valid_through_utc": "2026-09-08T00:00:00Z"},  # precedes recorded_at
        {"count_fee_valid_through_utc": "2026-09-08T00:00:00Z"},
        {"count_fee_verified": False},
        {"count_fee_covers_failed_and_rejected": False},
        {"count_fee_evidence_sha256": "unknown"},
        {"count_fee_evidence": ""},
        {"sdk_version": "3.8.0"},
        {"httpx_version": "2.12.0"},
        {"synthetic": "yes"},
        {"recorded_at_utc": "2026-09-09"},
    ],
)
def test_authority_fails_closed_on_missing_or_invalid_fact(override):
    with pytest.raises((ValueError, C.ContractViolation)):
        synthetic_authority(**override)


def test_price_validity_requires_finite_time_inside_both_intervals():
    a = synthetic_authority(count_fee_valid_through_utc="2026-10-01T00:00:00Z")
    start = datetime(2026, 9, 9, tzinfo=timezone.utc).timestamp()
    fee_end = datetime(2026, 10, 1, tzinfo=timezone.utc).timestamp()
    assert a.price_valid_at(start) and a.price_valid_at(fee_end)
    assert not a.price_valid_at(start - 1)  # before recorded_at
    assert not a.price_valid_at(fee_end + 1)  # count-fee evidence expired first
    for bad in (float("-inf"), float("inf"), float("nan"), True, None, "2026"):
        assert not a.price_valid_at(bad)


def test_authority_load_rejects_duplicate_keys_and_missing_fields(tmp_path):
    good = synthetic_authority().as_dict()
    path = tmp_path / "authority.json"
    path.write_bytes(json.dumps(good).encode())
    assert AuthorityRecord.load(path) == synthetic_authority()
    text = json.dumps(good)
    dup = text[:-1] + ', "usd_ceiling": "999999"}'
    path.write_bytes(dup.encode())
    with pytest.raises(ValueError):
        AuthorityRecord.load(path)
    del good["count_fee_evidence"]
    path.write_bytes(json.dumps(good).encode())
    with pytest.raises(ValueError):
        AuthorityRecord.load(path)


def test_frozen_record_mutation_is_detected_by_revalidation():
    a = synthetic_authority()
    object.__setattr__(a, "usd_ceiling", "1e9")
    with pytest.raises((ValueError, C.ContractViolation)):
        AuthorityRecord.from_dict(a.as_dict())


# ------------------------------------------------------------------ ledger


def rates():
    return synthetic_authority().rates()


def test_ledger_books_unknown_in_full_and_actual_when_reconciled(tmp_path):
    with DurableJournal(tmp_path / "j") as log:
        ledger = MoneyLedger(log, scope="study", ceiling=Fraction(10))
        k1 = ledger.reserve(
            request_class="generation",
            transport_reservation="t1",
            amount=Fraction(2),
            basis={},
            class_cap=10,
        )
        k2 = ledger.reserve(
            request_class="generation",
            transport_reservation="t2",
            amount=Fraction(2),
            basis={},
            class_cap=10,
        )
        assert ledger.state()["committed"] == 4
        ledger.settle(
            k1, outcome="retained_unknown", computed_charge=None, reconciled=False, findings=["x"]
        )
        ledger.settle(
            k2,
            outcome="settled_actual",
            computed_charge=Fraction(1, 2),
            reconciled=True,
            findings=[],
        )
        state = ledger.state()
        assert state["committed"] == Fraction(5, 2) and not state["halted"]
        assert state["unresolved_or_retained"] == 1


def test_ledger_r1_unreconciled_known_charge_above_reservation_is_an_overrun(tmp_path):
    """Review fix R1: contradictory total, but input/output categories price above the
    reservation. The ledger must book the KNOWN category charge, not the reservation."""
    with DurableJournal(tmp_path / "j") as log:
        ledger = MoneyLedger(log, scope="study", ceiling=Fraction(1))
        amount = C.reservation_for_generation(42, rates())  # 42*4e-6 + 8192*20e-6
        key = ledger.reserve(
            request_class="generation",
            transport_reservation="t1",
            amount=amount,
            basis={},
            class_cap=10,
        )
        usage = {
            "input_tokens": 42,
            "output_tokens": 20000,  # above the 8192 cap
            "total_tokens": 1,  # contradictory total => not reconciled
            "input_tokens_details": {"cached_tokens": 0, "cache_write_tokens": 0},
        }
        settlement = C.settle_response({"usage": usage}, 42, amount, rates(), policy="study")
        assert not settlement["reconciled"] and settlement["overrun"]
        ledger.settle(
            key,
            outcome="retained_unreconciled",
            computed_charge=settlement["charge"],
            reconciled=False,
            findings=settlement["findings"],
        )
        state = ledger.state()
        assert state["committed"] == settlement["charge"] > amount
        assert state["overrun_recorded"] and state["halted"]
        with pytest.raises(LedgerHalted):
            ledger.reserve(
                request_class="count",
                transport_reservation="t2",
                amount=Fraction(0),
                basis={},
                class_cap=10,
            )


def test_ledger_ceiling_and_class_caps_refuse_before_dispatch(tmp_path):
    with DurableJournal(tmp_path / "j") as log:
        ledger = MoneyLedger(log, scope="e9", ceiling=Fraction(1))
        ledger.reserve(
            request_class="count",
            transport_reservation="a",
            amount=Fraction(1, 2),
            basis={},
            class_cap=1,
        )
        with pytest.raises(LedgerHalted, match="count_attempt_cap_reached"):
            ledger.reserve(
                request_class="count",
                transport_reservation="b",
                amount=Fraction(0),
                basis={},
                class_cap=1,
            )
        with pytest.raises(LedgerHalted, match="monetary_ceiling_reached"):
            ledger.reserve(
                request_class="generation",
                transport_reservation="c",
                amount=Fraction(3, 4),
                basis={},
                class_cap=5,
            )
        with pytest.raises(LedgerHalted, match="duplicate_money_reservation"):
            ledger.reserve(
                request_class="count",
                transport_reservation="a",
                amount=Fraction(0),
                basis={},
                class_cap=5,
            )


def test_ledger_settlement_rules_are_strict(tmp_path):
    with DurableJournal(tmp_path / "j") as log:
        ledger = MoneyLedger(log, scope="study", ceiling=Fraction(10))
        key = ledger.reserve(
            request_class="generation",
            transport_reservation="t",
            amount=Fraction(2),
            basis={},
            class_cap=5,
        )
        with pytest.raises(C.ContractViolation):  # unreconciled cannot settle to actual
            ledger.settle(
                key,
                outcome="settled_actual",
                computed_charge=Fraction(1),
                reconciled=False,
                findings=[],
            )
        with pytest.raises(C.ContractViolation):  # overrun outcome must exceed the reservation
            ledger.settle(
                key,
                outcome="overrun_recorded",
                computed_charge=Fraction(1),
                reconciled=True,
                findings=[],
            )
        with pytest.raises(C.ContractViolation):  # a reconciled known charge may not be retained
            ledger.settle(
                key,
                outcome="retained_unknown",
                computed_charge=Fraction(1),
                reconciled=True,
                findings=[],
            )
        ledger.settle(
            key,
            outcome="overrun_recorded",
            computed_charge=Fraction(3),
            reconciled=True,
            findings=[],
        )
        assert ledger.state()["committed"] == 3 and ledger.state()["halted"]
        with pytest.raises(C.ContractViolation):  # no second settlement
            ledger.settle(
                key, outcome="retained_unknown", computed_charge=None, reconciled=False, findings=[]
            )


def test_fraction_text_grammar_is_bounded():
    assert fraction_from_text("3/4") == Fraction(3, 4)
    for bad in ("3/0", "1e5/1", "1/1/1", "x", "1" * 81 + "/1"):
        with pytest.raises(C.ContractViolation):
            fraction_from_text(bad)


# ------------------------------------------------------------------ F8


def test_f8_money_str_is_independent_of_hostile_ambient_decimal_context():
    from decimal import Inexact, Overflow, localcontext

    with localcontext() as ctx:
        ctx.prec, ctx.Emax, ctx.Emin = 2, 1, -1
        ctx.traps[Inexact] = True
        ctx.traps[Overflow] = True
        assert C.money_str(Fraction(123), 12) == "123.000000000000"
        assert C.money_str(Fraction(20501, 125000), 6) == "0.164008"
        assert C.money_str(Fraction(0), 12) == "0.000000000000"
        assert C.money_str(Fraction(-7, 4), 2) == "-1.75"
        assert C._to_fraction("1234567890.123456789", "x") == Fraction(1234567890123456789, 10**9)
        assert C.rates_per_million("4", "0.4", "5", "20")["output"] == Fraction(1, 50000)
    with pytest.raises(C.ContractViolation):
        C.money_str(Fraction(1, 3), 6)


def test_f8_decimal_inputs_are_bounded_by_coefficient_and_raw_exponent():
    from decimal import Decimal

    with pytest.raises(C.ContractViolation):
        C._to_fraction(Decimal("1." + "0" * 100 + "1"), "x")
    with pytest.raises(C.ContractViolation):
        C._to_fraction(Decimal("1E+41"), "x")
    with pytest.raises(C.ContractViolation):
        C._to_fraction(Decimal("1E-41"), "x")
    assert C._to_fraction(Decimal("0.4"), "x") == Fraction(2, 5)
    assert C._to_fraction(Decimal("4E+1"), "x") == Fraction(40)
    assert C._to_fraction(Decimal("-2.5"), "x") == Fraction(-5, 2)


def test_f7_list_tag_semantics_absent_present_null_and_whole_objects():
    """Operational replacement for the two reference assertions that required tuple tags
    (test_absent_optional_safe_fields_are_acceptable,
    test_identity_vector_is_presence_tagged_and_covers_whole_frozen_objects)."""
    payload = response_object(temperature=None)
    del payload["prompt_cache_options"]
    vector = C.identity_vector(payload)
    assert vector["tools"] == ["absent"]  # optional-safe field absent
    assert vector["background"] == ["absent"]
    assert vector["temperature"] == ["present", "null"]  # present with a null value
    assert vector["prompt_cache_options"] == ["absent"]
    assert vector["reasoning"] == ["present", '{"effort":"medium","summary":null}']  # whole object
    assert vector["text"] == ["present", '{"format":{"type":"text"},"verbosity":"medium"}']
    assert C.validate_expected_profile(payload, reasoning_effort="medium") == [
        "profile_echo_missing:prompt_cache_options.mode"
    ]
    assert C.validate_expected_profile(response_object(), reasoning_effort="medium") == []
    assert set(vector) == set(C.IDENTITY_KEYS)
    assert all(isinstance(v, list) for v in vector.values())
