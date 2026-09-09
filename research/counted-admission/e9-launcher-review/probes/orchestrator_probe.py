"""Offline observations of worker cancellation and the journal's run deadline."""

import json
import tempfile
import time
from pathlib import Path

from e9tests import support
from qbridge_e9 import mocks
from qbridge_e9.limits import E9Limits
from qbridge_e9.orchestrator import E9Orchestrator


class RealClock:
    def __call__(self):
        return time.monotonic()

    def time(self):
        return support.WALL

    def sleep(self, seconds):
        time.sleep(seconds)


def main():
    root = Path(tempfile.mkdtemp(prefix="orchestrator-probe-"))
    output = {}
    seen_timeouts = []

    def slow_generation(request):
        seen_timeouts.append(request.extensions.get("timeout"))
        time.sleep(2.25)
        return mocks.derived_generation(request)

    handler = mocks.derived_transport(generation_plan=[slow_generation])
    journal, _, _, orchestrator, _, _ = support.build(
        root / "deadline", handler, clock=RealClock(), limits=E9Limits(deadline_seconds=2)
    )
    started = time.monotonic()
    outcomes = orchestrator.run()
    output["blocking_generation_not_canceled"] = {
        "elapsed_seconds": time.monotonic() - started,
        "configured_deadline_seconds": 2,
        "request_timeouts": seen_timeouts,
        "outcomes": [outcome.outcome for outcome in outcomes],
        "remaining_seconds": orchestrator.remaining_seconds(),
    }
    journal.close()

    clock = support.Clock()
    first = True

    def exhaust_once(request):
        nonlocal first
        if first:
            first = False
            clock.advance(7400)
        return mocks.derived_generation(request)

    handler = mocks.derived_transport(generation_plan=[exhaust_once])
    journal, provider, records, orchestrator, clock, fixtures = support.build(
        root / "reopen", handler, clock=clock
    )
    first_outcomes = orchestrator.run()
    before = [len(handler.count_calls), len(handler.generation_calls)]
    reopened = E9Orchestrator(
        journal=journal,
        provider=provider,
        fixture_set=fixtures,
        records_dir=records,
        limits=E9Limits(),
        clock=clock,
        sleep=clock.sleep,
    )
    second_outcomes = reopened.run()
    output["same_journal_resets_exhausted_deadline"] = {
        "first_outcomes": [outcome.outcome for outcome in first_outcomes],
        "first_stop": orchestrator._stop_reason,
        "first_attempts": before,
        "second_outcomes": [outcome.outcome for outcome in second_outcomes],
        "after_attempts": [len(handler.count_calls), len(handler.generation_calls)],
        "second_remaining_seconds": reopened.remaining_seconds(),
    }
    journal.close()
    print(json.dumps(output, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
