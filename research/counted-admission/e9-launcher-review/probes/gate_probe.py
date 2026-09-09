"""Offline counterexamples for the preserved E9 fixture and live gate code."""

import json
import shutil
import subprocess
import tempfile
from pathlib import Path

from counted_responses_provider import contract as C
from counted_responses_provider.provider import SingleAttemptResponsesProvider
from e9tests import support
from e9tests.test_gate import _complete_evidence, gate
from qbridge.request_records import RequestRecords
from qbridge_e9.fixtures import load_fixture_set, sha256_hex


def main():
    root = Path(tempfile.mkdtemp(prefix="gate-probe-"))
    evidence_dir = root / "evidence"
    evidence_dir.mkdir()
    evidence = _complete_evidence(evidence_dir)

    # Only this new temporary repository is initialized. The reviewed project
    # and its history are never changed.
    gitroot = root / "worktree-layout"
    gitroot.mkdir()
    subprocess.run(["git", "init", "-q", str(gitroot)], check=True)
    records = support.private_dir(gitroot / "out" / "raw")
    evidence["records_dir"] = records
    result = gate(**evidence)
    store = RequestRecords(records, public_repo=records.parent / "public_repo_guard")
    store.close()
    output = {
        "git_records_gate": {
            "layout": "new temporary Git repository; git init only",
            "may_dispatch_live": result.may_dispatch_live,
            "requirement": next(
                row.as_dict() for row in result.requirements if row.key == "records.private"
            ),
            "records_writer_accepts": True,
        }
    }

    target = root / "fixtures"
    shutil.copytree(support.FIXTURES_DIR, target)
    manifest = json.loads((target / "manifest.json").read_text())
    entry = manifest["fixtures"][0]
    text = "Review probe changed this committed F1 user prompt."
    for request_class in ("count", "generation"):
        spec = entry["files"][request_class]
        path = target / spec["path"]
        body = json.loads(path.read_bytes())
        body["input"][1]["content"] = text
        data = C.canonical_bytes(body)
        path.write_bytes(data)
        spec.update(sha256=sha256_hex(data), bytes=len(data))
    entry.update(
        user_sha256=sha256_hex(text.encode("ascii")),
        user_bytes=len(text),
        combined_text_bytes=entry["system_bytes"] + len(text),
    )
    (target / "manifest.json").write_text(json.dumps(manifest))

    class PurePrepare:
        effort = "medium"
        prepare = SingleAttemptResponsesProvider.prepare

    fixture_set = load_fixture_set(
        target,
        reasoning_effort="medium",
        provider=PurePrepare(),
        repo_root=support.REPO_ROOT,
    )
    output["changed_committed_fixture"] = {
        "checks_passed": sum(check.passed for check in fixture_set.checks),
        "checks_failed": len(fixture_set.failed),
        "user_text": fixture_set.fixtures[0].user_text,
        "original_manifest_sha256": sha256_hex(
            (support.FIXTURES_DIR / "manifest.json").read_bytes()
        ),
        "accepted_mutated_manifest_sha256": fixture_set.manifest_sha256,
    }

    evidence["records_dir"] = support.private_dir(root / "outside-raw")
    path = evidence["authorization_record"]
    authorization = json.loads(path.read_text())
    authorization["approved_at_utc"] = "invalid UTC, not an instant"
    path.write_text(json.dumps(authorization))
    result = gate(**evidence)
    output["invalid_approval_timestamp"] = {
        "may_dispatch_live": result.may_dispatch_live,
        "requirement": next(
            row.as_dict()
            for row in result.requirements
            if row.key == "authorization.explicit_e9"
        ),
    }
    manifest["source_sha256"] = {}
    (target / "manifest.json").write_text(json.dumps(manifest))
    fixture_set = load_fixture_set(
        target, reasoning_effort="medium", repo_root=support.REPO_ROOT
    )
    output["empty_source_hash_set_accepted"] = not fixture_set.failed
    print(json.dumps(output, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
