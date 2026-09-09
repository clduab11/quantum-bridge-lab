"""Crash, reopen and duplicate-dispatch regressions, including real processes.

An attempt whose dispatch outcome is unknown may already have been billed, so
it is never replayed. A finished fixture is never dispatched twice.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

from e9tests import support
from qbridge.journal import DurableJournal, JournalBusy, NoReplayError
from qbridge_e9 import mocks
from qbridge_e9.acceptance import evaluate_acceptance
from qbridge_e9.limits import E9Limits
from qbridge_e9.orchestrator import E9Orchestrator

PROVIDER_PATH = support.REPO_ROOT / "research" / "counted-admission" / "provider-candidate"
PACKAGE_ROOT = Path(__file__).resolve().parents[1]
ENV_PATH = os.pathsep.join(
    [str(support.REPO_ROOT / "src"), str(PROVIDER_PATH), str(PACKAGE_ROOT)]
)


def child_env():
    env = dict(os.environ)
    env["PYTHONPATH"] = ENV_PATH
    env.pop("OPENAI_API_KEY", None)
    return env


def test_rerunning_a_finished_journal_dispatches_nothing_new(tmp_path):
    handler = mocks.derived_transport()
    journal, provider, records_dir, orch, clock, fs = support.build(tmp_path, handler)
    first = orch.run()
    assert [o.outcome for o in first] == ["completed"] * 4
    dispatches = len(handler.count_calls) + len(handler.generation_calls)
    assert dispatches == 8

    again = support.reopen(journal, provider, fs, records_dir, clock)
    second = again.run()
    # Review finding 7: the completed outcomes are reconstructed from the
    # durable journal, not discarded, so acceptance is preserved.
    assert [o.outcome for o in second] == ["completed"] * 4
    assert all(o.reconstructed for o in second)
    assert len(handler.count_calls) + len(handler.generation_calls) == dispatches
    assert again.attempts_used("count") == 4  # unchanged
    assert again.attempts_used("generation") == 4
    assert evaluate_acceptance(journal, second, reasoning_effort="medium").passed


def test_an_unresolved_prior_attempt_is_never_replayed(tmp_path):
    """Simulates a worker that reserved a dispatch and died before completing."""
    handler = mocks.derived_transport()
    journal, provider, records_dir, orch, clock, fs = support.build(tmp_path, handler)
    journal.reserve(
        "transport",
        "E9:0:1:1:count:1",
        block=0,
        arm="E9",
        batch=1,
        logical=1,
        attempt=1,
        request_class="count",
        body_sha256=fs.by_name("F1_short").count_sha256,
        fixture="F1_short",
        dispatch_monotonic=0.0,
        armed_budget_seconds=300.0,
    )
    outcomes = orch.run()
    assert orch.refused_reason.startswith("unresolved_prior_attempt:")
    assert handler.count_calls == [] and handler.generation_calls == []
    assert all(o.outcome == "refused" for o in outcomes)
    refusals = support.events(journal, "e9_run_refused")
    assert refusals and refusals[0]["reason"].startswith("unresolved_prior_attempt:")
    assert refusals[0]["dispatched"] is False
    acceptance = evaluate_acceptance(journal, outcomes, reasoning_effort="medium")
    assert not acceptance.passed


def test_the_journal_refuses_a_reused_reservation_number(tmp_path):
    handler = mocks.derived_transport()
    journal, *_ = support.build(tmp_path, handler)
    journal.reserve("transport", "E9:0:1:1:count:1", block=0, arm="E9", batch=1, logical=1)
    with pytest.raises(NoReplayError):
        journal.reserve("transport", "E9:0:1:1:count:1", block=0, arm="E9", batch=1, logical=1)


def test_a_second_writer_cannot_open_the_same_journal(tmp_path):
    path = support.private_dir(tmp_path / "work") / "j.jsonl"
    with DurableJournal(path):
        with pytest.raises(JournalBusy):
            DurableJournal(path)


# --- real-process regressions ---------------------------------------------


def _cli(work_dir, extra=()):
    return subprocess.run(
        [
            sys.executable,
            "-m",
            "qbridge_e9.cli",
            "dry-run",
            "--fixtures",
            str(support.FIXTURES_DIR),
            "--repo-root",
            str(support.REPO_ROOT),
            "--work-dir",
            str(work_dir),
            *extra,
        ],
        capture_output=True,
        text=True,
        env=child_env(),
        cwd=str(PACKAGE_ROOT),
        timeout=300,
    )


def test_real_process_dry_run_completes_and_reports(tmp_path):
    result = _cli(tmp_path / "run")
    assert result.returncode == 0, result.stderr[-2000:]
    payload = json.loads(result.stdout)
    assert payload["fabricated_responses"] is True
    assert payload["gate_may_dispatch_live"] is False
    assert payload["e9_accepted"] is True
    assert payload["attempts"] == {"count": 4, "generation": 4}
    assert Path(payload["report"]).name.startswith("e9_report_")
    report = json.loads(Path(payload["report"]).read_text())
    authz = report["authorizations"]
    # Review finding 7: derived from the gate, not hardcoded.
    assert authz["amendment_a1_adoption_evidence"] == "fail"
    assert authz["amendment_a1_adopted_per_evidence"] is False
    assert authz["spending_authority_issued_by_this_run"] is False
    assert authz["spending_authority_consumed"] is False
    assert authz["transport_class"] == "httpx.MockTransport"
    assert authz["experimental_generation_calls"] == 0
    assert authz["fabricated_dispatch_attempts"] == {"count": 4, "generation": 4}
    # storage.outside_git is measured, not asserted.
    assert report["storage"]["git_worktree_root"] is None
    assert report["storage"]["outside_git"] is True
    assert report["deadline"]["attempt_wall_clock_enforced_at_transport"] is True


def test_real_process_rerun_on_the_same_work_dir_adds_no_dispatch(tmp_path):
    work = tmp_path / "run"
    first = _cli(work)
    assert first.returncode == 0, first.stderr[-2000:]
    before = sorted(p.name for p in (work / "raw").iterdir())
    second = _cli(work)
    after = sorted(p.name for p in (work / "raw").iterdir())
    assert after == before, "a rerun must not write new raw request records"
    payload = json.loads(second.stdout)
    assert payload["attempts"] == {"count": 4, "generation": 4}
    # Review finding 7: reports are per-run and never overwritten.
    first_report = json.loads(first.stdout)["report"]
    second_report = payload["report"]
    assert first_report != second_report
    assert Path(first_report).is_file() and Path(second_report).is_file()
    index = (work / "e9_reports.jsonl").read_text().strip().splitlines()
    assert len(index) == 2
    assert json.loads(second.stdout)["e9_accepted"] is True


def test_real_child_crash_leaves_an_unresolved_reservation_that_blocks_replay(tmp_path):
    """A hard-killed child cannot erase its reservation, and the parent stops."""
    work = support.private_dir(tmp_path / "work")
    journal_path = work / "e9_journal.jsonl"
    script = textwrap.dedent(
        f"""
        import os, sys
        from qbridge.journal import DurableJournal
        journal = DurableJournal({str(journal_path)!r})
        journal.reserve(
            "transport", "E9:0:1:1:count:1", block=0, arm="E9", batch=1,
            logical=1, attempt=1, request_class="count",
            body_sha256="0"*64, fixture="F1_short",
        )
        os._exit(9)
        """
    )
    child = subprocess.run(
        [sys.executable, "-c", script], capture_output=True, text=True,
        env=child_env(), cwd=str(PACKAGE_ROOT), timeout=120,
    )
    assert child.returncode == 9, child.stderr[-2000:]

    handler = mocks.derived_transport()
    records_dir = support.private_dir(work / "raw")
    with DurableJournal(journal_path) as journal:
        import httpx

        from counted_responses_provider.provider import SingleAttemptResponsesProvider
        from qbridge.request_records import RequestRecords

        from qbridge_e9.deadline import DeadlineGuard, guarded_transport_factory

        clock = support.Clock()
        guard = DeadlineGuard(clock=clock)
        provider = SingleAttemptResponsesProvider(
            journal=journal,
            records=RequestRecords(records_dir, public_repo=work / "guard"),
            authority=support.authority(),
            transport_factory=guarded_transport_factory(
                lambda: httpx.MockTransport(handler), guard
            ),
            api_key_provider=lambda: support.FABRICATED_KEY,
            wall_clock=clock.time,
        )
        orch = E9Orchestrator(
            journal=journal,
            provider=provider,
            fixture_set=support.fixture_set(provider),
            records_dir=records_dir,
            limits=E9Limits(),
            clock=clock,
            sleep=clock.sleep,
            deadline_guard=guard,
        )
        orch.run()
    assert orch.refused_reason.startswith("unresolved_prior_attempt:")
    assert handler.count_calls == [] and handler.generation_calls == []


def test_live_mode_is_refused_without_confirmation_and_without_a_key(tmp_path):
    common = [
        "--fixtures", str(support.FIXTURES_DIR),
        "--repo-root", str(support.REPO_ROOT),
        "--work-dir", str(tmp_path / "live"),
    ]
    unconfirmed = subprocess.run(
        [sys.executable, "-m", "qbridge_e9.cli", "live", *common],
        capture_output=True, text=True, env=child_env(), cwd=str(PACKAGE_ROOT), timeout=120,
    )
    assert unconfirmed.returncode == 2
    assert "--confirm-live is required" in unconfirmed.stderr

    confirmed = subprocess.run(
        [sys.executable, "-m", "qbridge_e9.cli", "live", *common, "--confirm-live"],
        capture_output=True, text=True, env=child_env(), cwd=str(PACKAGE_ROOT), timeout=120,
    )
    assert confirmed.returncode == 2
    assert "refused" in confirmed.stderr
    assert "--authority" in confirmed.stderr or "OPENAI_API_KEY" in confirmed.stderr


def test_gate_subcommand_exits_nonzero_and_prints_every_failure(tmp_path):
    result = subprocess.run(
        [
            sys.executable, "-m", "qbridge_e9.cli", "gate",
            "--fixtures", str(support.FIXTURES_DIR),
            "--repo-root", str(support.REPO_ROOT),
            "--work-dir", str(tmp_path / "gate"),
        ],
        capture_output=True, text=True, env=child_env(), cwd=str(PACKAGE_ROOT), timeout=120,
    )
    assert result.returncode == 2
    payload = json.loads(result.stdout)
    assert payload["may_dispatch_live"] is False
    assert "authority.not_synthetic" in payload["failed_keys"]
    assert payload["requirements_total"] == 20


# --- review finding 8: offline paths and the bare invocation --------------


def test_a_bare_invocation_is_a_clean_usage_error_not_a_crash():
    result = subprocess.run(
        [sys.executable, "-m", "qbridge_e9.cli"],
        capture_output=True, text=True, env=child_env(), cwd=str(PACKAGE_ROOT), timeout=120,
    )
    assert result.returncode == 2
    assert "AttributeError" not in result.stderr
    assert "a subcommand is required" in result.stderr
    assert result.stdout == ""


def test_the_dry_run_never_reads_the_credential_variable(tmp_path):
    """A present OPENAI_API_KEY must not change an offline run, and the gate
    must record the credential as unchecked rather than reading it."""
    env = child_env()
    env["OPENAI_API_KEY"] = "sk-FABRICATED-must-not-be-read"
    result = subprocess.run(
        [
            sys.executable, "-m", "qbridge_e9.cli", "dry-run",
            "--fixtures", str(support.FIXTURES_DIR),
            "--repo-root", str(support.REPO_ROOT),
            "--work-dir", str(tmp_path / "run"),
        ],
        capture_output=True, text=True, env=env, cwd=str(PACKAGE_ROOT), timeout=300,
    )
    assert result.returncode == 0, result.stderr[-2000:]
    payload = json.loads(result.stdout)
    assert "credential.present" in payload["gate_failed_keys"], (
        "an offline run must not be able to satisfy the credential requirement"
    )
    report = json.loads(Path(payload["report"]).read_text())
    detail = next(
        r["detail"] for r in report["gate"]["requirements"] if r["key"] == "credential.present"
    )
    assert "present=False" in detail
    assert "sk-FABRICATED-must-not-be-read" not in Path(payload["report"]).read_text()


def test_the_gate_subcommand_checks_the_credential_only_when_asked(tmp_path):
    env = child_env()
    env["OPENAI_API_KEY"] = "sk-FABRICATED-presence-only"
    base = [
        sys.executable, "-m", "qbridge_e9.cli", "gate",
        "--fixtures", str(support.FIXTURES_DIR),
        "--repo-root", str(support.REPO_ROOT),
    ]
    without = subprocess.run(
        base + ["--work-dir", str(tmp_path / "a")],
        capture_output=True, text=True, env=env, cwd=str(PACKAGE_ROOT), timeout=120,
    )
    with_flag = subprocess.run(
        base + ["--work-dir", str(tmp_path / "b"), "--check-credential"],
        capture_output=True, text=True, env=env, cwd=str(PACKAGE_ROOT), timeout=120,
    )
    assert without.returncode == 2 and with_flag.returncode == 2
    off = json.loads(without.stdout)
    on = json.loads(with_flag.stdout)
    assert "credential.present" in off["failed_keys"]
    assert "credential.present" not in on["failed_keys"]
    assert "sk-FABRICATED-presence-only" not in without.stdout + with_flag.stdout


def test_the_cli_refuses_a_work_dir_inside_a_git_worktree(tmp_path):
    """Review finding 3: raw records must never be written where they can be
    committed, and the refusal happens before anything is created."""
    repo = tmp_path / "somerepo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q", str(repo)], check=True, timeout=60)
    work = repo / "e9-work"
    result = subprocess.run(
        [
            sys.executable, "-m", "qbridge_e9.cli", "dry-run",
            "--fixtures", str(support.FIXTURES_DIR),
            "--repo-root", str(support.REPO_ROOT),
            "--work-dir", str(work),
        ],
        capture_output=True, text=True, env=child_env(), cwd=str(PACKAGE_ROOT), timeout=300,
    )
    assert result.returncode != 0
    assert "Git worktree" in result.stderr or "Git worktree" in result.stdout
    assert not work.exists(), "nothing may be created inside the worktree"
