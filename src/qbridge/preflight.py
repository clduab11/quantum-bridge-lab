"""Run the checked-in analytic/synthetic contracts, preserving their exact inputs.

This source-checkout command has no provider adapter or study objective. Passing
these checks does not freeze a protocol or close real-provider readiness gates.
"""

import argparse
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import signal
import subprocess
import sys
import time

PROTOCOL_SHA256 = "0df9242fd2d0ad5d30b75ea91f498842ac68fe0df9616afd4c9c04518233eda5"
CHECKS = (
    ("E1", "Propagator identities", ["tests/test_physics.py"], "segment or rotation or generator"),
    (
        "E2",
        "Fidelity identities and independent state-average conversion",
        ["tests/test_physics.py"],
        "fidelity or average_gate",
    ),
    (
        "E3",
        "Literal synthetic aggregation and component timing",
        ["tests/test_physics.py"],
        "synthetic_mean or aggregation",
    ),
    ("E4", "Overflow-safe disk mapping", ["tests/test_physics.py"], "mapping"),
    ("E5", "JSON envelope and per-slot salvage", ["tests/test_proposals.py"], "not render"),
    ("E6", "Literal prompt rendering", ["tests/test_proposals.py"], "render"),
    (
        "E7",
        "Synthetic failure, custody-of-events and seed contracts",
        ["tests/test_runner.py", "tests/test_journal.py", "tests/test_seeds.py"],
        None,
    ),
    (
        "E8",
        "Locked inference and temporary synthetic custody",
        ["tests/test_analysis.py", "tests/test_custody.py"],
        None,
    ),
)


def _hash(data):
    return hashlib.sha256(data).hexdigest()


