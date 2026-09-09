"""Stage preserved sources and record offline financial review observations."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

PROGRAMS = ("arithmetic_probe.py", "retry_headroom_probe.py", "run_probes.py")
PATCHES = ("0001-spend-limit-not-retryable.diff", "0002-conservative-generation-reservation.diff")
OFFLINE_GUARD = '''"""No network connections in independent financial probes."""
import socket

def refuse_network(*args, **kwargs):
    raise RuntimeError("network operations are disabled for offline financial probes")

socket.create_connection = refuse_network
socket.getaddrinfo = refuse_network
socket.socket.connect = refuse_network
socket.socket.connect_ex = refuse_network
socket.socket.sendto = refuse_network
'''
ENVIRONMENT_PROBE = """import importlib.metadata, json, platform, socket, sys
try:
    socket.getaddrinfo("network-guard.invalid", 443)
except RuntimeError as error:
    assert str(error) == "network operations are disabled for offline financial probes"
else:
    raise AssertionError("offline guard was not installed")
print(json.dumps({
    "python": platform.python_version(), "executable": sys.executable,
    "platform": platform.platform(), "network_guard_checked": True,
    "packages": {name: importlib.metadata.version(name) for name in
        ("openai", "httpx", "pydantic", "numpy", "scipy", "cma", "pytest", "ruff")},
}))
"""


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def hashes(root):
    return {
        str(path.relative_to(root)): digest(path)
        for path in sorted(root.rglob("*"))
        if path.is_file()
        and not any(part in ("__pycache__", ".pytest_cache", ".ruff_cache") for part in path.parts)
        and not path.name.startswith("._")
    }


def copy_preserved(source, target):
    shutil.copytree(
        source,
        target,
        ignore=shutil.ignore_patterns("__pycache__", ".pytest_cache", ".ruff_cache", "._*"),
    )
    if hashes(source) != hashes(target):
        raise RuntimeError("staged source hashes differ from preserved bytes")


def main(argv=None):
    here = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--python", default=sys.executable, help="existing review Python runtime")
    parser.add_argument("--repo-root", type=Path, default=here.parents[3])
    parser.add_argument("--submission", type=Path, default=here.parent / "submission")
    parser.add_argument("--results", type=Path, default=here / "evidence")
    args = parser.parse_args(argv)
    repository, submission, results = (
        args.repo_root.resolve(),
        args.submission.resolve(),
        args.results.resolve(),
    )
    original_source = repository / "research" / "counted-admission" / "provider-candidate"
    if not (submission / "qbridge_e9" / "money.py").is_file():
        parser.error("submission must contain the preserved revision-2 packages")
    if not (original_source / "counted_responses_provider" / "contract.py").is_file():
        parser.error("repo-root must contain the preserved original provider candidate")
    patch_command = shutil.which("patch")
    if patch_command is None:
        parser.error("the local patch command is required")
    results.mkdir(parents=True, exist_ok=True)
    inputs = {
        "submission": hashes(submission),
        "original_provider": hashes(original_source),
        "core": hashes(repository / "src"),
        "fixtures": hashes(repository / "research" / "counted-admission" / "e9-inputs"),
    }
    summary = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "evidence_type": "offline arithmetic checks and a qualified component counterexample",
        "experimental_count_calls": 0,
        "experimental_generation_calls": 0,
        "live_spending_authority": False,
        "credential_environment_inherited": False,
        "network_guard": "Python socket connection, DNS and sendto operations raise before access",
        "source_sha256": inputs,
        "probe_sha256": {name: digest(here / name) for name in PROGRAMS},
        "offline_guard_sha256": hashlib.sha256(OFFLINE_GUARD.encode()).hexdigest(),
        "patches": [],
        "results": [],
    }
    with tempfile.TemporaryDirectory(prefix="qbridge-financial-probes-") as temporary:
        stage = Path(temporary)
        copied, original, patched = stage / "e9rev2", stage / "original", stage / "patched"
        copy_preserved(submission, copied)
        copy_preserved(original_source, original)
        copy_preserved(original_source, patched)
        (stage / "repo").symlink_to(repository, target_is_directory=True)
        guard, scratch = stage / "offline_guard", stage / "scratch"
        guard.mkdir()
        scratch.mkdir()
        (guard / "sitecustomize.py").write_text(OFFLINE_GUARD)
        base_environment = {
            "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
            "TMPDIR": str(scratch),
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONHASHSEED": "0",
        }
        for patch in PATCHES:
            path = copied / "patches" / patch
            completed = subprocess.run(
                [patch_command, "-p4", "--batch", "--forward", "-i", str(path)],
                cwd=patched,
                env=base_environment,
                capture_output=True,
                text=True,
                timeout=30,
                check=False,
            )
            label = Path(patch).stem
            (results / f"{label}.stdout.log").write_text(completed.stdout)
            (results / f"{label}.stderr.log").write_text(completed.stderr)
            summary["patches"].append(
                {"patch": patch, "sha256": digest(path), "exit_code": completed.returncode}
            )
            completed.check_returncode()
        summary["patched_provider_sha256"] = hashes(patched)
        jobs = (
            ("arithmetic", "arithmetic_probe.py", patched, []),
            ("retry_original", "retry_headroom_probe.py", original, ["--variant", "original"]),
            ("retry_patched", "retry_headroom_probe.py", patched, ["--variant", "patched"]),
        )
        for label, program, dependency, flags in jobs:
            environment = dict(
                base_environment,
                PYTHONPATH=os.pathsep.join(
                    map(str, (guard, repository / "src", dependency, copied))
                ),
            )
            runtime = subprocess.run(
                [args.python, "-c", ENVIRONMENT_PROBE],
                cwd=copied,
                env=environment,
                text=True,
                capture_output=True,
                timeout=30,
                check=True,
            )
            summary["environment"] = json.loads(runtime.stdout)
            completed = subprocess.run(
                [args.python, str(here / program), *flags],
                cwd=copied,
                env=environment,
                text=True,
                capture_output=True,
                timeout=120,
                check=False,
            )
            stdout, stderr = results / f"{label}.stdout.log", results / f"{label}.stderr.log"
            stdout.write_text(completed.stdout)
            stderr.write_text(completed.stderr)
            record = {
                "probe": program,
                "variant": label,
                "exit_code": completed.returncode,
                "stdout_sha256": digest(stdout),
                "stderr_sha256": digest(stderr),
            }
            try:
                payload = json.loads(completed.stdout)
                output = results / f"{label}.json"
                output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
                record["json_sha256"] = digest(output)
                record["observation_recorded"] = True
            except json.JSONDecodeError:
                record["observation_recorded"] = False
            summary["results"].append(record)
        summary["staged_submission_unchanged"] = hashes(copied) == inputs["submission"]
        summary["staged_original_provider_unchanged"] = (
            hashes(original) == inputs["original_provider"]
        )
    summary["preserved_submission_unchanged"] = hashes(submission) == inputs["submission"]
    summary["preserved_provider_unchanged"] = hashes(original_source) == inputs["original_provider"]
    (results / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    print(
        json.dumps({"results": summary["results"], "environment": summary["environment"]}, indent=2)
    )
    unchanged = all(value for key, value in summary.items() if key.endswith("_unchanged"))
    return (
        0
        if unchanged
        and all(row["exit_code"] == 0 and row["observation_recorded"] for row in summary["results"])
        else 1
    )


if __name__ == "__main__":
    raise SystemExit(main())
