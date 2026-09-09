"""Observe rev2 gate fixes and the two remaining independent counterexamples."""

import contextlib
import io
import json
import os
import shutil
import socket
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import httpx
from e9tests import support
from e9tests.test_gate import _complete_evidence, gate
from qbridge_e9 import cli, mocks
from qbridge_e9.fixtures import FixtureError, load_fixture_set


def no_network(*args, **kwargs):
    raise RuntimeError("network prohibited in offline review")


def main():
    socket.socket.connect = no_network
    socket.socket.connect_ex = no_network
    socket.create_connection = no_network
    socket.getaddrinfo = no_network
    repo = support.REPO_ROOT.resolve()
    root = Path(tempfile.mkdtemp(prefix="qbridge-rev2-gates-"))
    out = {"experimental_requests": 0, "network_blocked": True}

    # Recheck the earlier concrete defects.
    gitroot = root / "git"
    gitroot.mkdir()
    subprocess.run(["git", "init", "-q", str(gitroot)], check=True)
    e = _complete_evidence(root / "evidence")
    e["records_dir"] = support.private_dir(gitroot / "out" / "raw")
    out["normal_git_refused"] = "records.private" in [r.key for r in gate(**e).failures]
    link = root / "outside-link"
    link.symlink_to(e["records_dir"])
    e["records_dir"] = link
    out["symlink_into_git_refused"] = "records.private" in [r.key for r in gate(**e).failures]
    linked = root / "linked"
    linked.mkdir()
    (linked / ".git").write_text("gitdir: /tmp/not-used\n")
    e["records_dir"] = support.private_dir(linked / "raw")
    out["linked_marker_refused"] = "records.private" in [r.key for r in gate(**e).failures]

    fixtures = root / "fixtures"
    shutil.copytree(support.FIXTURES_DIR, fixtures)
    manifest = json.loads((fixtures / "manifest.json").read_text())
    manifest["source_sha256"] = {}
    (fixtures / "manifest.json").write_text(json.dumps(manifest))
    try:
        load_fixture_set(fixtures, repo_root=repo, reasoning_effort="medium")
    except FixtureError as exc:
        out["mutated_manifest_refused"] = str(exc)
    baseline = load_fixture_set(support.FIXTURES_DIR, repo_root=repo, reasoning_effort="medium")
    out["baseline_checks"] = sum(c.passed for c in baseline.checks)

    e = _complete_evidence(root / "expiry-evidence")
    authpath = e["authorization_record"]
    auth = json.loads(authpath.read_text())
    auth["approved_at_utc"] = "invalid UTC, not an instant"
    authpath.write_text(json.dumps(auth))
    out["invalid_timestamp_refused"] = "authorization.bound_and_timed" in [
        r.key for r in gate(**e).failures
    ]
    with contextlib.redirect_stderr(io.StringIO()) as stderr:
        out["bare_cli_exit"] = cli.main([])
    out["bare_cli_stderr"] = stderr.getvalue().strip()

    class SpyEnvironment(dict):
        reads = 0

        def get(self, key, default=None):
            if key == "OPENAI_API_KEY":
                self.reads += 1
            return super().get(key, default)

    oldenv = os.environ
    spy = SpyEnvironment({"OPENAI_API_KEY": "FABRICATED-never-real"})
    os.environ = spy
    try:
        args = cli.build_parser().parse_args(
            [
                "dry-run",
                "--fixtures",
                str(support.FIXTURES_DIR),
                "--repo-root",
                str(repo),
                "--work-dir",
                str(root / "dry"),
            ]
        )
        report, _ = cli.run_mode(args, "dry-run")
        out["dry_run_key_reads"] = spy.reads
        out["dry_run_fabricated"] = report["fabricated_responses"]
    finally:
        os.environ = oldenv

    # Gate-only command claims all requirements passed without checking either input.
    e = _complete_evidence(root / "gate-evidence")
    authority_path = root / "authority.json"
    authority_path.write_text(json.dumps(e["authority"].as_dict()))
    command = [
        "gate",
        "--fixtures",
        str(root / "ABSENT-FIXTURES"),
        "--repo-root",
        str(root / "ABSENT-REPO"),
        "--work-dir",
        str(root / "gate-work"),
        "--authority",
        str(authority_path),
        "--adoption-evidence",
        str(e["adoption_evidence"]),
        "--billing-evidence",
        str(e["billing_evidence"]),
        "--authorization",
        str(e["authorization_record"]),
        "--specification",
        str(e["specification_path"]),
        "--check-credential",
    ]
    oldenv = os.environ
    os.environ = SpyEnvironment({"OPENAI_API_KEY": "FABRICATED-never-real"})
    try:
        with contextlib.redirect_stdout(io.StringIO()) as stdout:
            code = cli.main(command)
        result = json.loads(stdout.getvalue())
        out["gate_with_absent_inputs"] = {
            "exit_code": code,
            "may_dispatch_live": result["may_dispatch_live"],
            "passed": result["requirements_passed"],
            "failed": result["failed_keys"],
        }
    finally:
        os.environ = oldenv

    # Follow the live control path solely with a fabricated BaseTransport. No socket
    # can be opened; no real HTTP transport is created. Advance the clock after the
    # first count so every subsequent dispatch is after the recorded approval expiry.
    e = _complete_evidence(root / "live-expiry-evidence")
    wall = [support.WALL]
    expires = support.WALL + 1
    auth = json.loads(e["authorization_record"].read_text())
    auth["expires_at_utc"] = datetime.fromtimestamp(expires, timezone.utc).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )
    e["authorization_record"].write_text(json.dumps(auth))
    authority_path.write_text(json.dumps(e["authority"].as_dict()))
    seen = []

    class FabricatedTransport(httpx.BaseTransport):
        def handle_request(self, request):
            is_count = request.url.path.endswith("/input_tokens")
            seen.append(
                {
                    "class": "count" if is_count else "generation",
                    "wall": wall[0],
                    "after_approval_expiry": wall[0] >= expires,
                }
            )
            response = (
                mocks.derived_count(request) if is_count else mocks.derived_generation(request)
            )
            if len(seen) == 1:
                wall[0] += 2
            return response

    original_factory = cli._inner_transport_factory
    original_time = cli.time.time
    cli._inner_transport_factory = lambda mode, fs: (
        lambda: FabricatedTransport(),
        "FABRICATED-review-only",
    )
    cli.time.time = lambda: wall[0]
    try:
        args = cli.build_parser().parse_args(
            [
                "live",
                "--fixtures",
                str(support.FIXTURES_DIR),
                "--repo-root",
                str(repo),
                "--work-dir",
                str(root / "expiry-work"),
                "--authority",
                str(authority_path),
                "--adoption-evidence",
                str(e["adoption_evidence"]),
                "--billing-evidence",
                str(e["billing_evidence"]),
                "--authorization",
                str(e["authorization_record"]),
                "--specification",
                str(e["specification_path"]),
                "--confirm-live",
            ]
        )
        report, _ = cli.run_mode(args, "live", env={"OPENAI_API_KEY": "FABRICATED-never-real"})
        out["approval_expiry_during_run"] = {
            "fabricated_dispatches": seen,
            "accepted": report["acceptance"]["e9_accepted"],
            "gate_initially_passed": report["gate"]["may_dispatch_live"],
            "stop_reason": report["run"]["stop_reason"],
        }
    finally:
        cli._inner_transport_factory = original_factory
        cli.time.time = original_time
    out["private_probe_directory"] = str(root)
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
