"""Review finding 1: the attempt wall clock must actually bound one dispatch.

Codex's reproduction: a 2 s global deadline with a 2.25 s blocking
MockTransport generation returned after about 2.7 s and marked F1 *completed*,
because httpx timeouts are per-phase and the orchestrator called the provider
synchronously.

These tests exercise a REAL worker against a stalled and a slow transport,
assert the cancellation and the late-result rejection, and assert cleanup.
Every transport here is in-process; nothing opens a socket.
"""

from __future__ import annotations

import threading
import time

import httpx
import pytest

from e9tests import support
from qbridge_e9 import mocks
from qbridge_e9.deadline import (
    CANCEL_GRACE_SECONDS,
    DeadlineGuard,
    DeadlineNotArmed,
    MockDeadlineTransport,
    guarded_transport_factory,
)
from qbridge_e9.limits import E9Limits


class StalledTransport(httpx.BaseTransport):
    """A stand-in for a real transport blocked in a socket read.

    ``close()`` releases the block and makes the pending read fail, which is
    what closing a connection pool does to an in-flight request.
    """

    def __init__(self):
        self.release = threading.Event()
        self.entered = threading.Event()
        self.closes = 0

    def handle_request(self, request):
        self.entered.set()
        if not self.release.wait(30):  # pragma: no cover - would be a hung test
            raise AssertionError("stalled transport was never released")
        if self.closes:
            raise httpx.ReadError("connection closed by client", request=request)
        return httpx.Response(200, json={"late": True})

    def close(self):
        self.closes += 1
        self.release.set()


class LateResponseTransport(httpx.BaseTransport):
    """Returns a valid response, but only after the budget has expired."""

    def __init__(self, delay):
        self.delay = delay

    def handle_request(self, request):
        time.sleep(self.delay)
        return httpx.Response(200, json={"late": True, "value": 42})

    def close(self):
        pass


def request():
    return httpx.Request("POST", "https://example.invalid/v1/responses", json={})


# --- transport level: a real worker, cancelled and rejected ----------------


def test_a_stalled_real_transport_is_cancelled_at_the_budget():
    guard = DeadlineGuard()
    inner = StalledTransport()
    wrapped = guard.wrap(inner)
    guard.arm(0.2)
    started = time.monotonic()
    with pytest.raises(httpx.ReadTimeout):
        wrapped.handle_request(request())
    elapsed = time.monotonic() - started
    assert inner.entered.is_set()
    assert inner.closes == 1, "cancellation must close the inner transport"
    assert guard.cancellations == ["inner_transport_closed"]
    assert elapsed < 0.2 + CANCEL_GRACE_SECONDS + 1.0
    boundary = guard.drain()
    assert boundary["expiries"] and boundary["expiries"][0]["budget_seconds"] == 0.2
    assert boundary["late_results"] and boundary["late_results"][0]["accepted"] is False


def test_a_late_response_is_rejected_and_recorded_not_returned():
    guard = DeadlineGuard()
    wrapped = guard.wrap(LateResponseTransport(0.15))
    guard.arm(0.02)
    with pytest.raises(httpx.ReadTimeout):
        wrapped.handle_request(request())
    late = guard.drain()["late_results"]
    assert len(late) == 1
    assert late[0]["accepted"] is False
    # The bytes are recorded for audit even though the SDK never saw them.
    assert late[0]["kind"] in ("response", "still_running")
    if late[0]["kind"] == "response":
        assert late[0]["http_status"] == 200
        assert late[0]["body_bytes"] > 0
        assert len(late[0]["body_sha256"]) == 64


def test_a_response_inside_the_budget_is_returned_normally():
    guard = DeadlineGuard()
    wrapped = guard.wrap(LateResponseTransport(0.0))
    guard.arm(5.0)
    response = wrapped.handle_request(request())
    assert response.status_code == 200
    assert guard.drain() == {"expiries": [], "late_results": [], "cancellations": []}


def test_workers_are_daemon_threads_and_are_reported_while_alive():
    guard = DeadlineGuard()
    inner = StalledTransport()
    wrapped = guard.wrap(inner)
    guard.arm(0.05)
    with pytest.raises(httpx.ReadTimeout):
        wrapped.handle_request(request())
    # The worker thread must never be able to block interpreter exit.
    assert all(w.daemon for w in guard._workers)
    inner.release.set()
    for _ in range(100):
        if guard.workers_alive == 0:
            break
        time.sleep(0.01)
    assert guard.workers_alive == 0, "the released worker must finish and be reaped"


