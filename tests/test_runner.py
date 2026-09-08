"""Synthetic objectives and mocked transport only; no study evaluation."""

import importlib
import multiprocessing
import os
import signal
import time
from dataclasses import dataclass

import numpy as np
import pytest


def modules():
    return importlib.import_module("qbridge.journal"), importlib.import_module("qbridge.runner")


class Clock:
    def __init__(self):
        self.now = 0.0
        self.waits = []

    def __call__(self):
        return self.now

    def sleep(self, seconds):
        self.waits.append(seconds)
        self.now += seconds


def vectors(count=10, value=0.0):
    return [[value] * 20 for _ in range(count)]


def identity_map(raw):
    return np.asarray(raw, dtype=float)


def constant_objective(theta):
    return 0.5


def make_runner(tmp_path, arm="AI", objective=constant_objective, **kwargs):
    journal, runner = modules()
    log = journal.DurableJournal(tmp_path / "events")
    clock = kwargs.pop("clock", Clock())
    instance = runner.ArmRunner(
        log, block=0, arm=arm, objective=objective, map_action=identity_map,
        clock=clock, sleep=clock.sleep, executor=runner.InlineExecutor(),
        input_token_limit=1000, count_input_tokens=lambda request: 10, **kwargs,
    )
    return instance, log, clock, runner


@dataclass
class Parsed:
    vectors: tuple
    valid_count: int
    reason: str | None
    schema_valid: bool


def parse(text):
    if text == "bad":
        return Parsed((None,) * 10, 0, "invalid_json", False)
    if text == "partial":
        return Parsed((None, tuple([0.2] * 20)) + (None,) * 8, 1, None, False)
    return Parsed(tuple(tuple(row) for row in vectors()), 10, None, True)


def render(history, batch):
    return f"batch={batch};indices=" + ",".join(str(row["index"]) for row in history)


def run_ai(instance, transport):
    return instance.run_llm(transport, parse_response=parse, render_user=render, system_prompt=lambda: "synthetic")


def test_partial_response_keeps_slot_positions_without_correction(tmp_path):
    instance, log, _, runner = make_runner(tmp_path)
    with log:
        instance.initialize(vectors())
        result = run_ai(instance, lambda request, timeout: runner.TransportResponse(200, "partial"))
        assert result["valid_evaluations"] == 29
        assert result["forfeits"] == 171
        assert result["logical_calls"] == 19
        assert [row["index"] for row in instance.history()][:12] == list(range(1, 11)) + [12, 22]


def test_only_one_zero_valid_correction_uses_same_slots(tmp_path):
    instance, log, _, runner = make_runner(tmp_path)
    requests = []

    def transport(request, timeout):
        requests.append(request)
        return runner.TransportResponse(200, "bad")

    with log:
        instance.initialize(vectors())
        result = run_ai(instance, transport)
        assert result["logical_calls"] == 38
        assert result["attempt_allowances_used"] == 38
        assert result["forfeits"] == 190
        assert "PREVIOUS RESPONSE REJECTED: invalid_json." in requests[1]["user"]
        assert result["valid_evaluations"] == 10


def test_transport_retries_identical_request_three_times_with_fixed_backoffs(tmp_path):
    instance, log, clock, runner = make_runner(tmp_path)
    requests = []

    def transport(request, timeout):
        requests.append((request, timeout))
        return runner.TransportResponse(503, "unavailable")

    with log:
        instance.initialize(vectors())
        result = run_ai(instance, transport)
        assert result["attempt_allowances_used"] == 57
        assert result["logical_calls"] == 19
        assert clock.waits == [5.0, 20.0] * 19
        assert requests[0] == requests[1] == requests[2]
        assert requests[0][1] == 300.0
        assert result["forfeits"] == 190


@pytest.mark.parametrize("status", [400, 401, 403])
def test_terminal_http_error_never_retries_or_corrects(tmp_path, status):
    instance, log, clock, runner = make_runner(tmp_path)
    with log:
        instance.initialize(vectors())
        result = run_ai(instance, lambda request, timeout: runner.TransportResponse(status, "not JSON"))
        assert result["attempt_allowances_used"] == 19
        assert result["logical_calls"] == 19
        assert clock.waits == []


