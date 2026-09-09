"""Run counterexamples against an isolated copy of the preserved submission.

Exit zero means all probe programs produced JSON. These are counterexamples,
not passing safety tests and not permission for experimental requests.
"""

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

PROBES = ("gate_probe.py", "cli_probe.py", "orchestrator_probe.py", "reopen_probe.py")
OFFLINE_GUARD = '''"""Network connections are forbidden in independent review probes."""
import socket

def refuse_network(*args, **kwargs):
    raise RuntimeError("network operations are disabled for offline review probes")

socket.create_connection = refuse_network
socket.getaddrinfo = refuse_network
socket.socket.connect = refuse_network
socket.socket.connect_ex = refuse_network
'''
ENVIRONMENT_PROBE = '''import importlib.metadata, json, platform, sys
print(json.dumps({
    "python": platform.python_version(),
    "executable": sys.executable,
    "platform": platform.platform(),
    "packages": {name: importlib.metadata.version(name) for name in
        ("openai", "httpx", "pydantic", "numpy", "scipy", "cma", "pytest", "ruff")},
}))
'''


def hashes(root):
    return {
        str(path.relative_to(root)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(root.rglob("*"))
        if path.is_file()
        and not any(part in ("__pycache__", ".pytest_cache", ".ruff_cache") for part in path.parts)
        and not path.name.startswith("._")
    }


def main(argv=None):
    here = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--python", default=sys.executable, help="existing review runtime")
    parser.add_argument("--repo-root", type=Path, default=here.parents[3])
    parser.add_argument("--submission", type=Path, default=here.parent / "submission")
    parser.add_argument("--results", type=Path, default=here / "evidence")
    args = parser.parse_args(argv)
    repository = args.repo_root.resolve()
    submission = args.submission.resolve()
    results = args.results.resolve()
    if not (submission / "qbridge_e9" / "cli.py").is_file():
        parser.error("submission must contain preserved qbridge_e9 and e9tests packages")
    if not (repository / "src" / "qbridge").is_dir():
        parser.error("repo-root must be the quantum-bridge-lab repository")
    results.mkdir(parents=True, exist_ok=True)
    before = hashes(submission)
    summary = {
        "evidence_type": "counterexample observations; not passing safety tests",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "experimental_count_calls": 0,
        "experimental_generation_calls": 0,
        "live_spending_authority": False,
        "network_guard": "socket connection and DNS operations raise before access",
        "real_api_key_in_child_environment": False,
        "provider_patch_applied": False,
        "submission_sha256": before,
        "probe_sha256": {
            name: hashlib.sha256((here / name).read_bytes()).hexdigest() for name in PROBES
        },
        "results": [],
    }
    with tempfile.TemporaryDirectory(prefix="qbridge-e9-probes-") as temporary:
        stage = Path(temporary)
        copied = stage / "e9"
        shutil.copytree(
            submission,
            copied,
            ignore=shutil.ignore_patterns("__pycache__", ".pytest_cache", ".ruff_cache", "._*"),
        )
        if hashes(copied) != before:
            raise RuntimeError("staged submission hashes differ from preserved bytes")
        (stage / "repo").symlink_to(repository, target_is_directory=True)
        guard = stage / "offline_guard"
        guard.mkdir()
        (guard / "sitecustomize.py").write_text(OFFLINE_GUARD)
        scratch = stage / "scratch"
        scratch.mkdir()
        environment = {
            "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
            "TMPDIR": str(scratch),
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONHASHSEED": "0",
            "PYTHONPATH": os.pathsep.join(
                map(str, (
                    guard,
                    stage / "repo" / "src",
                    stage / "repo" / "research" / "counted-admission" / "provider-candidate",
                    copied,
                ))
            ),
        }
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
        for name in PROBES:
            completed = subprocess.run(
                [args.python, str(here / name)],
                cwd=copied,
                env=environment,
                text=True,
                capture_output=True,
                timeout=120,
                check=False,
            )
            label = Path(name).stem
            (results / f"{label}.stdout.log").write_text(completed.stdout)
            (results / f"{label}.stderr.log").write_text(completed.stderr)
            record = {"probe": name, "exit_code": completed.returncode}
            try:
                payload = json.loads(completed.stdout)
                (results / f"{label}.json").write_text(
                    json.dumps(payload, indent=2, sort_keys=True) + "\n"
                )
                record["observation_recorded"] = True
            except json.JSONDecodeError:
                record["observation_recorded"] = False
            summary["results"].append(record)
    summary["preserved_submission_unchanged"] = hashes(submission) == before
    (results / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    print(json.dumps({key: value for key, value in summary.items() if not key.endswith("sha256")},
                     indent=2, sort_keys=True))
    return 0 if summary["preserved_submission_unchanged"] and all(
        row["exit_code"] == 0 and row["observation_recorded"] for row in summary["results"]
    ) else 1


if __name__ == "__main__":
    raise SystemExit(main())
