import json
import socket

import pytest

from qbridge.preflight import run_preflight
from qbridge import preflight


def test_interrupted_contract_kills_group_and_reaps_child(tmp_path, monkeypatch):
    events = []

    class Child:
        pid = 999999

        def wait(self, timeout=None):
            events.append(("wait", timeout))
            if timeout is not None:
                raise KeyboardInterrupt
            return -9

    monkeypatch.setattr(preflight.subprocess, "Popen", lambda *a, **kw: Child())
    monkeypatch.setattr(preflight.os, "killpg", lambda *args: events.append(("kill", args)))
    with pytest.raises(KeyboardInterrupt):
        preflight._run_contract(["synthetic"], root=tmp_path, environment={}, log=tmp_path / "log")
    assert any(event[0] == "kill" for event in events)
    assert events[-1] == ("wait", None)


def test_snapshot_execution_has_durable_inputs_before_interruption(tmp_path, monkeypatch):
    output = tmp_path / "interrupted"
    monkeypatch.setattr(preflight, "CHECKS", preflight.CHECKS[:1])

    def interrupt(command, *, root, environment, log):
        assert root == output / "inputs"
        assert environment["PYTHONPATH"] == str(root / "src")
        assert (root / "tests/test_physics.py").is_file()
        records = [
            json.loads(line) for line in (output / "EXPOSURE_LOG.jsonl").read_text().splitlines()
        ]
        assert records[0]["state"] == "started"
        assert records[0]["inputs"]["fixture_files"]["tests/test_physics.py"]
        raise KeyboardInterrupt

    monkeypatch.setattr(preflight, "_run_contract", interrupt)
    with pytest.raises(KeyboardInterrupt):
        run_preflight(output)
    records = [
        json.loads(line) for line in (output / "EXPOSURE_LOG.jsonl").read_text().splitlines()
    ]
    assert records[-1]["state"] == "finished"
    assert records[-1]["result"]["error"] == "KeyboardInterrupt"
    assert not (output / "report.json").exists()


def test_supplementary_fixture_failure_is_recorded_in_final_report(tmp_path, monkeypatch):
    monkeypatch.setattr(preflight, "CHECKS", preflight.CHECKS[2:3])

    def contracts_pass(command, *, root, environment, log):
        log.write_text("synthetic contract execution fixture")
        return 0

    def fixture_fails(*args, **kwargs):
        raise ValueError("synthetic supplementary failure")

    monkeypatch.setattr(preflight, "_run_contract", contracts_pass)
    monkeypatch.setattr(preflight, "_fixture", fixture_fails)
    report = run_preflight(tmp_path / "failed")
    assert not report["all_checks_passed"]
    assert report["checks"][0]["error"] == "ValueError"


def test_preflight_preserves_reproducible_offline_contract_records(tmp_path, monkeypatch):
    # This monkeypatch checks the orchestrator only. The subprocess contract
    # suite is inspected source with synthetic adapters, not a network sandbox.
    original_connect = socket.socket.connect

    def no_network(self, address):
        if self.family in (socket.AF_INET, socket.AF_INET6):
            raise AssertionError("offline preflight attempted network access")
        return original_connect(self, address)

    monkeypatch.setattr(socket.socket, "connect", no_network)
    output = tmp_path / "offline"
    report = run_preflight(output)
    assert report["scope"] == "analytic_components_and_synthetic_fixtures"
    assert report["study_objective_evaluations"] == 0
    assert report["experimental_model_calls"] == 0
    assert report["all_checks_passed"]
    assert {row["id"] for row in report["checks"]} == {f"E{i}" for i in range(1, 9)}
    assert all(row["passed"] for row in report["checks"])
    assert report["readiness"]["G-MODEL"] == "pending"
    assert report["readiness"]["G-COST"] == "pending"
    assert not report["frozen"]
    assert report == json.loads((output / "report.json").read_text())
    records = [
        json.loads(line) for line in (output / "EXPOSURE_LOG.jsonl").read_text().splitlines()
    ]
    assert len(records) >= 8
    assert all(row["event"] == "engineering_check" for row in records)
    assert all("inputs" in row for row in records)
    with pytest.raises(FileExistsError):
        run_preflight(output)
