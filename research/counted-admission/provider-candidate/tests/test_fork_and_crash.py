"""Real sequential qbridge.runner.ProcessExecutor children: every dispatch runs in a
forked worker whose memory is discarded. Only the journal and the raw record
directory carry state. MockTransport only; constant objective; no network."""

import os

import httpx
from support import (
    Clock,
    Fabricated,
    events,
    gen_ok,
    make_provider,
    make_runner,
    response_object,
    run,
    usage,
)

from counted_responses_provider import contract as C
from counted_responses_provider.authority import parse_utc
from counted_responses_provider.provider import seed_identity_baseline
from qbridge.journal import DurableJournal
from qbridge.runner import ProcessExecutor

BASELINE = C.identity_vector(response_object())
REQUEST = {"system": "s", "user": "u", "max_tokens": 8192}


def seeded(log):
    seed_identity_baseline(
        log,
        vector=BASELINE,
        source="FABRICATED E9 acceptance record (test only)",
        accepted_from_e9=True,
    )


def halts(log):
    return [(e["reason"], e["inferential_failure"]) for e in events(log, "provider_halted")]


def raw_names(tmp_path):
    return sorted(p.name for p in (tmp_path / "raw").iterdir())


def test_identical_responses_in_successive_children_and_after_reopen_never_false_halt(tmp_path):
    with DurableJournal(tmp_path / "j") as log:
        seeded(log)
        handler = Fabricated()
        provider, _, clock = make_provider(tmp_path, log, handler)
        runner = make_runner(log, clock, executor=ProcessExecutor())
        runner.initialize([[0.0] * 20] * 10)
        for batch in (1, 2, 3):
            assert runner._logical(provider, REQUEST, batch, 1) == "good"
        assert not handler.requests  # children's memory never reaches the parent
        attempts = events(log, "provider_attempt")
        assert [a["category"] for a in attempts] == ["count_ok", "received_completed"] * 3
        assert all(
            a["metadata"]["identity_findings"] == []
            for a in attempts
            if a["request_class"] == "generation"
        )
        assert len(raw_names(tmp_path)) == 18
        assert not halts(log)
    with DurableJournal(tmp_path / "j") as log:  # close/reopen: baseline read back from JSON
        (tmp_path / "second").mkdir()
        provider, _, clock = make_provider(tmp_path / "second", log, Fabricated())
        runner = make_runner(log, clock, block=1, executor=ProcessExecutor())
        runner.initialize([[0.0] * 20] * 10)
        assert runner._logical(provider, REQUEST, 1, 1) == "good"
        assert not halts(log)
        assert provider.ledger.summary()["attempts"] == {"count": 4, "generation": 4}


def test_child_ivf_halt_survives_fork_and_blocks_the_next_block(tmp_path):
    with DurableJournal(tmp_path / "j") as log:
        seeded(log)
        drift = Fabricated(generation=lambda r: gen_ok(usage_obj=usage(cached=3)))
        provider, _, clock = make_provider(tmp_path, log, drift)
        result = run(make_runner(log, clock, executor=ProcessExecutor()), provider)
        assert result["ivf"] and result["forfeits"] == 190 and result["valid_evaluations"] == 10
        assert halts(log) == [("ivf_halt:cache_activity:cached_tokens=3", True)]
        assert len(raw_names(tmp_path)) == 6  # one count + one generation, three files each
        next_runner = make_runner(log, Clock(), block=1, executor=ProcessExecutor())
        (tmp_path / "next").mkdir()
        provider2, _, _ = make_provider(tmp_path / "next", log, Fabricated())
        result2 = run(next_runner, provider2)
        assert result2["forfeits"] == 190 and result2["ivf"]
        assert not events(log, "provider_dispatch_intent")[2:]  # no further dispatch intent
        assert raw_names(tmp_path / "next") == []


