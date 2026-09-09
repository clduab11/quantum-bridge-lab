"""Observe rev2 response-body deadlines and crash-prefix resumption."""

import json
import shutil
import tempfile
import time
from pathlib import Path

import httpx
from e9tests import support
from qbridge.journal import DurableJournal
from qbridge_e9 import mocks
from qbridge_e9.acceptance import evaluate_acceptance
from qbridge_e9.limits import E9Limits


class RealClock:
    def __call__(self):
        return time.monotonic()

    def time(self):
        return support.WALL

    def sleep(self, seconds):
        time.sleep(seconds)


class DelayedBody(httpx.SyncByteStream):
    def __init__(self, payload, delay):
        self.payload = payload
        self.delay = delay

    def __iter__(self):
        time.sleep(self.delay)
        yield self.payload


def main():
    root = Path(tempfile.mkdtemp(prefix="rev2-deadline-probe-"))
    output = {}

    def streaming_generation(request):
        normal = mocks.derived_generation(request)
        return httpx.Response(
            normal.status_code,
            headers=normal.headers,
            stream=DelayedBody(normal.content, 2.25),
        )

    handler = mocks.derived_transport(generation_plan=[streaming_generation])
    journal, _, _, orchestrator, _, _ = support.build(
        root / "streaming",
        handler,
        clock=RealClock(),
        limits=E9Limits(deadline_seconds=2),
    )
    started = time.monotonic()
    outcomes = orchestrator.run()
    output["streaming_response_body_evades_guard"] = {
        "elapsed_seconds": time.monotonic() - started,
        "deadline_seconds": 2,
        "first_outcome": outcomes[0].outcome,
        "wall_clock_events": support.events(journal, "e9_attempt_wall_clock"),
        "remaining_seconds": orchestrator.remaining_seconds(),
    }
    journal.close()

    # Retain a valid journal prefix ending after F2, representing a process
    # interruption before a final run event; do not fabricate chain entries.
    clock = support.Clock()

    def advance_generation(request):
        clock.advance(50)
        return mocks.derived_generation(request)

    handler = mocks.derived_transport(generation_plan=[advance_generation])
    journal, _, records, orchestrator, _, fixtures = support.build(
        root / "partial_source", handler, clock=clock
    )
    orchestrator.run()
    journal.close()
    resumed = root / "partial_resumed"
    resumed.mkdir()
    (resumed / "raw").mkdir(mode=0o700)
    lines = (root / "partial_source/work/e9_journal.jsonl").read_text().splitlines(keepends=True)
    keep = []
    for line in lines:
        keep.append(line)
        event = json.loads(line)
        event = event.get("payload", event)
        if (
            event.get("kind") == "e9_logical_finished"
            and event.get("fixture") == "F2_maximal_renderer"
        ):
            break
    journal_path = resumed / "e9_journal.jsonl"
    journal_path.write_text("".join(keep))
    journal_path.chmod(0o600)
    for path in records.iterdir():
        if "_l1_" in path.name or "_l2_" in path.name:
            shutil.copy2(path, resumed / "raw" / path.name)

    resume_clock = support.Clock()
    resume_clock.now = 10000
    resumed_handler = mocks.derived_transport()
    with DurableJournal(journal_path) as resumed_journal:
        _, resumed_orchestrator, _ = support.rebuild(
            resumed_journal,
            resumed / "raw",
            resumed_handler,
            fixtures,
            clock=resume_clock,
        )
        resumed_outcomes = resumed_orchestrator.run()
        acceptance = evaluate_acceptance(
            resumed_journal, resumed_outcomes, reasoning_effort="medium"
        ).as_dict()
        output["partial_resume_after_original_deadline_expired"] = {
            "monotonic_resume": 10000,
            "deadline_seconds": 7400,
            "prior_consumed_seconds": resumed_orchestrator._prior_consumed,
            "new_budget_seconds": resumed_orchestrator.budget_seconds(),
            "new_counts": len(resumed_handler.count_calls),
            "new_generations": len(resumed_handler.generation_calls),
            "acceptance": acceptance["e9_accepted"],
            "f2_f3_gap_seconds": acceptance["f2_f3_gap_seconds"],
        }
    print(json.dumps(output, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
