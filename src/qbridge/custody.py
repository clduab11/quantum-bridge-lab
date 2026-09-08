"""Auditable automated custody sequencing; not independent evaluator blinding.

The private file contains a permutation seed, mapping and fresh 256-bit nonce.
It must remain outside public Git. SHA-256 commits its entire canonical bytes.
Selection reads a manifest from an immutable full Git commit, never HEAD or the
worktree. Minimal manifest fields are mapping_sha256 and sealed_output_sha256;
additional study-manifest fields are allowed. The operator must first commit
these public hashes. This module neither freezes nor runs a real study.

Anyone with filesystem access may still read the private mapping early. File
permissions are a protection against other accounts, not proof of blindness or
proof that the process owner did not inspect the mapping.
"""

import hashlib
import json
import os
import random
import re
import secrets
import stat
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath

from qbridge.analysis import LABELS, PAIRS, summarize_stage


@dataclass(frozen=True)
class GitManifestRef:
    repo: Path
    commit: str
    path: str


def _canonical(value):
    return (
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON object key")
        result[key] = value
    return result


def read_json_bytes(data):
    """Strict JSON for command-line records, manifests and custody artifacts."""

    def reject_constant(value):
        raise ValueError(f"nonfinite JSON constant: {value}")

    return json.loads(data, object_pairs_hook=_unique_object, parse_constant=reject_constant)


def _digest(data):
    return hashlib.sha256(data).hexdigest()


def _write_exclusive(path, data):
    path = Path(path)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, "wb") as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())
    parent_fd = os.open(path.parent, os.O_RDONLY)
    try:
        os.fsync(parent_fd)
    finally:
        os.close(parent_fd)


def _protected_parent(path):
    info = Path(path).parent.stat()
    if info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) & 0o077:
        raise ValueError("private mapping parent must be owner-only (0700)")


def create_private_mapping(path, *, public_repo):
    """Create one protected mapping; never overwrite or place it in public repo.

    Call only within a separately authorized custody setup. Tests use temporary
    synthetic repositories and never establish a real-study mapping.
    """
    path = Path(path)
    if path.resolve().is_relative_to(Path(public_repo).resolve()):
        raise ValueError("mapping must be outside the public repository")
    _protected_parent(path)
    seed = secrets.token_hex(32)
    labels = list(LABELS)
    random.Random(int(seed, 16)).shuffle(labels)
    payload = {
        "schema": "qbridge.private-mapping.v1",
        "nonce": secrets.token_hex(32),
        "permutation_seed": seed,
        "mapping": dict(zip(("AI", "CMA", "RS"), labels)),
    }
    data = _canonical(payload)
    _write_exclusive(path, data)
    return _digest(data)


def seal_output(output, path):
    """Write canonical bytes once and return the hash to commit in the manifest.

    Writing a file is not the committed seal: selection additionally requires
    this hash to exist in the immutable Git manifest reference.
    """
    data = _canonical(output)
    _write_exclusive(path, data)
    return _digest(data)


def _committed_manifest(ref):
    if not re.fullmatch(r"[0-9a-f]{40}|[0-9a-f]{64}", ref.commit):
        raise ValueError("manifest reference requires a full immutable Git commit hash")
    path = PurePosixPath(ref.path)
    if path.is_absolute() or ".." in path.parts or not path.parts:
        raise ValueError("manifest requires a repository-relative path")
    command = ["git", "--no-replace-objects", "-C", str(ref.repo)]
    try:
        resolved = (
            subprocess.check_output(
                command + ["rev-parse", "--verify", ref.commit + "^{commit}"],
                stderr=subprocess.DEVNULL,
            )
            .decode()
            .strip()
        )
        if resolved != ref.commit:
            raise ValueError("manifest reference must identify the commit itself")
        data = subprocess.check_output(
            command + ["show", f"{ref.commit}:{path}"], stderr=subprocess.DEVNULL
        )
    except subprocess.CalledProcessError as exc:
        raise ValueError("committed manifest unavailable") from exc
    manifest = read_json_bytes(data)
    if not isinstance(manifest, dict) or any(
        not isinstance(manifest.get(key), str) or not re.fullmatch(r"[0-9a-f]{64}", manifest[key])
        for key in ("mapping_sha256", "sealed_output_sha256")
    ):
        raise ValueError("committed manifest requires mapping and sealed-output SHA-256")
    return manifest