def test_deadline_during_backoff_cancels_remaining_arm_work(tmp_path):
    instance, log, clock, runner = make_runner(tmp_path)

    def transport(request, timeout):
        clock.now = 35998.0
        return runner.TransportResponse(429, "limited")

    with log:
        instance.initialize(vectors())
        result = run_ai(instance, transport)
        assert result["attempt_allowances_used"] == 1
        assert result["forfeits"] == 190
        assert clock.waits == [2.0]
        assert result["endpoint"] == 0.5
        assert result["svf"] is False


def test_late_objective_value_is_not_accepted_at_deadline(tmp_path):
    clock = Clock()
    calls = 0

    def objective(theta):
        nonlocal calls
        calls += 1
        if calls == 11:
            clock.now = 36000.0
            return 0.0
        return 0.5

    instance, log, _, _ = make_runner(tmp_path, arm="RS", objective=objective, clock=clock)
    with log:
        instance.initialize(vectors())
        result = instance.run_random(vectors(190))
        assert result["endpoint"] == 0.5
        assert result["valid_evaluations"] == 10
        assert result["simulator_invalid"] == 1
        assert result["forfeits"] == 189
        assert result["svf"] is True


def test_isolated_invalid_rs_value_consumes_slot_and_continues(tmp_path):
    calls = 0

    def objective(theta):
        nonlocal calls
        calls += 1
        return float("nan") if calls == 11 else 0.5

    instance, log, _, _ = make_runner(tmp_path, arm="RS", objective=objective)
    with log:
        instance.initialize(vectors())
        result = instance.run_random(vectors(190))
        assert result["confirmed_objective_calls"] == 200
        assert result["valid_evaluations"] == 199
        assert result["simulator_invalid"] == 1
        assert result["forfeits"] == 0
        assert result["svf"] is True


def test_duplicate_counts_prior_confirmed_invalid_evaluation(tmp_path):
    calls = 0

    def objective(theta):
        nonlocal calls
        calls += 1
        return float("nan") if calls <= 2 else 0.5

    instance, log, _, _ = make_runner(tmp_path, arm="RS", objective=objective)
    with log:
        result = instance.initialize(vectors())
        completions = [event for event in log.read_events()
                       if event["kind"] == "completed" and event.get("resource") == "objective"]
        assert completions[0]["duplicate"] is False
        assert completions[1]["status"] == "simulator_invalid"
        assert completions[1]["duplicate"] is True
        assert completions[2]["status"] == "valid"
        assert completions[2]["duplicate"] is True
        assert result["duplicates"] == 9


def test_guard_crash_cancels_its_registered_nondetached_callback(tmp_path):
    _, runner = modules()
    executor = runner.ProcessExecutor()
    marker = tmp_path / "late_callback"

    def callback():
        os.kill(os.getppid(), signal.SIGKILL)
        time.sleep(0.2)
        marker.write_text("late")

    with pytest.raises((TimeoutError, runner.WorkerCrashed)):
        executor.guard(lambda: executor.call(callback, timeout=0.5), timeout=0.08)
    time.sleep(0.3)
    assert not marker.exists()


def test_callback_orphaned_before_registration_never_starts_work(tmp_path, monkeypatch):
    _, runner = modules()
    original_worker = runner._worker
    original_start = multiprocessing.process.BaseProcess.start
    marker = tmp_path / "orphan_work"

    def delayed_worker(send, receive, work, guard, callback_group, expected_parent):
        if not guard:
            time.sleep(0.15)
        original_worker(send, receive, work, guard, callback_group, expected_parent)

    def crash_after_start(process):
        original_start(process)
        if multiprocessing.parent_process() is not None:
            os.kill(os.getpid(), signal.SIGKILL)

    monkeypatch.setattr(runner, "_worker", delayed_worker)
    monkeypatch.setattr(multiprocessing.process.BaseProcess, "start", crash_after_start)
    executor = runner.ProcessExecutor()
    with pytest.raises((TimeoutError, runner.WorkerCrashed)):
        executor.guard(lambda: executor.call(lambda: marker.write_text("late"), timeout=1.0),
                       timeout=0.1)
    time.sleep(0.3)
    assert not marker.exists()


