"""Live-gate regressions: missing, expired, forged and synthetic evidence.

The gate must refuse by default and must be satisfiable only by a complete,
consistent, non-synthetic evidence set. The satisfiable case is constructed
inside pytest's tmp_path so that no file here can be mistaken for real
evidence; each generated file carries a `_gate_self_check_fixture` marker.
"""

from __future__ import annotations

import json
from pathlib import Path

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
    tmp_path = Path(tmp_path)
    tmp_path.mkdir(parents=True, exist_ok=True)
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
                "existing_month_to_date_spend_usd": "0",
                "concurrent_project_traffic": "none",
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
            "expires_at_utc": support.VALID_THROUGH,
            "authority_sha256": auth.sha256(),
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
    assert len(result.requirements) == 20


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
        "e9_unapproved_authority_template_rev2.json"
    )
    template = json.loads(path.read_text())
    assert template["authority_record"]["synthetic"] is True
    assert template["authority_record"]["count_fee_verified"] is False
    assert template["authorization_record"]["approved"] is False
    assert template["authorization_record"]["authority_sha256"] == "0" * 64
    assert template["adoption_evidence"]["amendment_adopted"] is False
    for key in ("existing_month_to_date_spend_usd", "concurrent_project_traffic"):
        assert template["billing_evidence"]["account_terms"][key] == "unknown"
    # It cannot even become an AuthorityRecord, so it cannot reach a transport.
    with pytest.raises(ValueError):
        AuthorityRecord.from_dict(template["authority_record"])


# --- review finding 3: real Git worktree detection ------------------------


def test_a_records_dir_inside_a_real_git_repository_fails_the_gate(tmp_path):
    """Codex's reproduction: `git init` a directory, put the records store
    inside it, and the old check (looking for a parent literally named
    '.git') let it pass."""
    import subprocess

    from qbridge_e9.gate import git_worktree_root

    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q", str(repo)], check=True, timeout=60)
    records = support.private_dir(repo / "out" / "raw")
    assert git_worktree_root(records) == repo

    evidence = _complete_evidence(tmp_path / "evidence")
    evidence["records_dir"] = records
    result = gate(**evidence)
    assert not result.may_dispatch_live
    assert "records.private" in failed(result)
    detail = next(r.detail for r in result.requirements if r.key == "records.private")
    assert str(repo) in detail


def test_a_linked_worktree_marker_file_is_detected(tmp_path):
    """Linked worktrees and submodules use a .git FILE, not a directory."""
    from qbridge_e9.gate import git_worktree_root

    fake = tmp_path / "linked"
    fake.mkdir()
    (fake / ".git").write_text("gitdir: /elsewhere/.git/worktrees/linked\n")
    records = support.private_dir(fake / "raw")
    assert git_worktree_root(records) == fake


def test_a_symlink_into_a_repository_is_detected(tmp_path):
    import subprocess

    from qbridge_e9.gate import git_worktree_root

    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q", str(repo)], check=True, timeout=60)
    real = support.private_dir(repo / "raw")
    link = tmp_path / "looks-outside"
    link.symlink_to(real, target_is_directory=True)
    assert git_worktree_root(link) == repo


def test_a_records_dir_under_the_verified_repo_root_fails_even_without_git(tmp_path):
    evidence = _complete_evidence(tmp_path / "evidence")
    inside = support.private_dir(tmp_path / "checkout" / "raw")
    evidence["records_dir"] = inside
    evidence["repo_root"] = tmp_path / "checkout"
    result = gate(**evidence)
    assert "records.private" in failed(result)
    assert "under_verified_repo_root=True" in next(
        r.detail for r in result.requirements if r.key == "records.private"
    )


def test_a_private_dir_outside_any_repository_passes(tmp_path):
    from qbridge_e9.gate import git_worktree_root

    records = support.private_dir(tmp_path / "raw")
    assert git_worktree_root(records) is None
    evidence = _complete_evidence(tmp_path / "evidence")
    evidence["records_dir"] = records
    assert gate(**evidence).may_dispatch_live


# --- review finding 6: the approval must be timed and bound ---------------


