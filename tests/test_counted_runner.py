"""Two-class control flow with fabricated provider responses and objectives."""

import hashlib
import json
from dataclasses import dataclass

import pytest

from qbridge.counted_runner import AttemptResult, CountedArmRunner, RequestPair
from qbridge.journal import DurableJournal
from qbridge.runner import ArmClosed, InlineExecutor


class Clock:
    def __init__(self):
        self.now, self.waits = 0.0, []

    def __call__(self):
        return self.now

    def sleep(self, seconds):
        self.waits.append(seconds)
        self.now += seconds


class Provider:
    def __init__(self, count=None, generation=None):
        self.count_calls, self.generation_calls = [], []
        self.on_count = count or (lambda: AttemptResult("count_ok", counted_tokens=20))
        self.on_generation = generation or (
            lambda: AttemptResult("received_completed", text="good")
        )

    def prepare(self, request):
        body = json.dumps(request, sort_keys=True).encode()
        return RequestPair(body, body + b" generation-only-fields")

    def count(self, pair, context, timeout):
        self.count_calls.append((pair, context, timeout))
        return self.on_count()

    def generate(self, pair, receipt, context, timeout):
        assert receipt.count_body_sha256 == hashlib.sha256(pair.count_body).hexdigest()
        assert receipt.logical_key == context.logical_key
        self.generation_calls.append((pair, receipt, context, timeout))
        return self.on_generation()


@dataclass
class Parsed:
    vectors: tuple
    valid_count: int
    reason: str | None
    schema_valid: bool


def parse(text):
    if text == "bad":
        return Parsed((None,) * 10, 0, "invalid_json", False)
    return Parsed(((0.0,) * 20,) * 10, 10, None, True)


def make(log, clock=None, **kwargs):
    clock = clock or Clock()
    return CountedArmRunner(
        log,
        block=kwargs.pop("block", 0),
        arm="AI",
        objective=lambda _: 0.5,
        map_action=lambda x: x,
        clock=clock,
        sleep=clock.sleep,
        executor=InlineExecutor(),
        admission_limit=100,
        **kwargs,
    ), clock


def run(instance, provider):
    instance.initialize([[0.0] * 20] * 10)
    return instance.run_llm(
        provider,
        parse_response=parse,
        render_user=lambda _history, batch: f"fabricated {batch}",
        system_prompt=lambda: "fabricated system",
    )


def test_count_exhaustion_never_dispatches_generation_or_correction(tmp_path):
    with DurableJournal(tmp_path / "journal") as log:
        runner, clock = make(log)
        provider = Provider(count=lambda: AttemptResult("count_retryable"))
        result = run(runner, provider)
        assert len(provider.count_calls) == 57
        assert not provider.generation_calls
        assert result["logical_calls"] == 19 and result["forfeits"] == 190
        assert clock.waits == [5.0, 20.0] * 19
        assert {e["reason"] for e in log.read_events() if e["kind"] == "slot_forfeited"} == {
            "count_exhausted"
        }


def test_generation_retries_reuse_one_receipt_and_identical_pair(tmp_path):
    with DurableJournal(tmp_path / "journal") as log:
        runner, _ = make(log)
        provider = Provider(generation=lambda: AttemptResult("gen_retryable"))
        result = run(runner, provider)
        assert len(provider.count_calls) == 19 and len(provider.generation_calls) == 57
        assert result["logical_calls"] == 19 and result["forfeits"] == 190
        first = provider.generation_calls[:3]
        assert first[0][0] == first[1][0] == first[2][0]
        assert first[0][1] == first[1][1] == first[2][1]
        events = [
            e
            for e in log.read_events()
            if e["kind"] == "reserved" and e.get("resource") == "transport"
        ]
        assert sum(e["request_class"] == "count" for e in events) == 19
        assert sum(e["request_class"] == "generation" for e in events) == 57


def test_admission_rejection_consumes_count_only(tmp_path):
    with DurableJournal(tmp_path / "journal") as log:
        runner, _ = make(log)
        provider = Provider(count=lambda: AttemptResult("count_ok", counted_tokens=101))
        result = run(runner, provider)
        assert len(provider.count_calls) == 19 and not provider.generation_calls
        assert result["forfeits"] == 190
        assert {e["reason"] for e in log.read_events() if e["kind"] == "slot_forfeited"} == {
            "admission_rejected"
        }


def test_received_zero_valid_text_gets_one_new_count_and_correction(tmp_path):
    with DurableJournal(tmp_path / "journal") as log:
        runner, _ = make(log)
        provider = Provider(generation=lambda: AttemptResult("received_incomplete", text="bad"))
        result = run(runner, provider)
        assert result["logical_calls"] == 38 and result["forfeits"] == 190
        assert len(provider.count_calls) == len(provider.generation_calls) == 38
        first, correction = provider.generation_calls[:2]
        assert first[1].logical_key != correction[1].logical_key
        assert first[1].count_body_sha256 != correction[1].count_body_sha256
        assert b"PREVIOUS RESPONSE REJECTED: invalid_json." in correction[0].count_body


