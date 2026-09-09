"""Review findings 2 and 7: reopening a journal must not reset the deadline,
must not forget a terminal stop, and must not lose a completed result.

Codex's reproductions:

* a first run that exhausted the 7,400 s stop limit was followed by a second
  orchestrator over the SAME journal that dispatched F2-F4 with
  ``remaining_seconds`` back at 7,400;
* after a ``project_spend_limit_exceeded`` stop, a reopen dispatched three more
  count/generation pairs;
* a rerun of a fully completed journal sent nothing but reported
  ``e9_accepted: false`` because the completed outcomes were discarded, and
  overwrote ``e9_report.json``.

Every response here is FABRICATED.
"""

from __future__ import annotations

import pytest

from e9tests import support
from qbridge_e9 import mocks
from qbridge_e9.acceptance import evaluate_acceptance
from qbridge_e9.limits import E9Limits


def run(tmp_path, handler, **kw):
    journal, provider, records_dir, orch, clock, fs = support.build(tmp_path, handler, **kw)
    return journal, provider, records_dir, orch, clock, fs


# --- finding 2: the governing deadline survives a reopen -------------------


def test_an_exhausted_deadline_is_not_reset_by_reopening_the_journal(tmp_path):
    clock = support.Clock()
    state = {"first": True}

    def exhaust_once(request):
        if state["first"]:
            state["first"] = False
            clock.advance(7400)
        return mocks.derived_generation(request)

    handler = mocks.derived_transport(generation_plan=[exhaust_once])
    journal, provider, records_dir, orch, clock, fs = run(tmp_path, handler, clock=clock)
    first = orch.run()
    assert orch._stop_reason == "deadline_exhausted"
    before = (list(handler.count_calls), list(handler.generation_calls))

    second = support.reopen(journal, provider, fs, records_dir, clock)
    outcomes = second.run()

    assert second.refused_reason == "prior_terminal_stop:deadline_exhausted"
    assert second.budget_seconds() <= 0, "consumed time must be subtracted, not reset"
    assert second.remaining_seconds() <= 0
    assert (handler.count_calls, handler.generation_calls) == before, "no new dispatch"
    # F1 finished in the first run and is reconstructed, not re-sent.
    assert outcomes[0].outcome == first[0].outcome == "completed"
    assert outcomes[0].reconstructed is True
    assert [o.outcome for o in outcomes[1:]] == ["refused"] * 3
    assert support.events(journal, "e9_run_refused")[0]["dispatched"] is False
    journal.close()


def test_a_terminal_spend_limit_stop_refuses_every_later_run(tmp_path):
    def billed(request):
        return mocks.error_response(429, code="project_spend_limit_exceeded")

    handler = mocks.derived_transport(count_plan=[billed, mocks.derived_count])
    journal, provider, records_dir, orch, clock, fs = run(tmp_path, handler)
    orch.run()
    assert orch._stop_reason == "spend_limit_halt:project_spend_limit_exceeded"
    before = (list(handler.count_calls), list(handler.generation_calls))

    second = support.reopen(journal, provider, fs, records_dir, clock)
    outcomes = second.run()

    assert second.refused_reason == (
        "prior_terminal_stop:spend_limit_halt:project_spend_limit_exceeded"
    )
    assert (handler.count_calls, handler.generation_calls) == before
    assert [o.outcome for o in outcomes[1:]] == ["refused"] * 3
    # The launcher's own e9_stopped reason is always recorded and is the one
    # the refusal quotes. With patch 0001 applied the provider ALSO records a
    # credential halt for the same 429, which is additional, not conflicting.
    reasons = {t["reason"] for t in second.terminal_records()}
    assert "spend_limit_halt:project_spend_limit_exceeded" in reasons
    assert any(t["kind"] == "e9_stopped" for t in second.terminal_records())
    journal.close()


def test_consumed_time_accumulates_across_runs(tmp_path):
    clock = support.Clock()
    per_call = {"n": 0}

    def slow(request):
        per_call["n"] += 1
        clock.advance(1000)
        return mocks.derived_generation(request)

    handler = mocks.derived_transport(generation_plan=[slow])
    journal, provider, records_dir, orch, clock, fs = run(tmp_path, handler, clock=clock)
    orch.run()
    consumed = journal.read_events()
    finished = [e for e in consumed if e["kind"] == "e9_run_finished"]
    assert finished and finished[0]["consumed_seconds"] >= 4000
    second = support.reopen(journal, provider, fs, records_dir, clock)
    # Nothing is left to do, but the budget must reflect what was consumed.
    assert second.consumed_seconds() == finished[0]["consumed_seconds"]
    assert second.budget_seconds() == pytest.approx(
        E9Limits().deadline_seconds - finished[0]["consumed_seconds"]
    )
    journal.close()


def test_an_unresolved_prior_attempt_refuses_continuation(tmp_path):
    handler = mocks.derived_transport()
    journal, provider, records_dir, orch, clock, fs = run(tmp_path, handler)
    # Simulate a process that died between reserving and completing: the
    # dispatch outcome is unknown and may already have been billed.
    journal.reserve(
        "transport",
        "E9:E9-preflight:1:1:count:1:orphan",
        block="E9-preflight",
        arm="E9",
        batch=1,
        logical=1,
        attempt=1,
        request_class="count",
        body_sha256="0" * 64,
        fixture="F1_short",
        dispatch_monotonic=0.0,
        armed_budget_seconds=300.0,
    )
    outcomes = orch.run()
    assert orch.refused_reason.startswith("unresolved_prior_attempt:")
    assert [o.outcome for o in outcomes] == ["refused"] * 4
    assert handler.count_calls == [] and handler.generation_calls == []
    journal.close()