class CMA:
    def __init__(self, *, invalid_ask=False):
        self.generations = 0
        self.invalid_ask = invalid_ask

    def ask(self):
        return vectors(9 if self.invalid_ask else 10, min(self.generations / 100, 0.19))

    def tell(self, samples, values):
        assert len(samples) == len(values) == 10
        self.generations += 1

    def stop(self):
        return {"synthetic_stop": True}


def test_cma_ignores_stop_but_only_tells_complete_generations(tmp_path):
    instance, log, _, _ = make_runner(tmp_path, arm="CMA")
    optimizer = CMA()
    with log:
        instance.initialize(vectors())
        result = instance.run_cma(optimizer)
        assert optimizer.generations == 19
        assert result["valid_evaluations"] == 200
        assert len([e for e in log.read_events() if e["kind"] == "cma_generation"]) == 19


def test_invalid_cma_ask_is_rejected_before_any_generation_objective(tmp_path):
    instance, log, _, _ = make_runner(tmp_path, arm="CMA")
    optimizer = CMA(invalid_ask=True)
    with log:
        instance.initialize(vectors())
        result = instance.run_cma(optimizer)
        assert optimizer.generations == 0
        assert result["confirmed_objective_calls"] == 10
        assert result["forfeits"] == 190
        assert result["svf"] is False


def test_cma_simulator_failure_keeps_earlier_values_without_partial_tell(tmp_path):
    calls = 0

    def objective(theta):
        nonlocal calls
        calls += 1
        return float("nan") if calls == 13 else 0.5

    instance, log, _, _ = make_runner(tmp_path, arm="CMA", objective=objective)
    optimizer = CMA()
    with log:
        instance.initialize(vectors())
        result = instance.run_cma(optimizer)
        assert optimizer.generations == 0
        assert result["valid_evaluations"] == 12
        assert result["simulator_invalid"] == 1
        assert result["forfeits"] == 187


def test_reopening_interrupted_arm_never_replays_reserved_slot(tmp_path):
    instance, log, _, runner = make_runner(tmp_path)
    instance.initialize(vectors())
    log.reserve("objective", "AI:0:11", block=0, arm="AI", slot=11)
    log.close()
    recovered, reopened, _, _ = make_runner(tmp_path)
    with reopened:
        result = recovered.summary()
        assert result["unresolved_objective_reservations"] == 1
        assert result["confirmed_objective_calls"] == 10
        assert result["forfeits"] == 189
        assert result["svf"] is True
        assert result["endpoint"] == 0.5
        with pytest.raises(runner.ArmClosed):
            recovered.initialize(vectors())


def test_model_change_sets_ivf_without_discarding_outcomes(tmp_path):
    instance, log, _, runner = make_runner(tmp_path, expected_identity={"model": "one"})
    with log:
        instance.initialize(vectors())
        result = run_ai(instance, lambda request, timeout: runner.TransportResponse(200, "ok", metadata={"model": "two"}))
        assert result["valid_evaluations"] == 200
        assert result["ivf"] is True


def test_input_token_ceiling_prevents_dispatch(tmp_path):
    instance, log, _, _ = make_runner(tmp_path)
    instance.count_input_tokens = lambda request: 1001

    def transport(request, timeout):
        raise AssertionError("oversized request must not dispatch")

    with log:
        instance.initialize(vectors())
        result = run_ai(instance, transport)
        assert result["attempt_allowances_used"] == 0
        assert result["forfeits"] == 190


def test_process_executor_cancels_work_instead_of_leaving_a_thread(tmp_path):
    _, runner = modules()
    marker = tmp_path / "must-not-exist"

    def work():
        time.sleep(0.25)
        marker.write_text("late side effect")

    with pytest.raises(TimeoutError):
        runner.ProcessExecutor().call(work, timeout=0.03)
    time.sleep(0.3)
    assert not marker.exists()


def test_process_guard_keeps_cma_state_for_all_generations(tmp_path):
    journal, runner = modules()
    with journal.DurableJournal(tmp_path / "events") as log:
        instance = runner.ArmRunner(log, block=0, arm="CMA", objective=constant_objective,
                                    map_action=identity_map)
        instance.initialize(vectors())
        result = instance.run_cma(CMA())
        assert result["valid_evaluations"] == 200
        assert len([e for e in log.read_events() if e["kind"] == "cma_generation"]) == 19