@pytest.mark.parametrize(
    "minimum,valid,waits", [(27.0, True, [27.0] * 38), (301.0, True, []), (None, False, [])]
)
def test_retry_after_minimum_never_shortened(tmp_path, minimum, valid, waits):
    with DurableJournal(tmp_path / "journal") as log:
        runner, clock = make(log)
        provider = Provider(
            count=lambda: AttemptResult(
                "count_retryable", retry_after_seconds=minimum, retry_after_valid=valid
            )
        )
        run(runner, provider)
        assert clock.waits == waits
        assert len(provider.count_calls) == (57 if waits else 19)


def test_halt_and_ivf_survive_a_fresh_runner(tmp_path):
    with DurableJournal(tmp_path / "journal") as log:
        runner, _ = make(log)
        provider = Provider(
            generation=lambda: AttemptResult(
                "received_completed", text="good", halt_reason="count_usage_mismatch", ivf=True
            )
        )
        result = run(runner, provider)
        assert result["ivf"] and result["forfeits"] == 190
        assert len(provider.count_calls) == len(provider.generation_calls) == 1
        next_runner, _ = make(log, block=1)
        run(next_runner, provider)
        assert len(provider.count_calls) == len(provider.generation_calls) == 1


def test_incomplete_count_evidence_halts_before_generation(tmp_path):
    with DurableJournal(tmp_path / "journal") as log:
        runner, _ = make(log)
        provider = Provider(count=lambda: AttemptResult("count_ok", counted_tokens=True))
        result = run(runner, provider)
        assert len(provider.count_calls) == 1 and not provider.generation_calls
        assert result["forfeits"] == 190


def test_common_deadline_includes_count_and_generation(tmp_path):
    with DurableJournal(tmp_path / "journal") as log:
        runner, clock = make(log)
        runner.deadline = 10

        def slow_count():
            clock.now += 11
            return AttemptResult("count_ok", counted_tokens=20)

        provider = Provider(count=slow_count)
        result = run(runner, provider)
        assert len(provider.count_calls) == 1 and not provider.generation_calls
        assert result["closed"] and result["forfeits"] == 190


def test_reopened_interrupted_arm_is_closed_without_replay(tmp_path):
    with DurableJournal(tmp_path / "journal") as log:
        runner, _ = make(log)
        runner.initialize([[0.0] * 20] * 10)
        reopened, _ = make(log)
        assert reopened.closed and reopened.summary()["forfeits"] == 190
        with pytest.raises(ArmClosed):
            reopened.run_llm(
                Provider(),
                parse_response=parse,
                render_user=lambda *_: "",
                system_prompt=lambda: "",
            )


def test_timeout_keeps_unresolved_count_reservations(tmp_path):
    def timeout():
        raise TimeoutError("fabricated provider timeout")

    with DurableJournal(tmp_path / "journal") as log:
        runner, _ = make(log)
        provider = Provider(count=timeout)
        result = run(runner, provider)
        reserved = [
            e
            for e in log.read_events()
            if e["kind"] == "reserved" and e.get("resource") == "transport"
        ]
        completed = {e["reservation"] for e in log.read_events() if e["kind"] == "completed"}
        assert len(reserved) == 57 and all(e["reservation"] not in completed for e in reserved)
        assert result["forfeits"] == 190 and not provider.generation_calls


@pytest.mark.parametrize("text,valid,forfeits", [("good", 20, 180), ("bad", 10, 190)])
def test_accounting_halt_preserves_received_text_but_suppresses_new_requests(
    tmp_path, text, valid, forfeits
):
    with DurableJournal(tmp_path / "journal") as log:
        runner, _ = make(log)
        provider = Provider(
            generation=lambda: AttemptResult(
                "received_completed",
                text=text,
                halt_reason="accounting_halt",
                accept_received_on_halt=True,
            )
        )
        result = run(runner, provider)
        assert result["valid_evaluations"] == valid
        assert result["forfeits"] == forfeits
        assert result["logical_calls"] == 1
        assert len(provider.count_calls) == len(provider.generation_calls) == 1
        assert not result["ivf"]


def test_real_worker_halt_is_observed_before_accepting_text(tmp_path):
    from qbridge.runner import ProcessExecutor

    with DurableJournal(tmp_path / "journal") as log:
        runner, _ = make(log)
        runner.executor = ProcessExecutor()

        class ForkProvider(Provider):
            def count(self, pair, context, timeout):
                log.append("fabricated_count_dispatch", transport_reservation=context.reservation)
                return AttemptResult("count_ok", counted_tokens=20)

            def generate(self, pair, receipt, context, timeout):
                log.append(
                    "provider_halted", reason="fabricated_child_halt", inferential_failure=True
                )
                # Journal state wins even if a child returns apparent success.
                return AttemptResult("received_completed", text="good")

        provider = ForkProvider()
        request = {"system": "fabricated", "user": "fabricated", "max_tokens": 8192}
        assert runner._logical(provider, request, 1, 1) is None
        assert runner._logical(provider, request, 2, 1) is None
        assert sum(e["kind"] == "fabricated_count_dispatch" for e in log.read_events()) == 1
        assert runner.summary()["ivf"]
