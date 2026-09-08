"""Crash-accounting tests; all records are synthetic."""

import importlib
import os
import stat

import pytest


def api():
    return importlib.import_module("qbridge.journal")


def test_completed_and_unresolved_objective_counts_survive_reopen(tmp_path):
    journal = api()
    path = tmp_path / "events.jsonl"
    with journal.DurableJournal(path) as log:
        first = log.reserve("objective", "AI:0:1", block=0, arm="AI", slot=1)
        log.complete(first, status="valid", invoked=True, value=0.25)
        log.reserve("objective", "AI:0:2", block=0, arm="AI", slot=2)
    with journal.DurableJournal(path) as log:
        counts = log.resource_counts(block=0, arm="AI")
        assert counts["confirmed_objective_calls"] == 1
        assert counts["unresolved_objective_reservations"] == 1
        assert counts["actual_objective_call_bounds"] == [1, 2]
        with pytest.raises(journal.NoReplayError):
            log.reserve("objective", "AI:0:2", block=0, arm="AI", slot=2)
    assert stat.S_IMODE(path.stat().st_mode) == 0o600


def test_attempt_reservation_does_not_claim_dispatch_or_zero_usage(tmp_path):
    with api().DurableJournal(tmp_path / "events") as log:
        log.reserve("transport", "AI:0:1:1:1", block=0, arm="AI")
        counts = log.resource_counts(block=0, arm="AI")
        assert counts["attempt_allowances_used"] == 1
        assert counts["confirmed_transport_dispatches"] == 0
        assert counts["unresolved_transport_reservations"] == 1
        assert counts["unknown_usage_attempts"] == 1


def test_duplicate_completion_is_rejected_without_appending(tmp_path):
    journal = api()
    with journal.DurableJournal(tmp_path / "events") as log:
        key = log.reserve("objective", "RS:0:1", block=0, arm="RS", slot=1)
        log.complete(key, status="valid", invoked=True, value=0.5)
        before = log.read_events()
        with pytest.raises(journal.NoReplayError):
            log.complete(key, status="valid", invoked=True, value=0.1)
        assert log.read_events() == before


@pytest.mark.parametrize("damage", [b"{unfinished", b"\n"])
def test_corrupt_or_incomplete_tail_fails_closed(tmp_path, damage):
    journal = api()
    path = tmp_path / "events"
    with journal.DurableJournal(path) as log:
        log.append("fixture", value=123)
    with path.open("ab") as stream:
        stream.write(damage)
    with pytest.raises(journal.JournalCorrupt):
        journal.DurableJournal(path)


def test_checksum_detects_a_rewritten_valid_json_record(tmp_path):
    journal = api()
    path = tmp_path / "events"
    with journal.DurableJournal(path) as log:
        log.append("fixture", value=123)
    path.write_bytes(path.read_bytes().replace(b"123", b"124"))
    with pytest.raises(journal.JournalCorrupt):
        journal.DurableJournal(path)


def test_reservation_is_fsynced_before_return(tmp_path, monkeypatch):
    calls = []
    real_fsync = os.fsync

    def observed_fsync(fd):
        real_fsync(fd)
        calls.append(fd)

    monkeypatch.setattr(os, "fsync", observed_fsync)
    with api().DurableJournal(tmp_path / "events") as log:
        before = len(calls)
        log.reserve("objective", "CMA:0:1", block=0, arm="CMA", slot=1)
        assert len(calls) > before
        assert log.read_events()[-1]["kind"] == "reserved"


def test_second_writer_and_symlink_are_rejected(tmp_path):
    journal = api()
    path = tmp_path / "events"
    with journal.DurableJournal(path):
        with pytest.raises(journal.JournalBusy):
            journal.DurableJournal(path)
    link = tmp_path / "link"
    link.symlink_to(path)
    with pytest.raises(OSError):
        journal.DurableJournal(link)


def test_partial_usage_keeps_unknown_categories_and_known_lower_bounds(tmp_path):
    with api().DurableJournal(tmp_path / "events") as log:
        first = log.reserve("transport", "AI:0:1", block=0, arm="AI")
        log.complete(first, dispatched=True, usage={"input_tokens": 7, "cached_tokens": 3})
        second = log.reserve("transport", "AI:0:2", block=0, arm="AI")
        log.complete(second, dispatched=True, usage={})
        counts = log.resource_counts(block=0, arm="AI", usage_categories=("reasoning_tokens",))
        assert counts["usage_lower_bounds"] == {"input_tokens": 7, "output_tokens": 0, "cached_tokens": 3, "reasoning_tokens": 0}
        assert counts["usage_missing_counts"] == {"input_tokens": 1, "output_tokens": 2, "cached_tokens": 1, "reasoning_tokens": 2}
        assert counts["unknown_usage_attempts"] == 2


@pytest.mark.parametrize("bad", [True, -1, 1.0, float("nan"), "3"])
def test_usage_counts_require_native_nonnegative_integers(tmp_path, bad):
    with api().DurableJournal(tmp_path / "events") as log:
        reservation = log.reserve("transport", "AI:0:1", block=0, arm="AI")
        with pytest.raises(ValueError):
            log.complete(reservation, dispatched=True, usage={"input_tokens": bad})
        assert log.resource_counts()["unresolved_transport_reservations"] == 1


def test_confirmed_nondispatch_does_not_widen_dispatch_bound(tmp_path):
    with api().DurableJournal(tmp_path / "events") as log:
        reservation = log.reserve("transport", "AI:0:1", block=0, arm="AI")
        log.complete(reservation, dispatched=False, usage=None)
        log.reserve("transport", "AI:0:2", block=0, arm="AI")
        assert log.resource_counts()["actual_transport_dispatch_bounds"] == [0, 1]