def test_arm_guard_cancels_a_nested_callback(tmp_path):
    _, runner = modules()
    marker = tmp_path / "nested-late-write"
    executor = runner.ProcessExecutor()

    def late_write():
        time.sleep(0.3)
        marker.write_text("should have been cancelled")

    with pytest.raises(TimeoutError):
        executor.guard(lambda: executor.call(late_write, timeout=1.0), timeout=0.06)
    time.sleep(0.35)
    assert not marker.exists()


@pytest.mark.parametrize("bad_slot", [1, 6])
def test_initialization_attempts_all_ten_after_isolated_simulator_invalid(tmp_path, bad_slot):
    calls = 0

    def objective(theta):
        nonlocal calls
        calls += 1
        return float("nan") if calls == bad_slot else 0.5

    instance, log, _, _ = make_runner(tmp_path, arm="RS", objective=objective)
    with log:
        initial = instance.initialize(vectors())
        assert initial["valid_evaluations"] == 9
        assert initial["confirmed_objective_calls"] == 10
        assert initial["closed"] is False
        result = instance.run_random(vectors(190))
        assert result["valid_evaluations"] == 199
        assert result["forfeits"] == 0
        assert result["svf"] is True


def test_zero_valid_initialization_stops_after_all_ten_slots(tmp_path):
    instance, log, _, _ = make_runner(tmp_path, objective=lambda theta: float("nan"))
    with log:
        result = instance.initialize(vectors())
        assert result["confirmed_objective_calls"] == 10
        assert result["simulator_invalid"] == 10
        assert result["forfeits"] == 190
        assert result["endpoint"] is None
        assert result["closed"] is True


def test_installed_pycma_ask_tell_continues_after_a_stop_condition(tmp_path):
    import cma

    instance, log, _, _ = make_runner(tmp_path, arm="CMA")

    def bounded_map(raw):
        pairs = np.asarray(raw).reshape(10, 2)
        norms = np.hypot(pairs[:, 0], pairs[:, 1])
        return (pairs / np.maximum(norms[:, None], 1.0)).reshape(20)

    instance.map_action = bounded_map
    optimizer = cma.CMAEvolutionStrategy(np.zeros(20), 0.5, {
        "popsize": 10, "seed": 7, "maxiter": 0, "verbose": -9, "verb_log": 0,
    })
    with log:
        instance.initialize(vectors())
        result = instance.run_cma(optimizer)
        assert optimizer.countiter == 19
        assert optimizer.stop()
        assert result["valid_evaluations"] == 200
        assert result["svf"] is False


def test_oversized_integer_objective_is_simulator_invalid_and_sets_svf(tmp_path):
    calls = 0

    def objective(theta):
        nonlocal calls
        calls += 1
        return 10**1000 if calls == 11 else 0.5

    instance, log, _, _ = make_runner(tmp_path, arm="RS", objective=objective)
    with log:
        instance.initialize(vectors())
        result = instance.run_random(vectors(190))
        assert result["svf"] is True
        assert result["simulator_invalid"] == 1
        assert result["confirmed_objective_calls"] == 200
        assert result["unresolved_objective_reservations"] == 0


def test_per_call_timeout_cancels_nondetached_callback_descendants(tmp_path):
    _, runner = modules()
    marker = tmp_path / "descendant-late-write"
    executor = runner.ProcessExecutor()

    def late_write():
        time.sleep(0.2)
        marker.write_text("should have been cancelled")

    def callback():
        process = multiprocessing.get_context("fork").Process(target=late_write)
        process.start()
        time.sleep(0.5)

    def arm():
        try:
            executor.call(callback, timeout=0.06)
        except TimeoutError:
            pass

    executor.guard(arm, timeout=2)
    time.sleep(0.25)
    assert not marker.exists()


def test_reported_fingerprint_change_sets_ivf_even_if_not_a_frozen_key(tmp_path):
    instance, log, _, runner = make_runner(tmp_path, expected_identity={"model": "fixed"})
    calls = 0

    def transport(request, timeout):
        nonlocal calls
        calls += 1
        return runner.TransportResponse(200, "ok", metadata={"model": "fixed", "fingerprint": "first" if calls == 1 else "second"})

    with log:
        instance.initialize(vectors())
        result = run_ai(instance, transport)
        assert result["valid_evaluations"] == 200
        assert result["ivf"] is True