# --- finding 7: a completed result is preserved ----------------------------


def test_a_rerun_of_a_completed_journal_preserves_acceptance(tmp_path):
    handler = mocks.derived_transport()
    journal, provider, records_dir, orch, clock, fs = run(tmp_path, handler)
    first = orch.run()
    first_record = evaluate_acceptance(journal, first, reasoning_effort="medium").as_dict()
    assert first_record["e9_accepted"] is True
    dispatched = (list(handler.count_calls), list(handler.generation_calls))

    second = support.reopen(journal, provider, fs, records_dir, clock)
    outcomes = second.run()
    second_record = evaluate_acceptance(journal, outcomes, reasoning_effort="medium").as_dict()

    assert (handler.count_calls, handler.generation_calls) == dispatched, "nothing re-sent"
    assert all(o.reconstructed for o in outcomes)
    assert second_record["e9_accepted"] is True
    assert second_record["failed_keys"] == []
    assert second_record["not_demonstrated_keys"] == []
    assert second_record["f2_f3_gap_seconds"] == first_record["f2_f3_gap_seconds"]
    assert second_record["identity_baseline_accepted"] is False
    journal.close()


def test_reconstruction_recovers_counts_admission_and_parse_results(tmp_path):
    handler = mocks.derived_transport()
    journal, provider, records_dir, orch, clock, fs = run(tmp_path, handler)
    first = orch.run()
    second = support.reopen(journal, provider, fs, records_dir, clock).run()
    for original, rebuilt in zip(first, second):
        assert rebuilt.fixture == original.fixture
        assert rebuilt.outcome == original.outcome
        assert rebuilt.counted_tokens == original.counted_tokens
        assert rebuilt.admission == original.admission
        assert rebuilt.parse == original.parse
        assert rebuilt.count_attempts == original.count_attempts
        assert rebuilt.generation_attempts == original.generation_attempts
        assert rebuilt.identity_vector == original.identity_vector
    journal.close()


def _truncate_journal_after(source, destination, kind, fixture):
    """Copy the journal up to and including one event, as a clean kill would.

    The journal is an append-only hash chain, so any record-boundary prefix is
    itself a valid chain. This models a process that died cleanly BETWEEN
    fixtures: the finished work is durable, no reservation is open and no
    terminal stop was written.
    """
    import json

    lines = source.read_text().splitlines(keepends=True)
    keep = []
    for line in lines:
        keep.append(line)
        record = json.loads(line)
        payload = record.get("payload", record)
        if payload.get("kind") == kind and payload.get("fixture") == fixture:
            break
    else:  # pragma: no cover - the event must exist
        raise AssertionError(f"{kind} for {fixture} not found in the journal")
    destination.write_text("".join(keep))
    return len(keep), len(lines)


def test_a_clean_interruption_between_fixtures_resumes_with_the_remaining_budget(tmp_path):
    """A non-terminal interruption may resume: the finished fixtures are
    reconstructed, only the unfinished ones are sent, and the time the killed
    run had already consumed is subtracted rather than handed back."""
    import shutil
    import stat as stat_module

    from qbridge.journal import DurableJournal

    clock = support.Clock()

    def slow(request):
        clock.advance(500)
        return mocks.derived_generation(request)

    handler = mocks.derived_transport(generation_plan=[slow])
    journal, provider, records_dir, orch, clock, fs = run(tmp_path, handler, clock=clock)
    orch.run()
    journal.close()
    source = tmp_path / "work" / "e9_journal.jsonl"

    resumed_work = tmp_path / "resumed"
    resumed_work.mkdir()
    resumed_journal_path = resumed_work / "e9_journal.jsonl"
    kept, total = _truncate_journal_after(
        source, resumed_journal_path, "e9_logical_finished", "F2_maximal_renderer"
    )
    assert 0 < kept < total
    resumed_journal_path.chmod(stat_module.S_IRUSR | stat_module.S_IWUSR)
    # Copy only the records the truncated prefix actually produced. The store
    # creates files exclusively (O_EXCL), so carrying across a record for a
    # fixture that never ran would make its first attempt fail retention -
    # which is the correct behaviour, but not what this test is about.
    resumed_records = support.private_dir(resumed_work / "raw")
    finished_logicals = {"_l1_", "_l2_"}
    for entry in records_dir.iterdir():
        if any(marker in entry.name for marker in finished_logicals):
            shutil.copy2(entry, resumed_records / entry.name)

    resumed_handler = mocks.derived_transport()
    resumed_clock = support.Clock()
    with DurableJournal(resumed_journal_path) as resumed:
        _provider, second, _guard = support.rebuild(
            resumed, resumed_records, resumed_handler, fs, clock=resumed_clock
        )
        outcomes = second.run()
        # Read the durable accounting while the journal is still open.
        consumed = second.consumed_seconds()
        budget = second.budget_seconds()

    assert second.refused_reason is None, "a clean partial journal may resume"
    # F1 and F2 were durable: reconstructed, not re-sent.
    assert [o.reconstructed for o in outcomes] == [True, True, False, False]
    assert [o.fixture for o in outcomes[2:]] == ["F3_repeat_of_F2", "F4_correction_no_valid_vectors"]
    assert len(resumed_handler.generation_calls) == 2, "only the unfinished fixtures are sent"
    # The killed run had already consumed 1,000 s across F1 and F2. Because
    # consumed time is recorded on every e9_logical_finished, that time is NOT
    # handed back to the resumed run even though no finish event was written.
    assert consumed >= 1000
    assert budget <= E9Limits().deadline_seconds - 1000
