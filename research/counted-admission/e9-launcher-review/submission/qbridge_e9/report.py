"""Durable E9 report. Fabricated dry-run evidence is labelled as such."""

from __future__ import annotations

import json
import platform
import sys
from datetime import datetime, timezone
from pathlib import Path

from counted_responses_provider import contract as C
from counted_responses_provider.ledger import decimal_text


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
):
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
        "authorizations": {
            "amendment_a1_adopted": False,
            "protocol_frozen": False,
            "live_spending_authority_issued": False,
            "study_launched": False,
            "experimental_generation_calls": 0 if fabricated else None,
            "provider_count_calls": 0 if fabricated else None,
        },
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
            "outside_git": True,
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
        ],
    }


def write_report(report, out_dir):
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / "e9_report.json"
    path.write_text(json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n")
    return path
