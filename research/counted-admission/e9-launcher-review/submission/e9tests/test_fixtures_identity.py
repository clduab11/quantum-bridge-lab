"""Strict fixture identity. A committed byte may never be changed to fit a run."""

from __future__ import annotations

import json
import shutil

import pytest

from qbridge_e9.fixtures import FixtureError, load_fixture_set
from e9tests import support


def _copy(tmp_path):
    target = tmp_path / "e9-inputs"
    shutil.copytree(support.FIXTURES_DIR, target)
    return target


def test_committed_fixtures_verify_with_builder_and_source_hashes():
    fs = support.fixture_set()
    assert [f.name for f in fs.fixtures] == [
        "F1_short",
        "F2_maximal_renderer",
        "F3_repeat_of_F2",
        "F4_correction_no_valid_vectors",
    ]
    assert not fs.failed
    # eight payload hashes + eight byte lengths are individually recorded
    hashed = [c for c in fs.checks if c.requirement == "eight committed payload hashes bound"]
    assert len(hashed) == 8 and all(c.passed for c in hashed)
    assert any("build_e9_inputs.py" in c.detail for c in fs.checks)
    assert sum(c.requirement == "manifest source hashes bound" for c in fs.checks) == 5


def test_provider_prepare_reproduces_every_committed_byte(tmp_path):
    scripted, _ = support.nominal_handler(support.fixture_set())
    _j, provider, _r, _o, _c, fs = support.build(tmp_path, scripted)
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


def test_single_byte_edit_fails_the_hash_binding(tmp_path):
    target = _copy(tmp_path)
    path = target / "F1_short.generation.json"
    data = bytearray(path.read_bytes())
    data[-2:-1] = b" "  # whitespace edit: still parses, different bytes
    path.write_bytes(bytes(data))
    with pytest.raises(FixtureError, match="payload hashes bound"):
        load_fixture_set(target, reasoning_effort="medium")


def test_broken_f2_f3_repeat_is_rejected(tmp_path):
    target = _copy(tmp_path)
    manifest = json.loads((target / "manifest.json").read_text())
    f3 = next(e for e in manifest["fixtures"] if e["fixture"] == "F3_repeat_of_F2")
    src = target / "F1_short.generation.json"
    dst = target / f3["files"]["generation"]["path"]
    dst.write_bytes(src.read_bytes())
    f3["files"]["generation"]["sha256"] = support.hashlib.sha256(src.read_bytes()).hexdigest()
    f3["files"]["generation"]["bytes"] = len(src.read_bytes())
    support.write_json(target / "manifest.json", manifest)
    with pytest.raises(FixtureError):
        load_fixture_set(target, reasoning_effort="medium")


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
def test_profile_or_allowance_drift_in_manifest_is_rejected(tmp_path, field, value):
    target = _copy(tmp_path)
    manifest = json.loads((target / "manifest.json").read_text())
    manifest[field] = value
    support.write_json(target / "manifest.json", manifest)
    with pytest.raises(FixtureError):
        load_fixture_set(target, reasoning_effort=manifest["reasoning_effort"])


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
def test_prospective_state_claims_cannot_be_flipped(tmp_path, field, value):
    target = _copy(tmp_path)
    manifest = json.loads((target / "manifest.json").read_text())
    manifest[field] = value
    support.write_json(target / "manifest.json", manifest)
    with pytest.raises(FixtureError, match="prospective state preserved"):
        load_fixture_set(target, reasoning_effort="medium")


def test_effort_must_equal_the_manifest_fixed_value():
    with pytest.raises(FixtureError, match="reasoning effort"):
        load_fixture_set(support.FIXTURES_DIR, reasoning_effort="high")
