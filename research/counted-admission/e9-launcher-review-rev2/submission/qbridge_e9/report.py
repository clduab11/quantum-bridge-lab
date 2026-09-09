"""Durable E9 report. Fabricated dry-run evidence is labelled as such.

Review finding 7 (fixed here). The previous revision hardcoded
``amendment_a1_adopted: false``, ``live_spending_authority_issued: false`` and
``storage.outside_git: true``, and wrote every run to the same
``e9_report.json``. Those fields are now DERIVED from the gate result, the
durable journal and the filesystem, the report distinguishes *issuing* spending
authority from *consuming* an authority that already exists, and each run gets
its own timestamped file that is never overwritten.
"""

from __future__ import annotations

import json
import platform
import sys
from datetime import datetime, timezone
from pathlib import Path

from counted_responses_provider import contract as C
from counted_responses_provider.ledger import decimal_text

from qbridge_e9.gate import git_worktree_root


def environment_record():
    try:
        import httpx
        import openai

        sdk, hx = openai.__version__, httpx.__version__
    except Exception as exc:  # pragma: no cover
        sdk, hx = None, f"import_failed:{type(exc).__name__}"
    try:
        import numpy

        numpy_version = numpy.__version__
    except Exception:  # pragma: no cover
        numpy_version = None
    return {
        "python": sys.version.split()[0],
        "python_implementation": platform.python_implementation(),
        "platform": platform.platform(),
        "openai": sdk,
        "httpx": hx,
        "numpy": numpy_version,
    }


def ledger_record(provider):
    state = provider.ledger.state()
    return {
        "scope": state["scope"],
        "ceiling_usd": decimal_text(state["ceiling"]),
        "committed_usd": decimal_text(state["committed"]),
        "attempts": dict(state["attempts"]),
        "unresolved_or_retained": state["unresolved_or_retained"],
        "overrun_recorded": state["overrun_recorded"],
        "halted": state["halted"],
        "open_reservations": list(state["open"]),
    }


def journal_summary(journal):
    counts = {}
    for event in journal.read_events():
        counts[event["kind"]] = counts.get(event["kind"], 0) + 1
    return counts


def dispatch_counts(journal):
    """Transport reservations per request class, read from the journal."""
    out = {"count": 0, "generation": 0}
    for event in journal.read_events():
        if event["kind"] == "reserved" and event.get("resource") == "transport":
            request_class = event.get("request_class")
            if request_class in out:
                out[request_class] += 1
    return out


def authorization_record(*, gate_result, journal, authority, mode, fabricated, transport_class):
    """Derived, never hardcoded.

    ``spending_authority_issued_by_this_run`` is a structural invariant: this
    launcher consumes a recorded authority and never creates one. Whether an
    existing authority was actually consumed is derived from the mode and the
    gate.
    """
    dispatches = dispatch_counts(journal)
    adoption_status = gate_result.status_of("adoption.record")
    return {
        "amendment_a1_adoption_evidence": adoption_status or "not_evaluated",
        "amendment_a1_adopted_per_evidence": adoption_status == "pass",
        "protocol_freeze_asserted_by_this_run": False,
        "spending_authority_issued_by_this_run": False,
        "spending_authority_consumed": bool(mode == "live" and gate_result.may_dispatch_live),
        "authority_sha256": authority.sha256(),
        "authority_synthetic": authority.synthetic,
        "study_launched_by_this_run": False,
        "transport_class": transport_class,
        "transport_is_mock": bool(fabricated),
        "transport_reservations": dispatches,
        "experimental_generation_calls": 0 if fabricated else dispatches["generation"],
        "provider_count_calls": 0 if fabricated else dispatches["count"],
        "fabricated_dispatch_attempts": dispatches if fabricated else {"count": 0, "generation": 0},
        "study_objective_candidate_evaluations": 0,
    }


