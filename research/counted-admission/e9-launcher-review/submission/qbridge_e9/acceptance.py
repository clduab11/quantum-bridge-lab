"""E9 acceptance specification, evaluated from the durable journal.

Every condition below is quoted from amendment A1 section A1.11 (proposed,
revision 2) and mapped to the code that decides it. Passing one request or
receiving HTTP 200 is explicitly insufficient.

A1.11 pass conditions, on EVERY fixture:
  1. valid count
  2. required echo fields equal the frozen profile (A1 section 6.1)
  3. usage.input_tokens == count, with all mandatory usage categories present
  4. cached_tokens == cache_write_tokens == 0
  5. identity vector recorded, and F2 vs F3 identical
  6. count(F3) == count(F2)
  7. section 6.7 parse result logged
Unknown mandatory usage, any profile mismatch, any count/usage inequality or any
cache activity fails E9. No baseline is recorded from a failed E9.
"""

from __future__ import annotations

from dataclasses import dataclass

from counted_responses_provider import contract as C

REQUIRED_FIXTURES = (
    "F1_short",
    "F2_maximal_renderer",
    "F3_repeat_of_F2",
    "F4_correction_no_valid_vectors",
)


@dataclass(frozen=True)
class Condition:
    key: str
    a1_requirement: str
    enforced_by: str
    status: str  # pass | fail | not_demonstrated
    detail: str

    @property
    def passed(self):
        return self.status == "pass"

    def as_dict(self):
        return {
            "key": self.key,
            "a1_requirement": self.a1_requirement,
            "enforced_by": self.enforced_by,
            "status": self.status,
            "detail": self.detail,
        }


@dataclass(frozen=True)
class Acceptance:
    conditions: tuple
    baseline_candidate: dict | None
    baseline_source: str | None
    f2_f3_gap_seconds: float | None
    cache_window_demonstrated: bool

    @property
    def failures(self):
        return tuple(c for c in self.conditions if c.status == "fail")

    @property
    def not_demonstrated(self):
        return tuple(c for c in self.conditions if c.status == "not_demonstrated")

    @property
    def passed(self):
        return not self.failures and not self.not_demonstrated

    def as_dict(self):
        return {
            "e9_accepted": self.passed,
            "conditions_total": len(self.conditions),
            "conditions_passed": sum(c.passed for c in self.conditions),
            "conditions_failed": len(self.failures),
            "conditions_not_demonstrated": len(self.not_demonstrated),
            "failed_keys": [c.key for c in self.failures],
            "not_demonstrated_keys": [c.key for c in self.not_demonstrated],
            "conditions": [c.as_dict() for c in self.conditions],
            "identity_baseline_candidate": self.baseline_candidate,
            "identity_baseline_source": self.baseline_source,
            "identity_baseline_accepted": False,
            "identity_baseline_acceptance_note": (
                "A1.11: the baseline is the identity vector of the first profile-valid"
                " completed E9 generation response and enters the manifest only on a"
                " separately recorded acceptance decision. This launcher records a"
                " CANDIDATE and never calls seed_identity_baseline."
            ),
            "f2_f3_gap_seconds": self.f2_f3_gap_seconds,
            "cache_window_coverage_demonstrated": self.cache_window_demonstrated,
        }


def _events(journal, kind):
    return [e for e in journal.read_events() if e["kind"] == kind]



def _generation_findings(journal):
    """Per-fixture generation findings and identity vectors, read from the journal.

    ``completed`` events inherit block/arm/batch/logical but not the fixture
    name, so the transport ``reserved`` event supplies it.
    """
    events = journal.read_events()
    reserved = {
        e["reservation"]: e
        for e in events
        if e["kind"] == "reserved" and e.get("resource") == "transport"
    }
    findings, vectors = {}, {}
    for event in events:
        if event["kind"] != "completed" or event.get("request_class") != "generation":
            continue
        origin = reserved.get(event.get("reservation"), {})
        fixture = origin.get("fixture")
        meta = event.get("metadata") or {}
        collected = (
            list(meta.get("usage_findings") or [])
            + list(meta.get("profile_findings") or [])
            + list(meta.get("identity_findings") or [])
        )
        findings.setdefault(fixture, []).extend(collected)
        if isinstance(meta.get("identity_vector"), dict):
            vectors[fixture] = meta["identity_vector"]
    return findings, vectors