def test_child_killed_after_request_retention_keeps_reservation_open(tmp_path):
    """STRICT. Known failure on macOS, reproduced BOTH in the Claude Science sandbox and by
    Codex in the authorized local 3.11.15 environment (112 passed / 1 failed, 34.04 s), so it
    is a core-runner defect, not a sandbox artifact. Recorded, not weakened:
    qbridge/runner.py ProcessExecutor._run, `finally` block, os.killpg(process.pid,
    signal.SIGKILL) raises PermissionError [Errno 1] EPERM when the child exited via
    os._exit(1) without sending a result (received=False, so process.join is skipped and
    the child is an unreaped zombie whose setsid() group has no signalable member). Only
    ProcessLookupError is caught there, so WorkerCrashed is masked and the runner records
    provider_client_error instead of recovering with transport_interruption. Minimal
    reproduction: ProcessExecutor().call(lambda: os._exit(1), timeout=10). Codex owns the
    core correction (abrupt-exit and descendant-cleanup regressions) and will rerun this test
    unchanged; the cloned core in this package's build was not patched."""

    def die(request):
        # The request bytes are already retained and the money reservation journaled.
        os._exit(1)

    with DurableJournal(tmp_path / "j") as log:
        seeded(log)
        provider, _, clock = make_provider(tmp_path, log, Fabricated(count=die))
        result = run(make_runner(log, clock, executor=ProcessExecutor()), provider)
        assert result["closed"] and result["forfeits"] == 190
        assert raw_names(tmp_path) == ["AI_b0_bt1_l1_count_a1.request.json"]
        reserved = events(log, "money_reserved")
        assert len(reserved) == 1 and not events(log, "money_settled")
        state = provider.ledger.state()
        assert state["open"] == [reserved[0]["money_reservation"]]
        assert state["committed"] == provider.authority.count_fee_ceiling()
        intents = events(log, "provider_dispatch_intent")
        assert (
            len(intents) == 1
            and intents[0]["transport_reservation"] == "transport:AI:0:1:1:count:1"
        )
        # the runner's own transport reservation is unresolved too
        counts = log.read_events()
        completed = {e["reservation"] for e in counts if e["kind"] == "completed"}
        assert "transport:AI:0:1:1:count:1" not in completed
        # a fresh block still carries the open reservation against the ceiling
        (tmp_path / "next").mkdir()
        provider2, _, _ = make_provider(tmp_path / "next", log, Fabricated())
        assert provider2.ledger.state()["committed"] == provider.authority.count_fee_ceiling()
        assert not halts(log)


def test_child_halt_persisted_before_return_overrides_apparent_success(tmp_path):
    """A child that persists a stricter halt during dispatch must not have its
    received text accepted under the accounting exception."""

    def inconsistent_then_stricter_halt(request):
        # Fabricates a durable IVF finding appearing during this attempt, then an
        # object whose only own finding is an inconsistent total.
        with DurableJournal(tmp_path / "j") as child_log:  # noqa: F841 - lock is inherited
            pass
        return gen_ok(usage_obj=usage(total=1))

    with DurableJournal(tmp_path / "j") as log:
        seeded(log)

        def handler(request):
            if request.url.path.endswith("/input_tokens"):
                return Fabricated().count(request)
            log.append(
                "provider_halted", reason="fabricated_stricter_halt", inferential_failure=True
            )
            return gen_ok(usage_obj=usage(total=1))

        provider, _, clock = make_provider(tmp_path, log, handler)
        result = run(make_runner(log, clock, executor=ProcessExecutor()), provider)
        assert result["ivf"] and result["valid_evaluations"] == 10 and result["forfeits"] == 190
        attempt = [
            a for a in events(log, "provider_attempt") if a["request_class"] == "generation"
        ][0]
        assert attempt["category"] == "received_completed"
        reasons = [r for r, _ in halts(log)]
        assert reasons[0] == "fabricated_stricter_halt"
        assert "accounting_halt" not in reasons  # weaker finding never overrode the stricter halt


def test_price_expiry_between_attempts_is_checked_in_the_child(tmp_path):
    with DurableJournal(tmp_path / "j") as log:
        seeded(log)
        provider, _, clock = make_provider(
            tmp_path, log, Fabricated(count=lambda r: httpx.Response(500, json={}))
        )
        runner = make_runner(log, clock, executor=ProcessExecutor())
        runner.initialize([[0.0] * 20] * 10)
        # advance the fabricated wall clock past validity after initialization; the
        # child re-reads it before dispatch
        clock.wall = (
            min(
                parse_utc(provider.authority.price_valid_through_utc),
                parse_utc(provider.authority.count_fee_valid_through_utc),
            )
            + 1.0
        )
        assert clock.wall > parse_utc(provider.authority.recorded_at_utc)
        runner._logical(provider, REQUEST, 1, 1)
        assert halts(log) == [("price_validity_expired", False)]
        assert not events(log, "provider_dispatch_intent") and raw_names(tmp_path) == []