def build_report(
    *,
    mode,
    fixture_set,
    gate_result,
    outcomes,
    acceptance,
    provider,
    journal,
    limits,
    stop_reason,
    elapsed_seconds,
    fabricated,
    authority,
    records_dir,
    journal_path,
    orchestrator=None,
    transport_class="unknown",
):
    worktree = git_worktree_root(records_dir)
    return {
        "kind": "e9_model_preflight_report",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "mode": mode,
        "evidence_class": (
            "FABRICATED offline dry run: every response was invented by "
            "qbridge_e9.mocks. No provider request, no charge, no measurement."
            if fabricated
            else "live provider dispatch"
        ),
        "fabricated_responses": bool(fabricated),
        "authorizations": authorization_record(
            gate_result=gate_result,
            journal=journal,
            authority=authority,
            mode=mode,
            fabricated=fabricated,
            transport_class=transport_class,
        ),
        "limits": {
            "deadline_seconds": limits.deadline_seconds,
            "max_count_attempts": limits.max_count_attempts,
            "max_generation_attempts": limits.max_generation_attempts,
            "attempt_timeout_seconds": limits.attempt_timeout_seconds,
            "max_attempts_per_logical": limits.max_attempts_per_logical,
            "admission_limit": limits.admission_limit,
            "max_output_tokens": limits.max_output_tokens,
            "model": limits.model,
            "reasoning_effort": limits.reasoning_effort,
            "count_endpoint": C.COUNT_ENDPOINT,
            "generation_endpoint": C.GENERATION_ENDPOINT,
        },
        "deadline": {
            "governing_deadline_seconds": limits.deadline_seconds,
            # Captured when this run STARTED. The journal total below also
            # includes this run's own consumption, which is what a subsequent
            # run would subtract.
            "prior_consumed_seconds": (
                orchestrator._prior_consumed if orchestrator is not None else None
            ),
            "journal_consumed_seconds_total": (
                orchestrator.consumed_seconds() if orchestrator is not None else None
            ),
            "budget_this_run_seconds": (
                orchestrator.budget_seconds() if orchestrator is not None else None
            ),
            "remaining_seconds": (
                orchestrator.remaining_seconds() if orchestrator is not None else None
            ),
            "attempt_wall_clock_enforced_at_transport": True,
            "refused_reason": getattr(orchestrator, "refused_reason", None),
            "prior_terminal_records": (
                orchestrator.terminal_records() if orchestrator is not None else None
            ),
        },
        "authority": {
            "scope": authority.scope,
            "synthetic": authority.synthetic,
            "sha256": authority.sha256(),
            "usd_ceiling": authority.usd_ceiling,
            "count_fee_ceiling_usd": authority.count_fee_ceiling_usd,
            "count_fee_verified": authority.count_fee_verified,
            "rate_source": authority.rate_source,
            "rate_source_sha256": authority.rate_source_sha256,
            "price_valid_through_utc": authority.price_valid_through_utc,
            "input_usd_per_million": authority.input_usd_per_million,
            "cached_input_usd_per_million": authority.cached_input_usd_per_million,
            "cache_write_usd_per_million": authority.cache_write_usd_per_million,
            "output_usd_per_million": authority.output_usd_per_million,
        },
        "environment": environment_record(),
        "storage": {
            "records_dir": str(records_dir),
            "journal": str(journal_path),
            "git_worktree_root": str(worktree) if worktree is not None else None,
            "outside_git": worktree is None,
        },
        "fixtures": fixture_set.as_dict(),
        "gate": gate_result.as_dict(),
        "run": {
            "stop_reason": stop_reason,
            "elapsed_seconds": elapsed_seconds,
            "outcomes": [o.as_dict() for o in outcomes],
        },
        "acceptance": acceptance.as_dict(),
        "ledger": ledger_record(provider),
        "journal_event_counts": journal_summary(journal),
        "limitations": [
            "A dry run demonstrates orchestration only. It measures no token count,"
            " no price, no cache behaviour, no model compliance and no cost.",
            "Byte length is not a token count and these fixtures do not prove that"
            " every legal history fits the context or the admission limit.",
            "Equality of count and usage at E9 is necessary, not sufficient, for the"
            " confirmatory claim (A1 adoption sequence).",
            "The reviewed Responses route exposes no serving fingerprint, so weight or"
            " serving changes that leave the echo unchanged are undetectable.",
            "No cache-window coverage is claimed. F2/F3 timing is recorded only.",
            "The software enforces attempt and reservation limits conditional on the"
            " recorded prices and provider compliance; it does not enforce the invoice.",
            "The attempt wall clock is enforced by cancelling the inner transport and"
            " rejecting late results. A synchronous in-process mock handler cannot be"
            " preempted; its late result is refused but its thread runs to completion.",
            "A hash match shows a retained file is the recorded one. It is not"
            " verification of an account's charges or of a person's approval.",
        ],
    }


def write_report(report, out_dir):
    """Write a per-run report that never overwrites an earlier one."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = report["generated_at_utc"].replace(":", "").replace("-", "")
    for sequence in range(0, 1000):
        suffix = "" if sequence == 0 else f"_{sequence:03d}"
        path = out_dir / f"e9_report_{stamp}{suffix}.json"
        if not path.exists():
            break
    else:  # pragma: no cover - 1000 reports in one second
        raise RuntimeError("cannot allocate a non-colliding report filename")
    payload = json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n"
    with open(path, "x", encoding="utf-8") as handle:
        handle.write(payload)
    index = out_dir / "e9_reports.jsonl"
    with open(index, "a", encoding="utf-8") as handle:
        handle.write(
            json.dumps(
                {
                    "report": path.name,
                    "generated_at_utc": report["generated_at_utc"],
                    "mode": report["mode"],
                    "e9_accepted": report["acceptance"]["e9_accepted"],
                    "stop_reason": report["run"]["stop_reason"],
                },
                sort_keys=True,
            )
            + "\n"
        )
    return path
