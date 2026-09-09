"""Live-gate regressions: missing, expired, forged and synthetic evidence.

The gate must refuse by default and must be satisfiable only by a complete,
consistent, non-synthetic evidence set. The satisfiable case is constructed
inside pytest's tmp_path so that no file here can be mistaken for real
evidence; each generated file carries a `_gate_self_check_fixture` marker.
"""

from __future__ import annotations

import json

import pytest

from counted_responses_provider.authority import HTTPX_VERSION, SDK_VERSION
from e9tests import support
from qbridge_e9.fixtures import sha256_hex
from qbridge_e9.gate import API_KEY_ENV, evaluate_gate
from qbridge_e9.limits import E9Limits

LIMITS = E9Limits()
NOW = support.WALL


def gate(**kw):
    kw.setdefault("mode", "live")
    kw.setdefault("limits", LIMITS)
    kw.setdefault("now_utc", NOW)
    kw.setdefault("env", {})
    return evaluate_gate(**kw)


def failed(result):
    return {r.key for r in result.failures}


# --- refusal by default -----------------------------------------------------


def test_empty_evidence_fails_every_requirement_except_the_installed_sdk():
    result = gate(authority=None)
    assert not result.may_dispatch_live
    assert "authority.present" in failed(result)
    passing = {r.key for r in result.requirements if r.passed}
    assert passing == {"environment.sdk_versions"}


def test_unresolved_requirements_are_failures_not_defaults():
    result = gate(authority=None)
    # No third status exists: an unresolved requirement cannot be "skipped".
    assert {r.status for r in result.requirements} == {"pass", "fail"}
    # Every failure states its reason; nothing fails silently or passes by default.
    assert all(r.detail.strip() for r in result.failures)
    assert len(result.failures) == len(result.requirements) - 1


def test_a_synthetic_authority_fails_the_live_gate():
    result = gate(authority=support.authority())
    assert "authority.not_synthetic" in failed(result)
    assert not result.may_dispatch_live


def test_dry_run_mode_never_permits_a_live_dispatch():
    result = evaluate_gate(
        mode="dry-run", authority=support.authority(synthetic=False), limits=LIMITS,
        now_utc=NOW, env={API_KEY_ENV: "x"},
    )
    assert result.may_dispatch_live is False


# --- specific evidence defects ---------------------------------------------


def test_expired_price_validity_fails():
    auth = support.authority(
        synthetic=False,
        price_valid_through_utc="2026-09-09T00:00:01Z",
        count_fee_valid_through_utc="2026-09-09T00:00:01Z",
    )
    assert "authority.price_validity" in failed(gate(authority=auth))


def test_marker_words_in_the_count_fee_evidence_fail():
    auth = support.authority(synthetic=False)
    assert "authority.count_fee" in failed(gate(authority=auth))


def test_a_proposed_amendment_cannot_satisfy_adoption(tmp_path):
    path = support.write_json(
        tmp_path / "adoption.json",
        {
            "amendment_adopted": False,
            "status": "PROPOSED",
            "amendment_file": "amendment_A1_counted_responses_admission_PROPOSED_2026-09-08.md",
            "operative_protocol_sha256": "0" * 64,
        },
    )
    result = gate(authority=support.authority(synthetic=False), adoption_evidence=path)
    assert "adoption.record" in failed(result)


def test_adoption_record_whose_protocol_hash_does_not_match_the_file_fails(tmp_path):
    spec = tmp_path / "protocol.md"
    spec.write_text("operative protocol bytes\n")
    path = support.write_json(
        tmp_path / "adoption.json",
        {
            "amendment_adopted": True,
            "status": "adopted",
            "amendment_file": "A1.md",
            "operative_protocol_sha256": "1" * 64,
        },
    )
    result = gate(
        authority=support.authority(synthetic=False),
        adoption_evidence=path,
        specification_path=spec,
    )
    assert "adoption.operative_protocol" in failed(result)


def test_billing_evidence_hash_must_match_the_authority(tmp_path):
    rates = tmp_path / "rates.md"
    rates.write_text("not the hashed source\n")
    path = support.write_json(
        tmp_path / "billing.json",
        {
            "_gate_self_check_fixture": True,
            "model_rates": {
                "retained_path": str(rates),
                "valid_through_utc": support.VALID_THROUGH,
            },
        },
    )
    result = gate(authority=support.authority(synthetic=False), billing_evidence=path)
    assert "billing.rate_source" in failed(result)


def test_unknown_account_terms_fail(tmp_path):
    path = support.write_json(
        tmp_path / "billing.json",
        {
            "_gate_self_check_fixture": True,
            "account_terms": {
                "billing_mode": "unknown",
                "usage_tier": None,
                "monthly_usage_limit_usd": "",
                "taxes": "unknown",
            },
        },
    )
    result = gate(authority=support.authority(synthetic=False), billing_evidence=path)
    assert "billing.account_terms" in failed(result)


def test_a_forged_authorization_amount_fails(tmp_path):
    path = support.write_json(
        tmp_path / "authorization.json",
        {
            "_gate_self_check_fixture": True,
            "approved": True,
            "scope": "e9",
            "approved_by": "owner",
            "approved_at_utc": support.RECORDED,
            "e9_usd_limit": "500",
        },
    )
    result = gate(
        authority=support.authority(synthetic=False, usd_ceiling="25"),
        authorization_record=path,
    )
    assert "authorization.explicit_e9" in failed(result)


