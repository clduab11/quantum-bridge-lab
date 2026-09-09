"""Wall-clock enforcement for ONE provider attempt.

Why this exists (review finding 1). ``httpx`` timeouts are per-phase
(``connect``/``read``/``write``/``pool``); none of them bounds the total time a
single dispatch may take. A slow-drip server, or a synchronous in-process
handler, can therefore exceed the 300 s attempt boundary that protocol v0.4 and
amendment A1.11 fix, and the orchestrator would accept the late result.

This module enforces the boundary at the only place bytes can leave: the
transport. One dispatch runs in a daemon worker thread with a total wall-clock
budget armed by the orchestrator. At expiry the guard

1. **cancels** by closing the inner transport, which aborts an in-flight socket
   read on a real ``httpx.HTTPTransport``;
2. waits a short fixed grace window for the cancellation to surface;
3. **rejects any late result** - a response that arrives after expiry is
   discarded, never returned to the SDK, and its status, byte length and digest
   are recorded so the audit trail still shows what came back; and
4. raises ``httpx.ReadTimeout``, which the reviewed provider classifies as an
   ordinary attempt timeout: the money reservation is retained as
   unknown-dispatched and the orchestrator applies the predetermined retry rule.

Honest limit: a *synchronous in-process* handler (``httpx.MockTransport`` with a
blocking body) cannot be preempted by any means available to CPython - there is
no safe way to interrupt arbitrary synchronous code in another thread. For that
case only steps 2-4 apply: the orchestrator observes the deadline exactly and
the late result is refused, but the worker thread runs to completion in the
background. It is a daemon thread, so it never blocks interpreter exit, and
``DeadlineGuard.workers_alive`` reports any that are still running.

The wrapper preserves the provider's synthetic/real boundary. A mock inner
transport is wrapped in a subclass of ``httpx.MockTransport``, so
``RecordingTransport.inner_is_mock`` - the check that refuses a synthetic
authority against a real transport and a real authority against a mock - is
unchanged.
"""

from __future__ import annotations

import hashlib
import threading
import time

import httpx

CANCEL_GRACE_SECONDS = 0.25


class DeadlineNotArmed(RuntimeError):
    """A dispatch was attempted without an armed wall-clock budget."""


class _DeadlineDispatch:
    """Shared wall-clock enforcement. Mixed into both transport flavours."""

    _guard: DeadlineGuard

    def _dispatch_with_deadline(self, request, dispatch):
        guard = self._guard
        budget = guard.take_budget()
        started = guard.clock()
        box: dict = {}
        done = threading.Event()

        def work():
            try:
                box["response"] = dispatch(request)
            except BaseException as exc:  # noqa: BLE001 - re-raised in the caller
                box["error"] = exc
            finally:
                done.set()

        worker = threading.Thread(target=work, name="e9-attempt", daemon=True)
        guard.register(worker)
        worker.start()

        remaining = budget - (guard.clock() - started)
        if not done.wait(max(remaining, 0.0)):
            guard.record_expiry(budget=budget, elapsed=guard.clock() - started)
            self._cancel()
            done.wait(CANCEL_GRACE_SECONDS)
            guard.record_late(box)
            raise httpx.ReadTimeout(
                "e9 attempt wall-clock budget exceeded; result rejected", request=request
            )
        if "error" in box:
            raise box["error"]
        return box["response"]

    def _cancel(self):
        raise NotImplementedError


class DeadlineTransport(_DeadlineDispatch, httpx.BaseTransport):
    """Deadline enforcement around a real transport. Cancels by closing it."""

    def __init__(self, inner: httpx.BaseTransport, guard: DeadlineGuard):
        self._inner = inner
        self._guard = guard

    def handle_request(self, request):
        return self._dispatch_with_deadline(request, self._inner.handle_request)

    def _cancel(self):
        try:
            self._inner.close()
            self._guard.record_cancel("inner_transport_closed")
        except Exception as exc:  # noqa: BLE001 - cancellation is best effort
            self._guard.record_cancel(f"close_failed:{type(exc).__name__}")

    def close(self):
        self._inner.close()


class MockDeadlineTransport(_DeadlineDispatch, httpx.MockTransport):
    """Deadline enforcement that still IS an ``httpx.MockTransport``.

    Subclassing keeps ``RecordingTransport.inner_is_mock`` true, so the
    provider's synthetic-authority boundary behaves exactly as reviewed.
    """

    def __init__(self, handler, guard: DeadlineGuard):
        super().__init__(handler)
        self._guard = guard

    def handle_request(self, request):
        return self._dispatch_with_deadline(
            request, lambda req: httpx.MockTransport.handle_request(self, req)
        )

    def _cancel(self):
        # A synchronous in-process handler is not preemptible; only the late
        # result is rejected. Recorded explicitly so no audit reader assumes
        # the work was actually stopped.
        self._guard.record_cancel("mock_transport_not_preemptible")


class DeadlineGuard:
    """Arms a per-attempt budget and collects what happened at the boundary."""

    def __init__(self, clock=time.monotonic):
        self.clock = clock
        self._budget = None
        self._workers = []
        self.expiries = []
        self.late_results = []
        self.cancellations = []

    # -- orchestrator side ------------------------------------------------
    def arm(self, budget_seconds):
        if not isinstance(budget_seconds, (int, float)) or budget_seconds <= 0:
            raise ValueError("attempt budget must be a positive number of seconds")
        self._budget = float(budget_seconds)

    def disarm(self):
        self._budget = None

    def drain(self):
        """Return and clear the boundary observations for one attempt."""
        record = {
            "expiries": list(self.expiries),
            "late_results": list(self.late_results),
            "cancellations": list(self.cancellations),
        }
        self.expiries.clear()
        self.late_results.clear()
        self.cancellations.clear()
        return record

    @property
    def workers_alive(self):
        return sum(1 for w in self._workers if w.is_alive())

    def wrap(self, inner):
        if isinstance(inner, httpx.MockTransport):
            return MockDeadlineTransport(inner.handler, self)
        return DeadlineTransport(inner, self)

    # -- transport side ---------------------------------------------------
    def take_budget(self):
        if self._budget is None:
            raise DeadlineNotArmed("the orchestrator must arm a budget before every dispatch")
        return self._budget

    def register(self, worker):
        self._workers = [w for w in self._workers if w.is_alive()]
        self._workers.append(worker)

    def record_expiry(self, *, budget, elapsed):
        self.expiries.append({"budget_seconds": budget, "elapsed_seconds": elapsed})

    def record_cancel(self, action):
        self.cancellations.append(action)

    def record_late(self, box):
        if "response" in box:
            response = box["response"]
            try:
                body = response.read()
            except Exception:  # noqa: BLE001 - a late body may be unreadable
                body = b""
            self.late_results.append(
                {
                    "kind": "response",
                    "http_status": getattr(response, "status_code", None),
                    "body_bytes": len(body),
                    "body_sha256": hashlib.sha256(body).hexdigest(),
                    "accepted": False,
                }
            )
        elif "error" in box:
            self.late_results.append(
                {"kind": "error", "error": type(box["error"]).__name__, "accepted": False}
            )
        else:
            self.late_results.append({"kind": "still_running", "accepted": False})


def guarded_transport_factory(inner_factory, guard: DeadlineGuard):
    """The transport_factory the provider must be constructed with."""

    def factory():
        return guard.wrap(inner_factory())

    return factory