@pytest.mark.parametrize(
    "value",
    ["invalid UTC, not an instant", "2026-13-45T99:99:99Z", "2026-09-09", "", "yes", "0"],
)
def test_a_non_instant_approval_time_closes_the_gate(tmp_path, value):
    evidence = _complete_evidence(tmp_path)
    path = Path(evidence["authorization_record"])
    record = json.loads(path.read_text())
    record["approved_at_utc"] = value
    support.write_json(path, record)
    result = gate(**evidence)
    assert not result.may_dispatch_live
    assert "authorization.bound_and_timed" in failed(result)


def test_an_approval_dated_in_the_future_closes_the_gate(tmp_path):
    evidence = _complete_evidence(tmp_path)
    path = Path(evidence["authorization_record"])
    record = json.loads(path.read_text())
    record["approved_at_utc"] = "2030-01-01T00:00:00Z"
    support.write_json(path, record)
    assert "authorization.bound_and_timed" in failed(gate(**evidence))


def test_an_expired_approval_closes_the_gate(tmp_path):
    evidence = _complete_evidence(tmp_path)
    path = Path(evidence["authorization_record"])
    record = json.loads(path.read_text())
    record["expires_at_utc"] = "2026-09-01T00:00:00Z"  # before NOW
    support.write_json(path, record)
    assert "authorization.bound_and_timed" in failed(gate(**evidence))


def test_an_approval_for_a_different_authority_closes_the_gate(tmp_path):
    """An approval must be bound to the authority record it authorizes."""
    evidence = _complete_evidence(tmp_path)
    path = Path(evidence["authorization_record"])
    record = json.loads(path.read_text())
    record["authority_sha256"] = "f" * 64
    support.write_json(path, record)
    result = gate(**evidence)
    assert "authorization.bound_and_timed" in failed(result)
    assert "bound=False" in next(
        r.detail for r in result.requirements if r.key == "authorization.bound_and_timed"
    )


def test_an_unbound_approval_closes_the_gate(tmp_path):
    evidence = _complete_evidence(tmp_path)
    path = Path(evidence["authorization_record"])
    record = json.loads(path.read_text())
    record.pop("authority_sha256")
    support.write_json(path, record)
    assert "authorization.bound_and_timed" in failed(gate(**evidence))


def test_an_adoption_record_dated_in_the_future_closes_the_gate(tmp_path):
    evidence = _complete_evidence(tmp_path)
    path = Path(evidence["adoption_evidence"])
    record = json.loads(path.read_text())
    record["adopted_at_utc"] = "2030-01-01T00:00:00Z"
    support.write_json(path, record)
    assert "adoption.record" in failed(gate(**evidence))


def test_unrecorded_account_terms_close_the_gate(tmp_path):
    """Review finding 9: a monthly project limit depends on month-to-date
    spend and concurrent project traffic, so both must be recorded."""
    for missing in ("existing_month_to_date_spend_usd", "concurrent_project_traffic"):
        evidence = _complete_evidence(tmp_path / missing)
        path = Path(evidence["billing_evidence"])
        record = json.loads(path.read_text())
        record["account_terms"][missing] = "unknown"
        support.write_json(path, record)
        result = gate(**evidence)
        assert "billing.account_terms" in failed(result), missing


# --- review finding 5: the ceiling must cover the conservative worst case --


def test_a_ceiling_that_cannot_fund_the_allowed_attempts_closes_the_gate(tmp_path):
    from qbridge_e9.money import conservative_e9_ceiling

    evidence = _complete_evidence(tmp_path)
    needed = conservative_e9_ceiling(evidence["authority"], LIMITS)
    assert float(needed) > 25, "the reproduction depends on 25 USD being short"
    evidence["authority"] = support.authority(
        synthetic=False,
        authorized_by="account owner",
        purpose="bounded E9 model preflight",
        rate_source=evidence["authority"].rate_source,
        rate_source_sha256=evidence["authority"].rate_source_sha256,
        count_fee_evidence=evidence["authority"].count_fee_evidence,
        count_fee_evidence_sha256=evidence["authority"].count_fee_evidence_sha256,
        usd_ceiling="25",
    )
    result = gate(**evidence)
    assert "authority.conservative_ceiling" in failed(result)
    detail = next(
        r.detail for r in result.requirements if r.key == "authority.conservative_ceiling"
    )
    assert "conservative requirement" in detail
