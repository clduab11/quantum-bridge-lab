"""Offline-preflight runner with injected objectives and transport callbacks.

There is deliberately no study objective, provider adapter, or full-study
command here. The POSIX process executor is for a single-threaded command-line
process. Its whole-arm guard keeps stateful CMA ask/tell in one worker and kills
that worker's process group on deadline. InlineExecutor is for synthetic clocks
and fixtures only; it makes no hard-cancellation claim.
"""

from __future__ import annotations

import copy
import math
import multiprocessing
import numbers
import os
import signal
import threading
import time
from dataclasses import dataclass, field
from multiprocessing.connection import wait

import numpy as np

from .journal import DurableJournal, JournalCorrupt

ARM_SECONDS = 36000.0
ATTEMPT_SECONDS = 300.0
TAU_MAP = 16 * 2**-52


class ArmClosed(RuntimeError):
    """This arm has ended and must never be resumed or replayed."""


class WorkerCrashed(RuntimeError):
    """Worker exited without returning a durable-observable completion."""


class RemoteError(RuntimeError):
    """A callback raised an ordinary exception in a worker."""


class _GuardCancelled(BaseException):
    pass


def _cancel_guard(_signum, _frame):
    # Unwind the guard's active ProcessExecutor.call first, killing that call's
    # separate process group before the guard itself is forcibly collected.
    raise _GuardCancelled()


@dataclass(frozen=True)
class TransportResponse:
    status: int
    text: str
    metadata: dict = field(default_factory=dict)
    usage: dict | None = None


class InlineExecutor:
    """Synthetic-only executor for deterministic fixtures and fake clocks."""

    def call(self, work, *, timeout):
        if timeout <= 0:
            raise TimeoutError("deadline expired")
        return work()

    def guard(self, work, *, timeout):
        return self.call(work, timeout=timeout)


def _worker(send, receive, work, guard, callback_group, expected_parent):
    receive.close()
    os.setsid()
    if not guard and callback_group is not None:
        # Publish before external work. The surviving outer guard owner can
        # collect this group even if the immediate parent is killed abruptly.
        callback_group.value = os.getpid()
        if os.getppid() != expected_parent:
            os._exit(1)
    signal.signal(signal.SIGTERM, _cancel_guard if guard else signal.SIG_DFL)
    try:
        try:
            result = work()
        except Exception as exc:
            send.send(("error", type(exc).__name__, str(exc)))
        else:
            send.send(("ok", result))
    finally:
        send.close()


class ProcessExecutor:
    """Killable POSIX callback execution, plus a group guard for whole arms.

    Each callback has its own process group, including its nondetached children.
    A guard's SIGTERM handler unwinds the active callback executor, cancelling
    that group before the guard's group is collected. A shared single-callback
    PID also lets the outer owner collect it after an abrupt guard crash.
    Callbacks must not detach themselves or create sessions. This executor is not a provider-side
    cancellation guarantee for requests already accepted by an external service.
    """

    def __init__(self):
        self._callback_group = None

    def call(self, work, *, timeout):
        return self._run(work, timeout=timeout, guard=False)

    def guard(self, work, *, timeout):
        return self._run(work, timeout=timeout, guard=True)

    def _run(self, work, *, timeout, guard):
        if not math.isfinite(timeout):
            raise ValueError("worker timeout must be finite")
        if timeout <= 0:
            raise TimeoutError("deadline expired")
        if os.name != "posix" or threading.active_count() != 1:
            raise RuntimeError("process executor requires a single-threaded POSIX caller")
        context = multiprocessing.get_context("fork")
        previous_group = self._callback_group
        if guard:
            self._callback_group = context.RawValue("q", 0)
        callback_group = self._callback_group
        receive, send = context.Pipe(duplex=False)
        process = context.Process(
            target=_worker, args=(send, receive, work, guard, callback_group, os.getpid())
        )
        started = time.monotonic()
        process.start()
        send.close()
        received = False
        try:
            while True:
                remaining = max(0.0, timeout - (time.monotonic() - started))
                ready = wait([receive, process.sentinel], timeout=min(remaining, 0.05))
                if ready:
                    break
                # A forked descendant can inherit both pipes and hold them
                # open after the worker exits. Poll waitpid via exitcode so
                # that inherited descriptors cannot delay crash cleanup.
                if process.exitcode is not None:
                    raise WorkerCrashed("worker exited before returning a result")
                if time.monotonic() - started >= timeout:
                    raise TimeoutError("worker deadline expired")
            if receive not in ready:
                raise WorkerCrashed("worker exited before returning a result")
            try:
                message = receive.recv()
                received = True
            except EOFError as exc:
                raise WorkerCrashed("worker returned no result") from exc
            if message[0] == "ok":
                return message[1]
            exception = {"ConnectionError": ConnectionError, "TimeoutError": TimeoutError}.get(
                message[1], RemoteError
            )
            raise exception(message[2])
        finally:
            receive.close()
            # A result proves the callback has returned. Let the worker exit
            # normally instead of racing killpg against a disappearing group.
            if received:
                process.join(timeout=0.1)
            elif guard and process.is_alive():
                # The guard can be waiting on a callback in another group.
                # Its handler unwinds that call and performs group cleanup.
                process.terminate()
                process.join(timeout=0.5)
            # Reap an already-exited worker even when it sent no result. On
            # macOS, signalling its unreaped group can raise EPERM and mask
            # WorkerCrashed. Still signal the group to collect descendants.
            process.join(timeout=0)
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            if process.is_alive():
                process.kill()
            process.join(timeout=1.0)
            if process.is_alive():
                process.kill()
                process.join(timeout=1.0)
            if guard and callback_group.value:
                # Reap the guard first, so it cannot create another callback
                # after we inspect its published group. A child that publishes
                # later detects its missing parent and exits before work.
                try:
                    os.killpg(callback_group.value, signal.SIGKILL)
                except ProcessLookupError:
                    pass
            elif not guard and callback_group is not None:
                callback_group.value = 0
            process.close()
            if guard:
                self._callback_group = previous_group


