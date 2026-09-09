"""Offline observations of billing stops and accepted evidence after reopening."""

import json
import tempfile
from pathlib import Path

from e9tests import support
from qbridge_e9 import mocks
from qbridge_e9.acceptance import evaluate_acceptance
from qbridge_e9.limits import E9Limits
from qbridge_e9.orchestrator import E9Orchestrator


def reopen(journal, provider, records, clock, fixtures):
    return E9Orchestrator(
        journal=journal,
        provider=provider,
        fixture_set=fixtures,
        records_dir=records,
        limits=E9Limits(),
        clock=clock,
        sleep=clock.sleep,
    )


def main():
    root = Path(tempfile.mkdtemp(prefix="reopen-probe-"))
    output = {}

    def billed(_request):
        return mocks.error_response(429, code="project_spend_limit_exceeded")

    handler = mocks.derived_transport(count_plan=[billed, mocks.derived_count])
    journal, provider, records, original, clock, fixtures = support.build(
        root / "billing-stop", handler
    )
    original.run()
    before = [len(handler.count_calls), len(handler.generation_calls)]
    reopened = reopen(journal, provider, records, clock, fixtures)
    outcomes = reopened.run()
    output["billing_stop_forgotten_on_reopen"] = {
        "first_stop": original._stop_reason,
        "before": before,
        "after": [len(handler.count_calls), len(handler.generation_calls)],
        "second_stop": reopened._stop_reason,
        "second_outcomes": [outcome.outcome for outcome in outcomes],
    }
    journal.close()

    handler = mocks.derived_transport()
    journal, provider, records, original, clock, fixtures = support.build(
        root / "report", handler
    )
    first = evaluate_acceptance(journal, original.run(), reasoning_effort="medium").as_dict()
    reopened = reopen(journal, provider, records, clock, fixtures)
    second = evaluate_acceptance(journal, reopened.run(), reasoning_effort="medium").as_dict()
    output["successful_journal_reread_loses_acceptance"] = {
        "first_accepted": first["e9_accepted"],
        "second_accepted": second["e9_accepted"],
        "second_failed": second["failed_keys"],
        "second_not_demonstrated": second["not_demonstrated_keys"],
        "dispatches": [len(handler.count_calls), len(handler.generation_calls)],
    }
    journal.close()
    print(json.dumps(output, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
