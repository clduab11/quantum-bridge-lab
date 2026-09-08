"""All mappings and repositories in this module are temporary synthetic fixtures."""

import hashlib
import json
import os
import subprocess

import pytest

from qbridge.analysis import analyze_masked
from qbridge.custody import (
    GitManifestRef,
    create_private_mapping,
    seal_output,
    select_pair,
)


def git(repo, *args):
    return subprocess.check_output(["git", "-C", str(repo), *args], text=True).strip()


@pytest.fixture
def setup(tmp_path):
    repo = tmp_path / "public"
    repo.mkdir()
    git(repo, "init", "-q")
    git(repo, "config", "user.email", "synthetic@example.invalid")
    git(repo, "config", "user.name", "Synthetic fixture")
    private = tmp_path / "private"
    private.mkdir(mode=0o700)
    mapping = private / "mapping.json"
    commitment = create_private_mapping(mapping, public_repo=repo)
    data = [
        {"label": label, "block": block, "y": y}
        for block in range(40)
        for label, y in (("A", -3.0), ("B", -2.0), ("C", -1.0))
    ]
    output = tmp_path / "output.json"
    sealed_hash = seal_output(analyze_masked(data), output)
    manifest = {"mapping_sha256": commitment, "sealed_output_sha256": sealed_hash}
    (repo / "manifest.json").write_text(json.dumps(manifest))
    git(repo, "add", "manifest.json")
    git(repo, "commit", "-qm", "synthetic seal")
    ref = GitManifestRef(repo, git(repo, "rev-parse", "HEAD"), "manifest.json")
    return repo, mapping, output, ref, tmp_path / "unmasking.json"


def test_nonce_commitment_permissions_and_exclusive_creation(setup):
    repo, mapping, _, _, _ = setup
    payload = json.loads(mapping.read_text())
    assert len(bytes.fromhex(payload["nonce"])) == 32
    assert len(bytes.fromhex(payload["permutation_seed"])) == 32
    assert set(payload["mapping"]) == {"AI", "CMA", "RS"}
    assert set(payload["mapping"].values()) == {"A", "B", "C"}
    assert mapping.stat().st_mode & 0o777 == 0o600
    with pytest.raises(FileExistsError):
        create_private_mapping(mapping, public_repo=repo)
    with pytest.raises(ValueError):
        create_private_mapping(repo / "private.json", public_repo=repo)


def test_mapping_parent_must_be_protected(tmp_path):
    os.chmod(tmp_path, 0o755)
    with pytest.raises(ValueError):
        create_private_mapping(
            tmp_path / "mapping.json", public_repo=tmp_path / "public"
        )


def test_canonical_seal_is_hash_of_exact_output_and_never_overwrites(setup, tmp_path):
    _, _, output, _, _ = setup
    second = tmp_path / "second.json"
    digest = seal_output(json.loads(output.read_text()), second)
    assert output.read_bytes() == second.read_bytes()
    assert digest == hashlib.sha256(output.read_bytes()).hexdigest()
    with pytest.raises(FileExistsError):
        seal_output({}, output)


def test_verified_selection_records_sequence_and_limits(setup):
    repo, mapping, output, ref, event_path = setup
    # Dirty worktree contents must not substitute for the committed manifest.
    (repo / "manifest.json").write_text("{}")
    result = select_pair(ref, output, mapping, event_path, actor="synthetic custodian")
    private = json.loads(mapping.read_text())["mapping"]
    pair = f"{private['AI']}-{private['CMA']}"
    assert result["pair"] == pair
    assert set(result["stages"]) == {"1", "2"}
    event = json.loads(event_path.read_text())
    assert event["pair"] == pair
    assert event["manifest_commit"] == ref.commit
    assert event["actor"] == "synthetic custodian"
    assert (
        event["sealed_output_sha256"] == hashlib.sha256(output.read_bytes()).hexdigest()
    )
    assert "not independent blinding" in event["custody_limit"]


@pytest.mark.parametrize(
    "mutation",
    ["missing_output", "wrong_output", "wrong_mapping", "permissions", "mutable_ref"],
)
def test_selection_refuses_invalid_seal_or_custody(setup, mutation):
    repo, mapping, output, ref, event = setup
    if mutation == "missing_output":
        output.unlink()
    elif mutation == "wrong_output":
        output.write_text("{}")
    elif mutation == "wrong_mapping":
        mapping.write_text("{}")
    elif mutation == "permissions":
        os.chmod(mapping, 0o644)
    else:
        ref = GitManifestRef(repo, "HEAD", "manifest.json")
    with pytest.raises((ValueError, FileNotFoundError)):
        select_pair(ref, output, mapping, event, actor="synthetic custodian")
    assert not event.exists()


def test_missing_committed_seal_rejected_before_mapping_access(setup):
    repo, mapping, output, _, event = setup
    (repo / "manifest.json").write_text("{}")
    git(repo, "add", "manifest.json")
    git(repo, "commit", "-qm", "synthetic missing seal")
    mapping.unlink()
    ref = GitManifestRef(repo, git(repo, "rev-parse", "HEAD"), "manifest.json")
    with pytest.raises(ValueError, match="manifest"):
        select_pair(ref, output, mapping, event, actor="synthetic custodian")


def test_fresh_nonce_changes_commitment_even_if_permutation_repeats(setup, monkeypatch):
    repo, mapping, _, _, _ = setup
    monkeypatch.setattr(
        "qbridge.custody.random.Random.shuffle", lambda self, values: None
    )
    first = create_private_mapping(mapping.parent / "one.json", public_repo=repo)
    second = create_private_mapping(mapping.parent / "two.json", public_repo=repo)
    one = json.loads((mapping.parent / "one.json").read_text())
    two = json.loads((mapping.parent / "two.json").read_text())
    assert one["mapping"] == two["mapping"]
    assert one["nonce"] != two["nonce"]
    assert first != second


def test_invalid_output_rejected_before_mapping_consultation(setup):
    repo, mapping, output, _, event = setup
    output.write_text("{}")
    manifest = {
        "mapping_sha256": "0" * 64,
        "sealed_output_sha256": hashlib.sha256(output.read_bytes()).hexdigest(),
    }
    (repo / "manifest.json").write_text(json.dumps(manifest))
    git(repo, "add", "manifest.json")
    git(repo, "commit", "-qm", "synthetic invalid output")
    mapping.unlink()
    ref = GitManifestRef(repo, git(repo, "rev-parse", "HEAD"), "manifest.json")
    with pytest.raises(ValueError, match="complete locked"):
        select_pair(ref, output, mapping, event, actor="synthetic custodian")


def test_empty_pair_summary_is_not_a_complete_seal(setup):
    repo, mapping, output, _, event = setup
    payload = json.loads(output.read_text())
    payload["stages"]["1"]["pairs"]["A-B"] = {}
    output.write_text(json.dumps(payload))
    manifest = {
        "mapping_sha256": "0" * 64,
        "sealed_output_sha256": hashlib.sha256(output.read_bytes()).hexdigest(),
    }
    (repo / "manifest.json").write_text(json.dumps(manifest))
    git(repo, "add", "manifest.json")
    git(repo, "commit", "-qm", "synthetic incomplete summary")
    mapping.unlink()
    ref = GitManifestRef(repo, git(repo, "rev-parse", "HEAD"), "manifest.json")
    with pytest.raises(ValueError, match="complete locked"):
        select_pair(ref, output, mapping, event, actor="synthetic custodian")