def _raw_vector(raw):
    try:
        entries = list(raw)
    except TypeError as exc:
        raise ValueError("raw vector is not iterable") from exc
    if len(entries) != 20:
        raise ValueError("raw vector must have 20 entries")
    if any(isinstance(x, (bool, np.bool_)) or not isinstance(x, numbers.Real) for x in entries):
        raise ValueError("raw vector must contain real numbers, not booleans")
    try:
        result = tuple(float(x) for x in entries)
    except (OverflowError, ValueError) as exc:
        raise ValueError("raw vector cannot convert to float64") from exc
    if not all(math.isfinite(x) for x in result):
        raise ValueError("raw vector contains non-finite values")
    return result


class ArmRunner:
    """One 200-slot arm of one block. All endpoints derive from durable logs.

    Instantiate before initialization/optimizer setup so their elapsed time is
    within the arm's deadline. Reopening an interrupted arm recovers accounting
    and forfeits untouched slots; it never resumes the algorithm. A completed
    instance may be inspected via history()/summary(), but cannot run again.
    """

    def __init__(
        self,
        journal: DurableJournal,
        *,
        block: int,
        arm: str,
        objective,
        map_action,
        clock=time.monotonic,
        sleep=time.sleep,
        executor=None,
        input_token_limit=None,
        count_input_tokens=None,
        expected_identity=None,
    ):
        if isinstance(block, bool) or not isinstance(block, int) or not 0 <= block < 40:
            raise ValueError("block must be 0 through 39")
        if arm not in {"AI", "CMA", "RS"}:
            raise ValueError("arm must be AI, CMA or RS")
        self.journal = journal
        self.block, self.arm = block, arm
        self.objective, self.map_action = objective, map_action
        self.clock, self.sleep = clock, sleep
        self.executor = executor if executor is not None else ProcessExecutor()
        self.input_token_limit, self.count_input_tokens = input_token_limit, count_input_tokens
        self.expected_identity = copy.deepcopy(expected_identity)
        events = self._events()
        starts = [e for e in events if e["kind"] == "arm_started"]
        if starts:
            self.started = starts[0]["started"]
            self.deadline = self.started + ARM_SECONDS
            if not self.closed:
                self._recover("interruption")
        else:
            self.started = self.clock()
            self.deadline = self.started + ARM_SECONDS
            self._event("arm_started", started=self.started, executor=type(self.executor).__name__)

    def _events(self):
        return [
            e
            for e in self.journal.read_events()
            if e.get("block") == self.block and e.get("arm") == self.arm
        ]

    def _event(self, kind, **fields):
        return self.journal.append(kind, block=self.block, arm=self.arm, **fields)

    @property
    def closed(self):
        return any(e["kind"] == "arm_finished" for e in self._events())

    def _remaining(self):
        return max(0.0, self.deadline - self.clock())

    def _allocated(self):
        return {
            e["slot"]
            for e in self._events()
            if e["kind"] == "slot_forfeited"
            or (e["kind"] == "reserved" and e.get("resource") == "objective")
        }

    def _forfeit(self, slots, reason):
        allocated = self._allocated()
        for slot in slots:
            if slot not in allocated:
                self._event("slot_forfeited", slot=slot, reason=reason)
                allocated.add(slot)

    def _flag(self, flag, reason):
        self._event(flag, reason=reason)

    def _finish(self, reason):
        if self.closed:
            return
        self._forfeit(range(1, 201), reason)
        if self.journal.resource_counts(block=self.block, arm=self.arm)[
            "unresolved_objective_reservations"
        ]:
            self._flag("svf", "unresolved_objective_reservation")
        if not self.history():
            self._flag("svf", "undefined_endpoint")
        self._event("arm_finished", reason=reason, elapsed=max(0.0, self.clock() - self.started))

    def _recover(self, reason):
        counts = self.journal.resource_counts(block=self.block, arm=self.arm)
        if counts["unresolved_objective_reservations"]:
            self._flag("svf", "unresolved_objective_reservation")
        self._finish(reason)

    def _live(self):
        if self.closed:
            return False
        if self._remaining() <= 0:
            self._recover("deadline")
            return False
        return True

    def _guarded(self, work):
        if self.closed:
            raise ArmClosed("arm is closed; no replay permitted")
        if not self._live():
            return self.summary()
        try:
            self.executor.guard(work, timeout=self._remaining())
        except TimeoutError:
            self._recover("deadline")
        except WorkerCrashed:
            self._recover("interruption")
        except (KeyboardInterrupt, SystemExit):
            self._recover("interruption")
            raise
        except JournalCorrupt:
            raise
        except Exception as exc:
            self._event("algorithm_exception", error=type(exc).__name__, message=str(exc))
            self._finish("algorithm_exception")
        return self.summary()

    def history(self):
        return [
            {"index": e["slot"], "theta": list(e["theta"]), "value": e["value"]}
            for e in self._events()
            if e["kind"] == "completed"
            and e.get("resource") == "objective"
            and e.get("status") == "valid"
        ]

    def summary(self):
        events = self._events()
        history = self.history()
        best = min(history, key=lambda row: (row["value"], row["index"])) if history else None
        counts = self.journal.resource_counts(block=self.block, arm=self.arm)
        return {
            "block": self.block,
            "arm": self.arm,
            "allotted_slots": 200,
            "endpoint": best["value"] if best else None,
            "best_index": best["index"] if best else None,
            "valid_evaluations": len(history),
            "forfeits": sum(e["kind"] == "slot_forfeited" for e in events),
            "simulator_invalid": sum(
                e["kind"] == "completed" and e.get("status") == "simulator_invalid" for e in events
            ),
            "mapping_failures": sum(
                e["kind"] == "completed"
                and e.get("invoked") is False
                and e.get("resource") == "objective"
                for e in events
            ),
            "logical_calls": sum(e["kind"] == "logical_started" for e in events),
            "duplicates": sum(
                e["kind"] == "completed" and e.get("duplicate", False) for e in events
            ),
            "svf": any(e["kind"] == "svf" for e in events),
            "ivf": any(e["kind"] == "ivf" for e in events),
            "closed": self.closed,
            **counts,
        }

    def _evaluate(self, raw, slot):
        if not self._live():
            return None
        raw = _raw_vector(raw)
        reservation = self.journal.reserve(
            "objective",
            f"{self.arm}:{self.block}:{slot}",
            block=self.block,
            arm=self.arm,
            slot=slot,
            raw=list(raw),
        )
        try:
            theta = np.asarray(self.map_action(raw), dtype=np.float64)
            if theta.shape != (20,) or not np.all(np.isfinite(theta)):
                raise ValueError("mapper returned invalid shape or nonfinite component")
            norms = np.hypot(theta[::2], theta[1::2])
            if np.any(norms > 1 + TAU_MAP):
                raise ValueError("mapped norm exceeds tolerance")
        except Exception as exc:
            self.journal.complete(
                reservation,
                status="simulator_invalid",
                invoked=False,
                error="mapping_failure",
                message=str(exc),
            )
            self._flag("svf", "mapping_failure")
            return None
        overshoots = [
            {"segment": int(k), "norm": float(norms[k])} for k in np.flatnonzero(norms > 1)
        ]
        if overshoots:
            self._event("mapping_norm_overshoots", slot=slot, overshoots=overshoots)
        # Compare every confirmed evaluation, including simulator-invalid
        # values, by binary64 image (and signed-zero bits). Unresolved
        # reservations do not establish that evaluation occurred.
        bits = theta.tobytes()
        duplicate = any(
            np.asarray(event["theta"], dtype=np.float64).tobytes() == bits
            for event in self._events()
            if event["kind"] == "completed"
            and event.get("resource") == "objective"
            and event.get("invoked") is True
            and "theta" in event
        )
        try:
            value = self.executor.call(lambda: self.objective(theta), timeout=self._remaining())
        except (TimeoutError, WorkerCrashed):
            # No completion is invented: execution may have begun or not.
            self._flag("svf", "unresolved_objective_reservation")
            self._finish("objective_interruption")
            return None
        except Exception as exc:
            self.journal.complete(
                reservation,
                status="simulator_invalid",
                invoked=True,
                raw=list(raw),
                theta=theta.tolist(),
                duplicate=duplicate,
                error=type(exc).__name__,
                message=str(exc),
            )
            self._flag("svf", "simulator_exception")
            return None
        try:
            if isinstance(value, (bool, np.bool_)) or not isinstance(value, numbers.Real):
                raise ValueError("objective result is not a real scalar")
            value = float(value)
            valid = math.isfinite(value) and 0 <= value <= 1
        except (ValueError, TypeError, OverflowError):
            valid = False
        expired = self._remaining() <= 0
        if not valid or expired:
            self.journal.complete(
                reservation,
                status="simulator_invalid",
                invoked=True,
                raw=list(raw),
                theta=theta.tolist(),
                duplicate=duplicate,
                error="deadline" if expired else "invalid_value",
            )
            self._flag("svf", "objective_deadline" if expired else "invalid_value")
            if expired:
                self._finish("deadline")
            return None
        value = float(value)
        self.journal.complete(
            reservation,
            status="valid",
            invoked=True,
            raw=list(raw),
            theta=theta.tolist(),
            value=value,
            duplicate=duplicate,
        )
        return value

    def initialize(self, raw_vectors):
        def work():
            if self._allocated():
                raise ArmClosed("initialization already consumed slots")
            actions = list(raw_vectors)
            if len(actions) != 10:
                raise ValueError("initialization requires ten actions")
            for slot, action in enumerate(actions, 1):
                self._evaluate(action, slot)
                if self.closed:
                    return
            if self.history():
                self._event("initialized")
            else:
                self._finish("zero_valid_initialization")

        return self._guarded(work)

    def _ready(self, expected_arm):
        if self.arm != expected_arm:
            raise ValueError(f"method requires arm {expected_arm}")
        if not any(e["kind"] == "initialized" for e in self._events()):
            raise ValueError("initialize the arm before optimizer work")

    def run_random(self, raw_vectors):
        self._ready("RS")

        def work():
            actions = iter(raw_vectors)
            for slot in range(11, 201):
                if not self._live():
                    return
                self._evaluate(next(actions), slot)
            self._finish("completed")

        return self._guarded(work)

    def run_cma(self, optimizer):
        self._ready("CMA")

        def work():
            for generation in range(1, 20):
                if not self._live():
                    return
                samples = optimizer.ask()
                if len(samples) != 10:
                    raise ValueError("CMA ask returned wrong generation size")
                for raw in samples:
                    _raw_vector(raw)
                values = []
                for j, raw in enumerate(samples):
                    value = self._evaluate(raw, 10 * generation + j + 1)
                    if value is None:
                        self._finish("incomplete_cma_generation")
                        return
                    values.append(value)
                optimizer.tell(samples, values)
                self._event(
                    "cma_generation",
                    generation=generation,
                    stop_conditions=_json_ready(optimizer.stop()),
                )
            self._finish("completed")

        return self._guarded(work)

    def _logical(self, transport, request, batch, logical):
        self._event("logical_started", batch=batch, logical=logical, request=request)
        if self.input_token_limit is None or self.count_input_tokens is None:
            raise ValueError(
                "an input-token counter and ceiling are required even for a mocked LLM"
            )
        length = self.count_input_tokens(request)
        if (
            isinstance(length, bool)
            or not isinstance(length, int)
            or not 0 <= length <= self.input_token_limit
        ):
            self._event(
                "request_not_sent", batch=batch, logical=logical, reason="input_token_ceiling"
            )
            return None
        for attempt in range(1, 4):
            if not self._live():
                return None
            reservation = self.journal.reserve(
                "transport",
                f"{self.arm}:{self.block}:{batch}:{logical}:{attempt}",
                block=self.block,
                arm=self.arm,
                batch=batch,
                logical=logical,
                attempt=attempt,
                request=request,
            )
            timeout = min(ATTEMPT_SECONDS, self._remaining())
            try:
                response = self.executor.call(
                    lambda: transport(copy.deepcopy(request), timeout), timeout=timeout
                )
            except TimeoutError:
                self._event("attempt_timeout", reservation=reservation)
                retry = True
            except ConnectionError as exc:
                self.journal.complete(
                    reservation,
                    status="connection_error",
                    dispatched=None,
                    usage=None,
                    message=str(exc),
                )
                retry = True
            except WorkerCrashed:
                self._recover("transport_interruption")
                return None
            except Exception as exc:
                self.journal.complete(
                    reservation,
                    status="client_error",
                    dispatched=None,
                    usage=None,
                    error=type(exc).__name__,
                    message=str(exc),
                )
                return None
            else:
                if not isinstance(response, TransportResponse):
                    self.journal.complete(
                        reservation,
                        status="client_error",
                        dispatched=None,
                        usage=None,
                        error="invalid_transport_response",
                    )
                    return None
                self.journal.complete(
                    reservation,
                    status="response",
                    dispatched=True,
                    http_status=response.status,
                    text=response.text,
                    metadata=response.metadata,
                    usage=response.usage,
                )
                if not self._live():
                    return None
                if 200 <= response.status < 300:
                    if self.expected_identity is not None and any(
                        response.metadata.get(key) != value
                        for key, value in self.expected_identity.items()
                    ):
                        self._flag("ivf", "model_or_decoding_change")
                    relevant = {
                        "model",
                        "fingerprint",
                        "system_fingerprint",
                        "decoding",
                        "effective_decoding",
                    }
                    prior_identity = {}
                    for event in self.journal.read_events():
                        if (
                            event["kind"] == "completed"
                            and event.get("resource") == "transport"
                            and 200 <= event.get("http_status", 0) < 300
                        ):
                            for key, value in event.get("metadata", {}).items():
                                if key in relevant and value is not None:
                                    prior_identity.setdefault(key, value)
                    if any(
                        key in prior_identity and value is not None and value != prior_identity[key]
                        for key, value in response.metadata.items()
                        if key in relevant
                    ):
                        self._flag("ivf", "reported_identity_change")
                    return response.text
                retry = response.status == 429 or 500 <= response.status < 600
            if not retry or attempt == 3:
                return None
            if not self._live():
                return None
            self.sleep(min((5.0, 20.0)[attempt - 1], self._remaining()))
        return None

    def run_llm(self, transport, *, parse_response, render_user, system_prompt):
        self._ready("AI")

        def work():
            system = system_prompt()
            for batch in range(1, 20):
                if not self._live():
                    return
                user = render_user(self.history(), batch)
                request = {"system": system, "user": user, "max_tokens": 8192}
                text = self._logical(transport, request, batch, 1)
                parsed = None
                if text is not None:
                    parsed = parse_response(text)
                    self._event(
                        "parsed_response",
                        batch=batch,
                        logical=1,
                        valid_count=parsed.valid_count,
                        schema_valid=parsed.schema_valid,
                        reason=parsed.reason,
                        validity=[v is not None for v in parsed.vectors],
                    )
                    if parsed.valid_count == 0:
                        correction = {
                            **request,
                            "user": user
                            + "\nPREVIOUS RESPONSE REJECTED: "
                            + parsed.reason
                            + ". Respond again following the output rules exactly.",
                        }
                        text = self._logical(transport, correction, batch, 2)
                        parsed = parse_response(text) if text is not None else None
                        if parsed is not None:
                            self._event(
                                "parsed_response",
                                batch=batch,
                                logical=2,
                                valid_count=parsed.valid_count,
                                schema_valid=parsed.schema_valid,
                                reason=parsed.reason,
                                validity=[v is not None for v in parsed.vectors],
                            )
                if not self._live():
                    return
                slots = range(10 * batch + 1, 10 * batch + 11)
                if parsed is None:
                    self._forfeit(slots, "logical_call_failed")
                    continue
                for slot, raw in zip(slots, parsed.vectors, strict=True):
                    if not self._live():
                        return
                    if raw is None:
                        self._forfeit([slot], "invalid_vector")
                    else:
                        self._evaluate(raw, slot)
            self._finish("completed")

        return self._guarded(work)


def _json_ready(value):
    """Normalize numerical CMA stop metadata without altering its control flow."""
    if isinstance(value, dict):
        return {str(k): _json_ready(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, np.ndarray)):
        return [_json_ready(v) for v in value]
    if isinstance(value, np.generic):
        return _json_ready(value.item())
    if isinstance(value, float) and not math.isfinite(value):
        return repr(value)
    return value
