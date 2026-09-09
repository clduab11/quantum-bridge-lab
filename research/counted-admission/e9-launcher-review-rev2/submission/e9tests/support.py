"""Offline test scaffolding. Every value here is FABRICATED and is not evidence."""

from __future__ import annotations

import hashlib
import json
import os
import stat
from pathlib import Path

import httpx

from counted_responses_provider.authority import (
    HTTPX_VERSION,
    SDK_VERSION,
    AuthorityRecord,
    profile_sha256,
)
from counted_responses_provider.provider import SingleAttemptResponsesProvider
from qbridge.journal import DurableJournal
from qbridge.request_records import RequestRecords

from qbridge_e9 import mocks
from qbridge_e9.deadline import DeadlineGuard, guarded_transport_factory
from qbridge_e9.fixtures import load_fixture_set
from qbridge_e9.limits import E9Limits
from qbridge_e9.orchestrator import E9Orchestrator

REPO_ROOT = Path(__file__).resolve().parents[2] / "repo"
FIXTURES_DIR = REPO_ROOT / "research" / "counted-admission" / "e9-inputs"
FABRICATED_KEY = "sk-OFFLINE-FABRICATED-NEVER-VALID"
RECORDED = "2026-09-09T00:00:00Z"
VALID_THROUGH = "2026-11-21T00:00:00Z"
# 2026-09-09T12:00:00Z, inside the fabricated validity window.
WALL = 1_788_955_200.0
PLACEHOLDER_SHA = hashlib.sha256(b"FABRICATED test placeholder").hexdigest()


def private_dir(path):
    path = Path(path)
    path.mkdir(parents=True, exist_ok=True)
    os.chmod(path, stat.S_IRWXU)
    return path


class Clock:
    """Monotonic clock whose sleeps advance time; records every wait."""

    def __init__(self, wall=WALL):
        self.now, self.wall, self.waits = 0.0, wall, []

    def __call__(self):
        return self.now

    def sleep(self, seconds):
        self.waits.append(seconds)
        self.now += seconds

    def time(self):
        return self.wall

    def advance(self, seconds):
        self.now += seconds


def authority(**overrides) -> AuthorityRecord:
    limits = E9Limits()
    data = {
        "scope": "e9",
        "synthetic": True,
        "authorized_by": "FABRICATED test fixture; this is NOT an authorization",
        "recorded_at_utc": RECORDED,
        "purpose": "offline orchestrator regression tests",
        "profile_sha256": profile_sha256("medium"),
        "model": "gpt-5.6-sol",
        "reasoning_effort": "medium",
        "input_token_ceiling": limits.admission_limit,
        "max_output_tokens": 8192,
        "count_attempt_cap": limits.max_count_attempts,
        "generation_attempt_cap": limits.max_generation_attempts,
        "usd_ceiling": "32",
        "input_usd_per_million": "4",
        "cached_input_usd_per_million": "0.4",
        "cache_write_usd_per_million": "5",
        "output_usd_per_million": "20",
        "billing_categories": ("input", "cached_input", "cache_write", "output"),
        "rate_source": "FABRICATED placeholder rate source",
        "rate_source_sha256": PLACEHOLDER_SHA,
        "price_valid_through_utc": VALID_THROUGH,
        "count_fee_ceiling_usd": "1.088",
        "count_fee_evidence": "FABRICATED placeholder; no count fee evidence exists",
        "count_fee_evidence_sha256": PLACEHOLDER_SHA,
        "count_fee_valid_through_utc": VALID_THROUGH,
        "count_fee_covers_failed_and_rejected": True,
        "count_fee_verified": True,
        "sdk_version": SDK_VERSION,
        "httpx_version": HTTPX_VERSION,
    }
    data.update(overrides)
    return AuthorityRecord(**data)


def fixture_set(provider=None, *, effort="medium"):
    return load_fixture_set(
        FIXTURES_DIR, reasoning_effort=effort, provider=provider, repo_root=REPO_ROOT
    )


def build(
    tmp_path,
    handler,
    *,
    auth=None,
    clock=None,
    api_key=FABRICATED_KEY,
    limits=None,
    guard=None,
    guard_clock=None,
):
    """Return (journal, provider, records_dir, orchestrator, clock, fixture_set).

    The DeadlineGuard is wired exactly as the CLI wires it: the provider's
    transport factory is wrapped, so every dispatch runs under an armed
    wall-clock budget. The orchestrator REFUSES to run without one.
    """
    work = private_dir(tmp_path / "work")
    records_dir = private_dir(work / "raw")
    journal = DurableJournal(work / "e9_journal.jsonl")
    records = RequestRecords(records_dir, public_repo=work / "guard")
    clock = clock or Clock()
    guard = guard or DeadlineGuard(clock=guard_clock or clock)
    provider = SingleAttemptResponsesProvider(
        journal=journal,
        records=records,
        authority=auth or authority(),
        transport_factory=guarded_transport_factory(
            lambda: httpx.MockTransport(handler), guard
        ),
        api_key_provider=lambda: api_key,
        wall_clock=clock.time,
    )
    fs = fixture_set(provider)
    orchestrator = E9Orchestrator(
        journal=journal,
        provider=provider,
        fixture_set=fs,
        records_dir=records_dir,
        limits=limits or E9Limits(),
        clock=clock,
        sleep=clock.sleep,
        deadline_guard=guard,
    )
    orchestrator.guard_handle = guard
    return journal, provider, records_dir, orchestrator, clock, fs


def reopen(journal, provider, fixture_set_, records_dir, clock, *, limits=None, guard=None):
    """A second orchestrator over the SAME journal, as a resumed process would."""
    return E9Orchestrator(
        journal=journal,
        provider=provider,
        fixture_set=fixture_set_,
        records_dir=records_dir,
        limits=limits or E9Limits(),
        clock=clock,
        sleep=clock.sleep,
        deadline_guard=guard or DeadlineGuard(clock=clock),
    )


def nominal_handler(fs):
    scripted, counts = mocks.nominal_plan(fs)
    return scripted, counts


def events(journal, kind):
    return [e for e in journal.read_events() if e["kind"] == kind]


def write_json(path, payload):
    Path(path).write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    return Path(path)


def rebuild(journal, records_dir, handler, fixture_set_, *, clock=None, auth=None, limits=None):
    """A provider AND orchestrator over an EXISTING journal, sharing one guard.

    The provider's transport and the orchestrator must share the same
    DeadlineGuard; if they do not, the transport raises DeadlineNotArmed rather
    than dispatching without a wall-clock bound.
    """
    clock = clock or Clock()
    guard = DeadlineGuard(clock=clock)
    records = RequestRecords(records_dir, public_repo=Path(records_dir).parent / "guard")
    provider = SingleAttemptResponsesProvider(
        journal=journal,
        records=records,
        authority=auth or authority(),
        transport_factory=guarded_transport_factory(
            lambda: httpx.MockTransport(handler), guard
        ),
        api_key_provider=lambda: FABRICATED_KEY,
        wall_clock=clock.time,
    )
    orchestrator = E9Orchestrator(
        journal=journal,
        provider=provider,
        fixture_set=fixture_set_,
        records_dir=records_dir,
        limits=limits or E9Limits(),
        clock=clock,
        sleep=clock.sleep,
        deadline_guard=guard,
    )
    return provider, orchestrator, guard