def test_dispatch_without_an_armed_budget_is_refused():
    guard = DeadlineGuard()
    wrapped = guard.wrap(LateResponseTransport(0.0))
    with pytest.raises(DeadlineNotArmed):
        wrapped.handle_request(request())


def test_wrapping_a_mock_transport_preserves_the_synthetic_boundary():
    """RecordingTransport.inner_is_mock must stay true, or a synthetic
    authority would be refused against its own offline transport."""
    guard = DeadlineGuard()
    wrapped = guard.wrap(httpx.MockTransport(lambda r: httpx.Response(200)))
    assert isinstance(wrapped, httpx.MockTransport)
    assert isinstance(wrapped, MockDeadlineTransport)


def test_a_mock_handler_is_not_preemptible_and_says_so():
    guard = DeadlineGuard()
    wrapped = guard.wrap(httpx.MockTransport(lambda r: (time.sleep(0.3), httpx.Response(200))[1]))
    guard.arm(0.02)
    with pytest.raises(httpx.ReadTimeout):
        wrapped.handle_request(request())
    assert guard.drain()["cancellations"] == ["mock_transport_not_preemptible"]


# --- orchestrator level: Codex's exact reproduction ------------------------


class RealClock:
    """Wall-clock monotonic time with a fixed fabricated UTC instant."""

    def __call__(self):
        return time.monotonic()

    def time(self):
        return support.WALL

    def sleep(self, seconds):
        return time.sleep(seconds)


def test_a_blocking_generation_beyond_the_deadline_is_not_marked_completed(tmp_path):
    seen = []

    def slow_generation(request_):
        seen.append(request_.extensions.get("timeout"))
        time.sleep(2.25)
        return mocks.derived_generation(request_)

    handler = mocks.derived_transport(generation_plan=[slow_generation])
    journal, _p, _r, orch, _c, _fs = support.build(
        tmp_path, handler, clock=RealClock(), limits=E9Limits(deadline_seconds=2)
    )
    started = time.monotonic()
    outcomes = orch.run()
    elapsed = time.monotonic() - started

    assert outcomes[0].outcome == "generation_failed"
    assert outcomes[0].outcome != "completed", "a late result must never be accepted"
    # The per-phase timeout the SDK saw is NOT what bounds the attempt.
    assert seen and seen[0]["read"] < 2.25
    # The run stops at the deadline plus the bounded cancellation grace window.
    assert elapsed < 2 + CANCEL_GRACE_SECONDS + 1.0
    boundary = support.events(journal, "e9_attempt_wall_clock")
    assert len(boundary) == 1
    assert boundary[0]["request_class"] == "generation"
    assert boundary[0]["late_results_rejected"], "the late result must be recorded as rejected"
    assert all(entry["accepted"] is False for entry in boundary[0]["late_results_rejected"])
    # The armed budget is min(300 s attempt timeout, remaining deadline); the
    # count attempt already consumed part of the 2 s, so it is strictly less.
    armed = boundary[0]["expiries"][0]["budget_seconds"]
    assert 0 < armed < 2
    assert armed == pytest.approx(boundary[0]["armed_budget_seconds"])
    journal.close()


def test_the_orchestrator_refuses_to_run_without_an_enforceable_wall_clock(tmp_path):
    handler = mocks.derived_transport()
    journal, provider, records_dir, _orch, clock, fs = support.build(tmp_path, handler)
    from qbridge_e9.orchestrator import E9Orchestrator

    unguarded = E9Orchestrator(
        journal=journal,
        provider=provider,
        fixture_set=fs,
        records_dir=records_dir,
        clock=clock,
        sleep=clock.sleep,
        deadline_guard=None,
    )
    outcomes = unguarded.run()
    assert unguarded.refused_reason == "attempt_wall_clock_not_enforceable"
    assert [o.outcome for o in outcomes] == ["refused"] * 4
    assert handler.count_calls == [] and handler.generation_calls == []
    journal.close()


def test_the_guarded_factory_arms_every_dispatch(tmp_path):
    guard = DeadlineGuard()
    factory = guarded_transport_factory(
        lambda: httpx.MockTransport(lambda r: httpx.Response(200)), guard
    )
    first, second = factory(), factory()
    assert first is not second, "a fresh transport per attempt, so closing one is safe"
    assert isinstance(first, MockDeadlineTransport)