def _private_bytes(path, repo):
    path = Path(path)
    if path.resolve().is_relative_to(Path(repo).resolve()):
        raise ValueError("mapping must be outside the public repository")
    _protected_parent(path)
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    with os.fdopen(fd, "rb") as stream:
        info = os.fstat(stream.fileno())
        if (
            not stat.S_ISREG(info.st_mode)
            or info.st_uid != os.getuid()
            or stat.S_IMODE(info.st_mode) != 0o600
        ):
            raise ValueError("mapping requires an owner-owned regular file with mode 0600")
        return stream.read()


def select_pair(ref, output_path, mapping_path, event_path, *, actor):
    """Verify the committed output seal *before* opening the private mapping.

    Persist an exclusive unmasking event, then return the precommitted pair.
    The event records UTC time, responsible actor, immutable manifest reference
    and sealed-output hash. It does not disclose the nonce or complete mapping.
    """
    if not isinstance(actor, str) or not actor.strip():
        raise ValueError("an actual custody actor must be recorded")
    manifest = _committed_manifest(ref)
    data = Path(output_path).read_bytes()
    if _digest(data) != manifest["sealed_output_sha256"]:
        raise ValueError("output does not match the committed seal")
    output = read_json_bytes(data)
    expected_pairs = {f"{left}-{right}" for left, right in PAIRS}
    try:
        validity = output["validity"]
        invalid = validity["invalid_for_confirmation"]
        valid = (
            output["schema"] == "qbridge.locked-analysis.v1"
            and type(invalid) is bool
            and type(validity["svf"]) is bool
            and type(validity["ivf"]) is bool
            and isinstance(validity["missing_endpoints"], list)
            and invalid
            == (validity["svf"] or validity["ivf"] or bool(validity["missing_endpoints"]))
            and set(output["stages"]) == {"1", "2"}
            and set(output["pair_decisions"]) == expected_pairs
            and all(set(output["stages"][stage]["pairs"]) == expected_pairs for stage in ("1", "2"))
        )
        if valid:
            for stage, start in (("1", 0), ("2", 20)):
                valid = valid and output["stages"][stage]["blocks"] == list(
                    range(start, start + 20)
                )
                for pair in expected_pairs:
                    summary = output["stages"][stage]["pairs"][pair]
                    valid = valid and summary == summarize_stage(
                        summary["differences"], invalid=invalid
                    )
            for pair in expected_pairs:
                first, second = (
                    output["stages"][s]["pairs"][pair]["nominal_category"] for s in ("1", "2")
                )
                expected = (
                    "invalid"
                    if invalid
                    else (
                        "replicated_support"
                        if first == second == "supports"
                        else (
                            "replicated_exclusion"
                            if first == second == "excludes"
                            else f"stage_1_{first};stage_2_{second}"
                        )
                    )
                )
                valid = valid and output["pair_decisions"][pair] == expected
    except (KeyError, TypeError, ValueError):
        valid = False
    if not valid:
        raise ValueError("sealed output must contain the complete locked all-pairs summary")
    private_data = _private_bytes(mapping_path, ref.repo)
    if _digest(private_data) != manifest["mapping_sha256"]:
        raise ValueError("mapping does not match the committed mapping hash")
    private = read_json_bytes(private_data)
    try:
        mapping = private["mapping"]
        valid = (
            private["schema"] == "qbridge.private-mapping.v1"
            and set(mapping) == {"AI", "CMA", "RS"}
            and set(mapping.values()) == set(LABELS)
            and re.fullmatch(r"[0-9a-f]{64}", private["nonce"])
            and re.fullmatch(r"[0-9a-f]{64}", private["permutation_seed"])
        )
        labels = list(LABELS)
        random.Random(int(private["permutation_seed"], 16)).shuffle(labels)
        valid = valid and mapping == dict(zip(("AI", "CMA", "RS"), labels))
    except (KeyError, TypeError, ValueError):
        valid = False
    if not valid:
        raise ValueError("invalid private mapping payload")
    pair = f"{mapping['AI']}-{mapping['CMA']}"
    event = {
        "event": "unmasking",
        "actor": actor,
        "time_utc": datetime.now(timezone.utc).isoformat(),
        "manifest_commit": ref.commit,
        "manifest_path": ref.path,
        "sealed_output_sha256": manifest["sealed_output_sha256"],
        "pair": pair,
        "custody_limit": "Auditable sequencing, not independent blinding; filesystem access can reveal mapping.",
    }
    _write_exclusive(event_path, _canonical(event))
    return {
        "pair": pair,
        "stages": {s: output["stages"][s]["pairs"][pair] for s in ("1", "2")},
        "decision": output["pair_decisions"][pair],
        "event": event,
    }
