"""Strict fixture identity. A committed byte may never be changed to fit a run.

Review finding 4 (fixed). The reviewed digests are pinned in
``qbridge_e9.fixtures``, so the caller-supplied manifest can only confirm what
was reviewed. Codex's reproduction - change a committed prompt, update its
declared digest, and watch 76 checks pass - is the first test below.

Because the pin now rejects ANY manifest edit, the per-field profile and
prospective-state checks are no longer reachable by editing the manifest. They
are still real requirements, so they are tested as an independent second line
of defence by re-pinning the module constant to the mutated digest. That
isolates each check instead of letting the pin mask it.
"""

from __future__ import annotations

import hashlib
import json
import shutil

import pytest

from e9tests import support
from qbridge_e9 import fixtures as fixtures_module
from qbridge_e9.fixtures import (
    REVIEWED_MANIFEST_SHA256,
    REVIEWED_PAYLOAD_SHA256,
    REVIEWED_SOURCE_SHA256,
    FixtureError,
    load_fixture_set,
    sha256_hex,
)


def _copy(tmp_path):
    target = tmp_path / "e9-inputs"
    shutil.copytree(support.FIXTURES_DIR, target)
    return target


def _load(target, **kw):
    kw.setdefault("reasoning_effort", "medium")
    kw.setdefault("repo_root", support.REPO_ROOT)
    return load_fixture_set(target, **kw)


def _repin(monkeypatch, target):
    """Re-pin the module constant to the mutated manifest's digest.

    Only for isolating the checks that sit BEHIND the pin. It does not weaken
    any shipped requirement: the pinned constant in the module is unchanged.
    """
    digest = sha256_hex((target / "manifest.json").read_bytes())
    monkeypatch.setattr(fixtures_module, "REVIEWED_MANIFEST_SHA256", digest)
    return digest


# --- the pinned reviewed digests ------------------------------------------


def test_committed_fixtures_verify_against_the_pinned_reviewed_digests():
    fs = support.fixture_set()
    assert [f.name for f in fs.fixtures] == list(fixtures_module.REVIEWED_FIXTURE_ORDER)
    assert not fs.failed
    assert fs.manifest_sha256 == REVIEWED_MANIFEST_SHA256
    assert fs.as_dict()["manifest_matches_reviewed_pin"] is True
    pinned = [c for c in fs.checks if c.requirement == "pinned reviewed payload digests"]
    assert len(pinned) == len(REVIEWED_PAYLOAD_SHA256) == 8
    assert all(c.passed for c in pinned)
    assert sum(
        c.requirement == "reviewed source files verified at repo_root" for c in fs.checks
    ) == len(REVIEWED_SOURCE_SHA256) == 5
    assert any("build_e9_inputs.py" in c.detail for c in fs.checks)


def test_a_self_consistent_replacement_fixture_is_refused(tmp_path):
    """Codex's reproduction: change the committed F1 prompt AND its declared
    digests so the manifest is internally consistent."""
    from counted_responses_provider import contract as C

    target = _copy(tmp_path)
    manifest = json.loads((target / "manifest.json").read_text())
    entry = manifest["fixtures"][0]
    text = "Review probe changed this committed F1 user prompt."
    for cls in ("count", "generation"):
        spec = entry["files"][cls]
        path = target / spec["path"]
        body = json.loads(path.read_bytes())
        body["input"][1]["content"] = text
        data = C.canonical_bytes(body)
        path.write_bytes(data)
        spec["sha256"] = sha256_hex(data)
        spec["bytes"] = len(data)
    entry["user_sha256"] = sha256_hex(text.encode("ascii"))
    entry["user_bytes"] = len(text)
    entry["combined_text_bytes"] = entry["system_bytes"] + len(text)
    (target / "manifest.json").write_text(json.dumps(manifest))

    with pytest.raises(FixtureError, match="pinned reviewed manifest digest"):
        _load(target)


def test_the_payload_pin_holds_even_if_the_manifest_pin_is_defeated(tmp_path, monkeypatch):
    """Second line of defence: the eight payload digests are checked directly."""
    from counted_responses_provider import contract as C

    target = _copy(tmp_path)
    manifest = json.loads((target / "manifest.json").read_text())
    spec = manifest["fixtures"][0]["files"]["generation"]
    path = target / spec["path"]
    body = json.loads(path.read_bytes())
    body["input"][1]["content"] = "a different committed prompt"
    data = C.canonical_bytes(body)
    path.write_bytes(data)
    spec["sha256"], spec["bytes"] = sha256_hex(data), len(data)
    (target / "manifest.json").write_text(json.dumps(manifest))
    _repin(monkeypatch, target)

    with pytest.raises(FixtureError, match="pinned reviewed payload digests"):
        _load(target)


def test_an_empty_reviewed_source_set_is_refused(tmp_path, monkeypatch):
    target = _copy(tmp_path)
    manifest = json.loads((target / "manifest.json").read_text())
    manifest["source_sha256"] = {}
    (target / "manifest.json").write_text(json.dumps(manifest))
    _repin(monkeypatch, target)
    with pytest.raises(FixtureError, match="complete reviewed source set declared"):
        _load(target)