def test_an_unapproved_authorization_template_fails(tmp_path):
    path = support.write_json(
        tmp_path / "authorization.json",
        {
            "approved": False,
            "status": "UNAPPROVED PROPOSAL",
            "scope": "e9",
            "approved_by": "",
            "approved_at_utc": "",
            "e9_usd_limit": "25",
        },
    )
    result = gate(
        authority=support.authority(synthetic=False), authorization_record=path
    )
    assert "authorization.explicit_e9" in failed(result)


def test_a_study_scope_authority_cannot_run_e9():
    auth = support.authority(
        synthetic=False, scope="study", count_attempt_cap=4560, generation_attempt_cap=4560
    )
    keys = failed(gate(authority=auth))
    assert "authority.scope" in keys and "authority.caps" in keys


def test_a_routing_alias_model_cannot_be_recorded():
    with pytest.raises(ValueError, match="no routing alias"):
        support.authority(model="gpt-daybreak-blue-latest")


def test_an_unverified_count_fee_cannot_even_be_constructed():
    with pytest.raises(ValueError, match="count_fee_verified"):
        support.authority(count_fee_verified=False)
    with pytest.raises(ValueError, match="failed and rejected"):
        support.authority(count_fee_covers_failed_and_rejected=False)


def test_credential_presence_is_recorded_without_the_value():
    result = gate(authority=None, env={API_KEY_ENV: "sk-NEVER-LOGGED-VALUE"})
    entry = next(r for r in result.requirements if r.key == "credential.present")
    assert entry.passed
    assert "sk-NEVER-LOGGED-VALUE" not in json.dumps(result.as_dict())


# --- the satisfiable case (proves the gate is not vacuous) -----------------


def _complete_evidence(tmp_path):
    rates = tmp_path / "rates.md"
    rates.write_text("gate self-check: stand-in for the retained rate page\n")
    fees = tmp_path / "count_fees.md"
    fees.write_text("gate self-check: stand-in for retained count-charge evidence\n")
    spec = tmp_path / "protocol_v0_5.md"
    spec.write_text("gate self-check: stand-in for the operative protocol\n")
    auth = support.authority(
        synthetic=False,
        authorized_by="account owner",
        purpose="bounded E9 model preflight",
        rate_source="retained rate page",
        rate_source_sha256=sha256_hex(rates.read_bytes()),
        count_fee_evidence="retained account charge statement",
        count_fee_evidence_sha256=sha256_hex(fees.read_bytes()),
    )
    adoption = support.write_json(
        tmp_path / "adoption.json",
        {
            "_gate_self_check_fixture": True,
            "amendment_adopted": True,
            "status": "adopted",
            "amendment_file": "A1.md",
            "operative_protocol_sha256": sha256_hex(spec.read_bytes()),
        },
    )
    billing = support.write_json(
        tmp_path / "billing.json",
        {
            "_gate_self_check_fixture": True,
            "model_rates": {
                "retained_path": str(rates),
                "valid_through_utc": support.VALID_THROUGH,
            },
            "count_request_charges": {
                "retained_path": str(fees),
                "valid_through_utc": support.VALID_THROUGH,
                "covers_failed_and_rejected": True,
            },
            "account_terms": {
                "billing_mode": "prepaid credits",
                "usage_tier": "1",
                "monthly_usage_limit_usd": "100",
                "taxes": "none applicable",
            },
        },
    )
    authorization = support.write_json(
        tmp_path / "authorization.json",
        {
            "_gate_self_check_fixture": True,
            "approved": True,
            "scope": "e9",
            "approved_by": "account owner",
            "approved_at_utc": support.RECORDED,
            "e9_usd_limit": auth.usd_ceiling,
        },
    )
    records = support.private_dir(tmp_path / "raw")
    return {
        "authority": auth,
        "adoption_evidence": adoption,
        "billing_evidence": billing,
        "authorization_record": authorization,
        "specification_path": spec,
        "records_dir": records,
        "env": {API_KEY_ENV: "sk-present-not-read"},
    }


def test_a_complete_consistent_non_synthetic_evidence_set_passes(tmp_path):
    result = gate(**_complete_evidence(tmp_path))
    assert result.may_dispatch_live, failed(result)
    assert len(result.requirements) == 18


@pytest.mark.parametrize(
    "drop",
    ["adoption_evidence", "billing_evidence", "authorization_record", "records_dir", "env"],
)
def test_removing_any_single_evidence_element_closes_the_gate(tmp_path, drop):
    evidence = _complete_evidence(tmp_path)
    evidence[drop] = {} if drop == "env" else None
    assert not gate(**evidence).may_dispatch_live


def test_authority_must_pin_the_installed_sdk_versions(tmp_path):
    evidence = _complete_evidence(tmp_path)
    assert (SDK_VERSION, HTTPX_VERSION) == (
        evidence["authority"].sdk_version,
        evidence["authority"].httpx_version,
    )
    result = gate(**evidence)
    entry = next(r for r in result.requirements if r.key == "environment.authority_pins")
    assert entry.passed


# --- the shipped unapproved template ---------------------------------------


def test_the_shipped_authority_template_cannot_be_constructed_or_dispatched():
    """deliverables/e9_unapproved_authority_template.json must be inert."""
    from pathlib import Path

    from counted_responses_provider.authority import AuthorityRecord

    path = Path(__file__).resolve().parents[1] / "deliverables" / (
        "e9_unapproved_authority_template.json"
    )
    template = json.loads(path.read_text())
    assert template["authority_record"]["synthetic"] is True
    assert template["authority_record"]["count_fee_verified"] is False
    assert template["authorization_record"]["approved"] is False
    assert template["adoption_evidence"]["amendment_adopted"] is False
    # It cannot even become an AuthorityRecord, so it cannot reach a transport.
    with pytest.raises(ValueError):
        AuthorityRecord.from_dict(template["authority_record"])
