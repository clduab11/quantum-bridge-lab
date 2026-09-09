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

    again = E9Orchestrator(
        journal=journal,
        provider=provider,
        fixture_set=fs,
        records_dir=records_dir,
        limits=E9Limits(),
        clock=clock,
        sleep=clock.sleep,
    )
    second = again.run()
    assert [o.outcome for o in second] == ["skipped"] * 4
    assert all(o.reason == "already_finished_in_this_journal" for o in second)
    assert len(handler.count_calls) + len(handler.generation_calls) == dispatches
    assert again.attempts_used("count") == 4  # unchanged
    assert again.attempts_used("generation") == 4


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
    )
    outcomes = orch.run()
    assert orch._stop_reason.startswith("unresolved_prior_attempt:")
    assert handler.count_calls == [] and handler.generation_calls == []
    assert all(o.outcome == "not_started" for o in outcomes)
    stops = support.events(journal, "e9_stopped")
    assert stops and stops[0]["reason"].startswith("unresolved_prior_attempt:")
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
    report = json.loads(Path(payload["report"]).read_text())
    assert report["authorizations"]["amendment_a1_adopted"] is False
    assert report["authorizations"]["live_spending_authority_issued"] is False


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

        clock = support.Clock()
        provider = SingleAttemptResponsesProvider(
            journal=journal,
            records=RequestRecords(records_dir, public_repo=work / "guard"),
            authority=support.authority(),
            transport_factory=lambda: httpx.MockTransport(handler),
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
        )
        orch.run()
    assert orch._stop_reason.startswith("unresolved_prior_attempt:")
    assert handler.count_calls == [] and handler.generation_calls == []


def test_live_mode_is_refused_without_confirmation_and_without_a_key(tmp_path):
    common = [
        "--fixtures", str(support.FIXTURES_DIR),
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
            "--work-dir", str(tmp_path / "gate"),
        ],
        capture_output=True, text=True, env=child_env(), cwd=str(PACKAGE_ROOT), timeout=120,
    )
    assert result.returncode == 2
    payload = json.loads(result.stdout)
    assert payload["may_dispatch_live"] is False
    assert "authority.not_synthetic" in payload["failed_keys"]
    assert payload["requirements_total"] == 18