def evaluate_acceptance(journal, outcomes, *, reasoning_effort: str) -> Acceptance:
    conditions = []

    def add(key, requirement, enforced_by, status, detail):
        conditions.append(Condition(key, requirement, enforced_by, status, detail))

    by_name = {o.fixture: o for o in outcomes}
    halts = _events(journal, "provider_halted")
    stops = _events(journal, "e9_stopped")

    # Structural: all four fixtures must have run to a received generation.
    add(
        "fixtures.all_four_completed",
        "Exactly four fixed fixtures, each run as one logical call",
        "orchestrator.run / e9_logical_finished",
        "pass"
        if all(
            name in by_name and by_name[name].outcome == "completed" for name in REQUIRED_FIXTURES
        )
        else "fail",
        ", ".join(
            f"{name}={by_name[name].outcome if name in by_name else 'absent'}"
            for name in REQUIRED_FIXTURES
        ),
    )
    add(
        "run.no_halt",
        "Unknown usage, profile mismatch, count/usage inequality or cache activity fails E9",
        "provider._persist_halt / orchestrator._halt",
        "pass" if not halts and not stops else "fail",
        f"provider_halted={[h.get('reason') for h in halts]}, "
        f"e9_stopped={[s.get('reason') for s in stops]}",
    )

    # 1. valid count on every fixture.
    receipts = {e.get("fixture"): e for e in _events(journal, "count_receipt")}
    add(
        "a1.1.valid_count",
        "Pass condition 1: valid count on every fixture",
        "contract.validate_count_payload via provider.count; count_receipt event",
        "pass"
        if all(
            name in receipts and type(receipts[name].get("counted_tokens")) is int
            for name in REQUIRED_FIXTURES
        )
        else "fail",
        ", ".join(
            f"{name}={receipts.get(name, {}).get('counted_tokens')}" for name in REQUIRED_FIXTURES
        ),
    )

    # 2/3/4 are decided inside the provider: any finding becomes an e9_fail halt.
    # The findings are read from the DURABLE journal, not from the in-memory
    # outcomes: a halted attempt returns no result to the orchestrator, but its
    # metadata and halt detail are already on disk.
    journal_findings, journal_vectors = _generation_findings(journal)
    all_findings = sorted(
        {f for values in journal_findings.values() for f in values}
        | {
            f
            for event in _events(journal, "provider_halt_detail")
            for f in (event.get("findings") or [])
        }
    )
    add(
        "a1.2.profile_echo",
        "Pass condition 2: required echo fields equal the frozen profile (A1 6.1)",
        "contract.validate_expected_profile (provider._received_object step 2)",
        "pass" if not any(f.startswith("profile_") for f in all_findings) else "fail",
        f"profile findings={sorted({f for f in all_findings if f.startswith('profile_')})}",
    )
    mismatch = [f for f in all_findings if f.startswith("count_usage_mismatch")]
    unknown = [
        f
        for f in all_findings
        if f.startswith(C.ACCOUNTING_FINDING_PREFIXES) or f == "input_tokens_details_unknown"
    ]
    add(
        "a1.3.usage_equals_count",
        "Pass condition 3: usage.input_tokens == count with all mandatory categories",
        "contract.usage_checks + settle_response (policy='e9')",
        "pass" if not mismatch and not unknown else "fail",
        f"count/usage mismatches={mismatch}, unknown-or-inconsistent usage={unknown}",
    )
    cache = [f for f in all_findings if f.startswith("cache_")]
    add(
        "a1.4.no_cache_activity",
        "Pass condition 4: cached_tokens == cache_write_tokens == 0",
        "contract.usage_checks cache_activity findings (IVF under e9 policy)",
        "pass" if not cache else "fail",
        f"cache findings={cache}",
    )

    # 5. identity vector recorded; F2 vs F3 identical.
    observations = _events(journal, "identity_observation")
    vectors = {
        name: vector for name, vector in journal_vectors.items() if name in REQUIRED_FIXTURES
    }
    add(
        "a1.5a.identity_recorded",
        "Pass condition 5: identity vector recorded for every fixture",
        "contract.identity_vector; provider identity_observation event",
        "pass" if len(vectors) == len(REQUIRED_FIXTURES) else "fail",
        f"vectors recorded for {sorted(vectors)}; identity_observation events={len(observations)}",
    )
    f2, f3 = vectors.get("F2_maximal_renderer"), vectors.get("F3_repeat_of_F2")
    if f2 is None or f3 is None:
        add(
            "a1.5b.f2_f3_identity_identical",
            "Pass condition 5: F2 and F3 identity vectors identical",
            "contract.compare_identity",
            "fail",
            "F2 or F3 identity vector absent",
        )
    else:
        diffs = C.compare_identity(f2, f3)
        add(
            "a1.5b.f2_f3_identity_identical",
            "Pass condition 5: F2 and F3 identity vectors identical",
            "contract.compare_identity",
            "pass" if not diffs else "fail",
            f"differences={diffs}",
        )

    # 6. count(F3) == count(F2).
    c2 = receipts.get("F2_maximal_renderer", {}).get("counted_tokens")
    c3 = receipts.get("F3_repeat_of_F2", {}).get("counted_tokens")
    add(
        "a1.6.f3_count_equals_f2",
        "Pass condition 6: count(F3) == count(F2)",
        "orchestrator count_receipt events",
        "pass" if isinstance(c2, int) and c2 == c3 else "fail",
        f"count(F2)={c2}, count(F3)={c3}",
    )

    # 7. section 6.7 parse result logged for every received text.
    parses = {e.get("fixture") for e in _events(journal, "e9_parse_result")}
    add(
        "a1.7.parse_result_logged",
        "Pass condition 7: section 6.7 parse result logged",
        "qbridge.proposals.parse_response; e9_parse_result event",
        "pass" if set(REQUIRED_FIXTURES) <= parses else "fail",
        f"parse results logged for {sorted(parses)}",
    )

    # Provisional identity observation vs an accepted baseline.
    baseline_candidate = observations[0]["vector"] if observations else None
    baseline_source = (
        observations[0].get("transport_reservation") if observations else None
    )
    add(
        "a1.baseline.provisional_only",
        "A provisional E9 identity observation is not an accepted baseline",
        "provider.identity_baseline (E9 records identity_observation, never identity_baseline)",
        "pass" if not _events(journal, "identity_baseline") else "fail",
        f"identity_observation={len(observations)}, "
        f"identity_baseline={len(_events(journal, 'identity_baseline'))}",
    )

    # F2/F3 timing: recorded, never assumed. A1.11 and the fixture README require
    # that no cache-lifetime claim is made without a demonstration.
    gap = None
    o2, o3 = by_name.get("F2_maximal_renderer"), by_name.get("F3_repeat_of_F2")
    if (
        o2 is not None
        and o3 is not None
        and o2.generation_started_monotonic is not None
        and o3.generation_started_monotonic is not None
    ):
        gap = o3.generation_started_monotonic - o2.generation_started_monotonic
    add(
        "a1.timing.f2_f3_recorded",
        "Record actual F2/F3 timing; claim no cache-window coverage not demonstrated",
        "orchestrator LogicalOutcome.generation_started_monotonic",
        "pass" if gap is not None else "not_demonstrated",
        f"F2->F3 generation start gap={gap!r} s. Cache-window coverage is NOT claimed:"
        " a zero-cache E9 pass demonstrates no cache lifetime.",
    )

    if reasoning_effort not in C.SUPPORTED_EFFORTS:
        add(
            "profile.effort_documented",
            "The reasoning effort is one documented Sol value fixed before E9",
            "contract.SUPPORTED_EFFORTS",
            "fail",
            f"effort={reasoning_effort!r}",
        )

    return Acceptance(
        tuple(conditions),
        baseline_candidate,
        baseline_source,
        gap,
        cache_window_demonstrated=False,
    )