def _write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    with os.fdopen(descriptor, "wb") as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())
    descriptor = os.open(path.parent, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _json(data):
    return (json.dumps(data, indent=2, sort_keys=True, allow_nan=False) + "\n").encode()


def _run_contract(command, *, root, environment, log):
    # A finite group timeout also stops fixture children if a regression hangs.
    with log.open("xb") as stream:
        process = subprocess.Popen(
            command,
            cwd=root,
            env=environment,
            stdout=stream,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
        try:
            return process.wait(timeout=180)
        except subprocess.TimeoutExpired:
            _stop_group(process)
            stream.write(b"\nPreflight contract group exceeded 180 seconds.\n")
            return 124
        except BaseException:
            _stop_group(process)
            raise
        finally:
            stream.flush()
            os.fsync(stream.fileno())


def _stop_group(process):
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass
    process.wait()


def _event(path, event):
    with path.open("ab") as stream:
        stream.write(json.dumps(event, sort_keys=True, allow_nan=False).encode() + b"\n")
        stream.flush()
        os.fsync(stream.fileno())


def _component_timings():
    from qbridge.physics import mean_infidelity, segment_unitary
    from qbridge.proposals import parse_response

    response = json.dumps({"proposals": [[0.0] * 20 for _ in range(10)]})
    start = time.perf_counter()
    for _ in range(100):
        segment_unitary([0.25, -0.5, 0.75], 0.125)
        mean_infidelity([0.25, 0.75])
        parse_response(response)
    return {
        "repetitions": 100,
        "seconds": time.perf_counter() - start,
        "scope": "component arithmetic and parser only; imports excluded",
        "inputs": {
            "generator": [0.25, -0.5, 0.75],
            "dt": 0.125,
            "fidelities": [0.25, 0.75],
            "response": response,
        },
    }


def _cma_options():
    import cma
    from qbridge.seeds import seed_manifest

    seed = seed_manifest(0)
    optimizer = cma.CMAEvolutionStrategy(
        [0.0] * 20, 0.5, {"popsize": 10, "seed": seed["cma_seed"], "verbose": -9}
    )
    return {
        "scope": "constructed only; no objective",
        "seed_fixture": seed,
        "effective_options_repr": {str(k): repr(v) for k, v in optimizer.opts.items()},
    }


def _fixture(name, *, snapshot, environment, output):
    filename = "component_timing.json" if name == "timing" else "cma_options.json"
    code = _run_contract(
        [
            sys.executable,
            "-c",
            "import sys; from pathlib import Path; from qbridge.preflight import "
            "_write, _json, _component_timings, _cma_options; "
            "_write(Path(sys.argv[2]), _json((_component_timings if sys.argv[1] == 'timing' "
            "else _cma_options)()))",
            name,
            str(output / filename),
        ],
        root=snapshot,
        environment=environment,
        log=output / f"{name}-fixture.log",
    )
    if code:
        raise RuntimeError(f"{name} fixture exited {code}; see preserved fixture log")
    return json.loads((output / filename).read_text())


def run_preflight(output):
    """Create a new evidence directory; failed checks remain recorded there."""
    root = Path(__file__).resolve().parents[2]
    protocol = root / "specification/ai_quantum_control_protocol_v0.4.md"
    if _hash(protocol.read_bytes()) != PROTOCOL_SHA256:
        raise ValueError("protocol differs from the reviewed v0.4; reassess before preflight")
    output = Path(output).resolve()
    output.mkdir(mode=0o700, parents=True, exist_ok=False)
    source_paths = sorted(
        set(
            [
                *root.glob("src/qbridge/**/*.py"),
                *root.glob("src/qbridge/prompts/*.txt"),
                *root.glob("tests/*.py"),
                *root.glob("analysis/*.py"),
                *root.glob("prompts/*.txt"),
                root / "pyproject.toml",
                root / "uv.lock",
                protocol,
            ]
        )
    )
    hashes = {}
    for path in source_paths:
        relative = str(path.relative_to(root))
        data = path.read_bytes()
        hashes[relative] = _hash(data)
        _write(output / "inputs" / relative, data)

    snapshot = output / "inputs"
    # Tests, their CLI subprocesses, and supplementary fixtures import this
    # archived checkout. The live worktree may change without changing evidence.
    environment = os.environ.copy()
    environment.update({"PYTHONPATH": str(snapshot / "src"), "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1"})
    environment.pop("PYTEST_ADDOPTS", None)
    checks = []
    exposure_log = output / "EXPOSURE_LOG.jsonl"
    _write(exposure_log, b"")
    for identifier, title, files, selection in CHECKS:
        args = ["-m", "pytest", "-q", "-p", "no:cacheprovider", "-o", "addopts=", *files]
        if selection:
            args.extend(["-k", selection])
        inputs = {
            "fixture_files": {name: hashes[name] for name in files},
            "pytest_arguments": args,
            "fixture_scope": "analytic components or fabricated records; source bytes archived",
        }
        if identifier in {"E3", "E7"}:
            inputs["supplementary_fixture"] = {
                "name": "timing" if identifier == "E3" else "cma_options",
                "source": "src/qbridge/preflight.py",
                "source_sha256": hashes["src/qbridge/preflight.py"],
            }
        event = {
            "event": "engineering_check",
            "id": identifier,
            "inputs": inputs,
            "study_objective_evaluations": 0,
            "experimental_model_calls": 0,
        }
        _event(exposure_log, {**event, "state": "started"})
        start = time.perf_counter()
        row = {"id": identifier, "name": title, "passed": False}
        try:
            code = _run_contract(
                [sys.executable, *args],
                root=snapshot,
                environment=environment,
                log=output / f"{identifier}.log",
            )
            row.update(
                {
                    "exit_code": code,
                    "passed": code == 0,
                    "log_sha256": _hash((output / f"{identifier}.log").read_bytes()),
                }
            )
            if identifier == "E3":
                row["component_timing"] = _fixture(
                    "timing", snapshot=snapshot, environment=environment, output=output
                )
            if identifier == "E7":
                _fixture("options", snapshot=snapshot, environment=environment, output=output)
                row["cma_options_sha256"] = _hash((output / "cma_options.json").read_bytes())
            if identifier == "E6":
                equal = all(
                    (snapshot / "prompts" / name).read_bytes()
                    == (snapshot / "src/qbridge/prompts" / name).read_bytes()
                    for name in ("system_v0.3.txt", "user_template_v0.3.txt")
                )
                row["canonical_and_packaged_prompts_equal"] = equal
                row["passed"] = row["passed"] and equal
        except BaseException as exc:
            row.update({"passed": False, "error": type(exc).__name__, "message": str(exc)})
            if not isinstance(exc, Exception):
                raise
        finally:
            row["elapsed_seconds"] = time.perf_counter() - start
            checks.append(row)
            _event(exposure_log, {**event, "state": "finished", "result": row})

    snapshot_unchanged = all(
        _hash((snapshot / name).read_bytes()) == digest for name, digest in hashes.items()
    )
    report = {
        "schema": "qbridge.offline-preflight.v1",
        "scope": "analytic_components_and_synthetic_fixtures",
        "study_objective_evaluations": 0,
        "experimental_model_calls": 0,
        "frozen": False,
        "all_checks_passed": snapshot_unchanged and all(row["passed"] for row in checks),
        "executed_snapshot_unchanged": snapshot_unchanged,
        "checks": checks,
        "source_sha256": hashes,
        "python": platform.python_version(),
        "packages": {
            name: importlib.metadata.version(name)
            for name in ("numpy", "scipy", "cma", "pytest", "ruff", "pip-audit")
        },
        "readiness": {
            name: "pending"
            for name in (
                "G-ENV",
                "G-CMA",
                "G-MODEL",
                "G-TRANSPORT",
                "G-CUSTODY",
                "G-LOCK",
                "G-EXPOSURE",
                "G-STORAGE",
                "G-RUNTIME",
                "G-COST",
            )
        },
        "readiness_note": "Evidence for offline components only. Full manifest, real-provider "
        "validation, protected study storage, roles and cost decisions remain.",
    }
    _write(output / "report.json", _json(report))
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    report = run_preflight(args.output_dir)
    print(
        json.dumps(
            {
                "all_checks_passed": report["all_checks_passed"],
                "report": str(args.output_dir / "report.json"),
                "frozen": False,
            }
        )
    )
    return 0 if report["all_checks_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