def test_a_partial_reviewed_source_set_is_refused(tmp_path, monkeypatch):
    target = _copy(tmp_path)
    manifest = json.loads((target / "manifest.json").read_text())
    manifest["source_sha256"].pop("src/qbridge/proposals.py")
    (target / "manifest.json").write_text(json.dumps(manifest))
    _repin(monkeypatch, target)
    with pytest.raises(FixtureError, match="complete reviewed source set declared"):
        _load(target)


def test_source_verification_is_not_optional():
    with pytest.raises(FixtureError, match="repo_root is required"):
        load_fixture_set(support.FIXTURES_DIR, reasoning_effort="medium", repo_root=None)


def test_a_wrong_repo_root_fails_source_verification(tmp_path):
    with pytest.raises(FixtureError):
        load_fixture_set(
            support.FIXTURES_DIR, reasoning_effort="medium", repo_root=tmp_path
        )


def test_an_extra_unreviewed_payload_file_is_refused(tmp_path, monkeypatch):
    target = _copy(tmp_path)
    (target / "F5_extra.generation.json").write_bytes(b"{}")
    _repin(monkeypatch, target)
    with pytest.raises(FixtureError, match="no unreviewed payload files present"):
        _load(target)


# --- properties of the committed set --------------------------------------


def test_provider_prepare_reproduces_every_committed_byte(tmp_path):
    scripted, _ = support.nominal_handler(support.fixture_set())
    _j, _provider, _r, _o, _c, fs = support.build(tmp_path, scripted)
    reproduced = [
        c for c in fs.checks if c.requirement == "provider.prepare reproduces the committed bytes"
    ]
    assert len(reproduced) == 8 and all(c.passed for c in reproduced)


def test_f2_and_f3_are_byte_identical():
    fs = support.fixture_set()
    f2, f3 = fs.by_name("F2_maximal_renderer"), fs.by_name("F3_repeat_of_F2")
    assert f2.count_bytes == f3.count_bytes
    assert f2.generation_bytes == f3.generation_bytes
    assert f2.count_sha256 == f3.count_sha256


def test_single_byte_edit_fails_the_payload_pin(tmp_path):
    target = _copy(tmp_path)
    path = target / "F1_short.generation.json"
    data = bytearray(path.read_bytes())
    data[-2:-1] = b" "  # whitespace edit: still parses, different bytes
    path.write_bytes(bytes(data))
    with pytest.raises(FixtureError, match="pinned reviewed payload digests"):
        _load(target)


def test_broken_f2_f3_repeat_is_rejected(tmp_path, monkeypatch):
    target = _copy(tmp_path)
    manifest = json.loads((target / "manifest.json").read_text())
    f3 = next(e for e in manifest["fixtures"] if e["fixture"] == "F3_repeat_of_F2")
    src = target / "F1_short.generation.json"
    dst = target / f3["files"]["generation"]["path"]
    dst.write_bytes(src.read_bytes())
    f3["files"]["generation"]["sha256"] = hashlib.sha256(src.read_bytes()).hexdigest()
    f3["files"]["generation"]["bytes"] = len(src.read_bytes())
    support.write_json(target / "manifest.json", manifest)
    _repin(monkeypatch, target)
    with pytest.raises(FixtureError):
        _load(target)


@pytest.mark.parametrize(
    "field,value",
    [
        ("admission_limit", 200000),
        ("max_output_tokens", 4096),
        ("model", "gpt-daybreak-blue-latest"),
        ("reasoning_effort", "high"),
        ("max_count_attempts", 24),
        ("deadline_seconds", 36000),
    ],
)
def test_profile_or_allowance_drift_in_manifest_is_rejected(tmp_path, monkeypatch, field, value):
    target = _copy(tmp_path)
    manifest = json.loads((target / "manifest.json").read_text())
    manifest[field] = value
    support.write_json(target / "manifest.json", manifest)
    _repin(monkeypatch, target)
    with pytest.raises(FixtureError):
        _load(target, reasoning_effort=manifest["reasoning_effort"])


@pytest.mark.parametrize(
    "field,value",
    [
        ("execution_authorized", True),
        ("protocol_adopted", True),
        ("count_fee_verified", True),
        ("counted_input_tokens", 100),
        ("provider_generation_calls", 1),
        ("study_objective_candidate_evaluations", 1),
    ],
)
def test_prospective_state_claims_cannot_be_flipped(tmp_path, monkeypatch, field, value):
    target = _copy(tmp_path)
    manifest = json.loads((target / "manifest.json").read_text())
    manifest[field] = value
    support.write_json(target / "manifest.json", manifest)
    _repin(monkeypatch, target)
    with pytest.raises(FixtureError, match="prospective state preserved"):
        _load(target)


def test_effort_must_equal_the_manifest_fixed_value():
    with pytest.raises(FixtureError, match="reasoning effort"):
        load_fixture_set(
            support.FIXTURES_DIR, reasoning_effort="high", repo_root=support.REPO_ROOT
        )
