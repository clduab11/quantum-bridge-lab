"""The bounded E9 orchestrator.

Division of responsibility, per the work order and A1.11:

* the reviewed provider owns exactly ONE HTTP attempt (bound bytes, pre-send
  verification, durable retention, monetary reservation, usage settlement,
  profile/identity checks, halt persistence);
* this orchestrator owns the fixture sequence, the two attempt caps, the
  attempt timeout, the retry rule, the monotonic stop limit, admission, the
  count receipt and the durable no-replay behaviour.

The orchestrator never lowers a server-directed wait, never retries a
documented billing/spend rejection, and never replays an attempt whose
dispatch outcome is unknown.
"""

from __future__ import annotations

import copy
import hashlib
import math
import time
from dataclasses import dataclass, field
from pathlib import Path

from counted_responses_provider import contract as C
from qbridge.counted_runner import AttemptResult, CountReceipt, DispatchContext, RequestPair

from qbridge_e9.limits import E9_ARM, E9_BLOCK, STUDY_ARM_LABELS, E9Limits

# developers.openai.com/api/docs/guides/error-codes and .../guides/spend-limits
# (retrieved 2026-09-09): these 429 codes are billing/spend rejections, and the
# guide states that retrying them will not restore access. The reviewed
# contract's _status_bucket maps every 429 to "retryable"; the orchestrator
# therefore classifies them itself. See patches/0001-spend-limit-not-retryable.diff
# for the minimal upstream correction.
SPEND_LIMIT_ERROR_CODES = frozenset(
    {
        "organization_spend_limit_exceeded",
        "project_spend_limit_exceeded",
        "organization_usage_limit_exceeded",
        "credit_balance_exhausted",
    }
)
SPEND_LIMIT_ERROR_TYPES = frozenset({"insufficient_quota"})

# Categories the orchestrator may retry, subject to contract.retry_decision.
RETRYABLE = frozenset({"count_retryable", "gen_retryable", "gen_failed_retryable"})
RECEIVED = frozenset({"received_completed", "received_incomplete"})


class E9Refused(RuntimeError):
    """The run could not start; no attempt was made."""


@dataclass
class LogicalOutcome:
    fixture: str
    batch: int
    logical: int
    count_category: str | None = None
    counted_tokens: int | None = None
    admission: str | None = None
    generation_category: str | None = None
    text: str | None = None
    parse: dict | None = None
    outcome: str = "not_started"
    reason: str | None = None
    count_attempts: int = 0
    generation_attempts: int = 0
    generation_started_monotonic: float | None = None
    generation_elapsed_seconds: float | None = None
    identity_vector: dict | None = None
    usage: dict | None = None
    findings: list = field(default_factory=list)

    def as_dict(self):
        return {
            "fixture": self.fixture,
            "batch": self.batch,
            "logical": self.logical,
            "outcome": self.outcome,
            "reason": self.reason,
            "count_category": self.count_category,
            "counted_tokens": self.counted_tokens,
            "admission": self.admission,
            "generation_category": self.generation_category,
            "count_attempts": self.count_attempts,
            "generation_attempts": self.generation_attempts,
            "generation_started_monotonic": self.generation_started_monotonic,
            "generation_elapsed_seconds": self.generation_elapsed_seconds,
            "identity_vector": self.identity_vector,
            "usage": self.usage,
            "findings": list(self.findings),
            "parse": self.parse,
            "text_present": self.text is not None,
        }


class E9Orchestrator:
    """Sequence the four fixtures under one monotonic stop limit."""

    def __init__(
        self,
        *,
        journal,
        provider,
        fixture_set,
        records_dir,
        limits: E9Limits | None = None,
        clock=time.monotonic,
        sleep=time.sleep,
        parse_response=None,
    ):
        self.journal = journal
        self.provider = provider
        self.fixture_set = fixture_set
        self.records_dir = Path(records_dir)
        self.limits = limits or E9Limits()
        self.clock = clock
        self.sleep = sleep
        if parse_response is None:
            from qbridge.proposals import parse_response as _parse

            parse_response = _parse
        self.parse_response = parse_response
        self.started_monotonic = None
        self.outcomes = []
        self._stop_reason = None

        authority = getattr(provider, "authority", None)
        if authority is None or authority.scope != "e9":
            raise E9Refused("the provider must be constructed with an E9-scope authority")
        if authority.count_attempt_cap != self.limits.max_count_attempts:
            raise E9Refused("authority count cap must equal the orchestrator's count allowance")
        if authority.generation_attempt_cap != self.limits.max_generation_attempts:
            raise E9Refused(
                "authority generation cap must equal the orchestrator's generation allowance"
            )
        if authority.input_token_ceiling != self.limits.admission_limit:
            raise E9Refused("authority input ceiling must equal the admission limit")
        if E9_ARM in STUDY_ARM_LABELS:
            raise E9Refused("the E9 record label must not be a study arm label")
        if fixture_set.failed:
            raise E9Refused(f"fixture verification failed: {fixture_set.failed[0].detail}")

    # -- durable state ----------------------------------------------------
    def _events(self):
        return self.journal.read_events()

    def _halt(self):
        halts = [e for e in self._events() if e["kind"] == "provider_halted"]
        if not halts:
            return None
        return next(
            (h for h in halts if h.get("inferential_failure")),
            next((h for h in halts if h.get("reason") != "accounting_halt"), halts[0]),
        )

    def _transport_events(self):
        events = self._events()
        reserved = [
            e for e in events if e["kind"] == "reserved" and e.get("resource") == "transport"
        ]
        completed = {e["reservation"] for e in events if e["kind"] == "completed"}
        return reserved, completed

    def attempts_used(self, request_class):
        reserved, _ = self._transport_events()
        return sum(1 for e in reserved if e.get("request_class") == request_class)

    def _finished_fixtures(self):
        return {
            e["fixture"]
            for e in self._events()
            if e["kind"] == "e9_logical_finished" and "fixture" in e
        }

    def remaining_seconds(self):
        if self.started_monotonic is None:
            return float(self.limits.deadline_seconds)
        return self.limits.deadline_seconds - (self.clock() - self.started_monotonic)

    # -- billing classification (defence in depth) ------------------------
    def billing_rejection(self, metadata):
        """Return a documented billing/spend code for a 429, else None."""
        if metadata.get("http_status") != 429:
            return None
        name = metadata.get("response_record")
        if not name:
            return None
        path = self.records_dir / name
        if not path.is_file():
            return None
        payload, error = C.parse_json_strict(path.read_bytes())
        if error is not None or not isinstance(payload, dict):
            return None
        err = payload.get("error")
        if not isinstance(err, dict):
            return None
        code, kind = err.get("code"), err.get("type")
        if isinstance(code, str) and code in SPEND_LIMIT_ERROR_CODES:
            return code
        if isinstance(kind, str) and kind in SPEND_LIMIT_ERROR_TYPES:
            return f"type:{kind}"
        return None

    # -- the run ----------------------------------------------------------
    def run(self):
        self.started_monotonic = self.clock()
        reserved, completed = self._transport_events()
        unresolved = [e["reservation"] for e in reserved if e["reservation"] not in completed]
        self.journal.append(
            "e9_run_started",
            arm=E9_ARM,
            block=E9_BLOCK,
            deadline_seconds=self.limits.deadline_seconds,
            max_count_attempts=self.limits.max_count_attempts,
            max_generation_attempts=self.limits.max_generation_attempts,
            admission_limit=self.limits.admission_limit,
            manifest_sha256=self.fixture_set.manifest_sha256,
            fixture_order=[f.name for f in self.fixture_set.fixtures],
            resumed=bool(reserved),
            prior_attempts={
                "count": self.attempts_used("count"),
                "generation": self.attempts_used("generation"),
            },
            unresolved_prior_reservations=unresolved,
        )
        if unresolved:
            # An attempt whose dispatch outcome is unknown may already have been
            # billed. Replaying it could duplicate a dispatch, so the run stops.
            self._persist_stop(f"unresolved_prior_attempt:{unresolved[0]}")

        already = self._finished_fixtures()
        for fixture in self.fixture_set.fixtures:
            outcome = LogicalOutcome(fixture.name, fixture.batch, fixture.logical)
            self.outcomes.append(outcome)
            if fixture.name in already:
                outcome.outcome, outcome.reason = "skipped", "already_finished_in_this_journal"
                continue
            if self._stop_reason is not None:
                outcome.outcome, outcome.reason = "not_started", self._stop_reason
                self._not_sent(fixture, self._stop_reason)
                continue
            halt = self._halt()
            if halt is not None:
                self._stop_reason = halt["reason"]
                outcome.outcome, outcome.reason = "not_started", halt["reason"]
                self._not_sent(fixture, halt["reason"])
                continue
            if self.remaining_seconds() <= 0:
                self._stop_reason = "deadline_exhausted"
                outcome.outcome, outcome.reason = "not_started", "deadline_exhausted"
                self._not_sent(fixture, "deadline_exhausted")
                continue
            self._logical(fixture, outcome)
            self.journal.append(
                "e9_logical_finished",
                arm=E9_ARM,
                block=E9_BLOCK,
                fixture=fixture.name,
                batch=fixture.batch,
                logical=fixture.logical,
                outcome=outcome.outcome,
                reason=outcome.reason,
            )

        self.journal.append(
            "e9_run_finished",
            arm=E9_ARM,
            block=E9_BLOCK,
            stop_reason=self._stop_reason,
            elapsed_seconds=self.clock() - self.started_monotonic,
            remaining_seconds=self.remaining_seconds(),
            attempts_used={
                "count": self.attempts_used("count"),
                "generation": self.attempts_used("generation"),
            },
            outcomes=[o.as_dict() for o in self.outcomes],
        )
        return tuple(self.outcomes)

    def _persist_stop(self, reason):
        self._stop_reason = reason
        self.journal.append("e9_stopped", arm=E9_ARM, block=E9_BLOCK, reason=reason)

    def _not_sent(self, fixture, reason, **extra):
        self.journal.append(
            "request_not_sent",
            arm=E9_ARM,
            block=E9_BLOCK,
            batch=fixture.batch,
            logical=fixture.logical,
            fixture=fixture.name,
            reason=reason,
            **extra,
        )

    # -- one fixture ------------------------------------------------------
    def _logical(self, fixture, outcome):
        pair = RequestPair(fixture.count_bytes, fixture.generation_bytes)
        self.journal.append(
            "logical_started",
            arm=E9_ARM,
            block=E9_BLOCK,
            batch=fixture.batch,
            logical=fixture.logical,
            fixture=fixture.name,
            count_body_sha256=fixture.count_sha256,
            generation_body_sha256=fixture.generation_sha256,
        )
        counted = self._attempts(pair, None, fixture, "count", outcome)
        if counted is None:
            outcome.outcome = "count_failed"
            return
        result, context = counted
        outcome.count_category = result.category
        outcome.counted_tokens = result.counted_tokens

        receipt = CountReceipt(
            context.logical_key,
            hashlib.sha256(pair.count_body).hexdigest(),
            result.counted_tokens,
            context.reservation,
        )
        self.journal.append(
            "count_receipt",
            arm=E9_ARM,
            block=E9_BLOCK,
            batch=fixture.batch,
            logical=fixture.logical,
            fixture=fixture.name,
            **receipt.__dict__,
        )

        admission = C.admit(result.counted_tokens, self.limits.admission_limit)
        outcome.admission = admission
        if admission != "admitted":
            # A1.11: an over-limit count is a recorded finding for a revised
            # amendment. L* is never changed from an observation.
            outcome.outcome, outcome.reason = "admission_rejected", "admission_rejected"
            self._not_sent(
                fixture, "admission_rejected", counted_tokens=result.counted_tokens
            )
            return
        if not C.may_dispatch_generation(
            count_category=result.category,
            admission=admission,
            pair_bound=True,
            profile_valid=True,
            halted=self._halt() is not None,
        ):
            outcome.outcome, outcome.reason = "generation_blocked", "may_dispatch_generation_false"
            self._not_sent(fixture, "may_dispatch_generation_false")
            return

        generated = self._attempts(pair, receipt, fixture, "generation", outcome)
        if generated is None:
            outcome.outcome = "generation_failed"
            return
        gen_result, _ = generated
        outcome.generation_category = gen_result.category
        outcome.text = gen_result.text
        outcome.usage = gen_result.usage
        meta = gen_result.metadata or {}
        outcome.identity_vector = meta.get("identity_vector")
        outcome.generation_elapsed_seconds = meta.get("elapsed_seconds")
        outcome.findings = list(meta.get("usage_findings") or []) + list(
            meta.get("profile_findings") or []
        ) + list(meta.get("identity_findings") or [])

        # A1 section 6.7 parse result is logged for every received text.
        if isinstance(gen_result.text, str):
            parsed = self.parse_response(gen_result.text)
            outcome.parse = {
                "valid_count": parsed.valid_count,
                "schema_valid": bool(parsed.schema_valid),
                "reason": parsed.reason,
                "vector_slots": len(parsed.vectors),
            }
            self.journal.append(
                "e9_parse_result",
                arm=E9_ARM,
                block=E9_BLOCK,
                batch=fixture.batch,
                logical=fixture.logical,
                fixture=fixture.name,
                **outcome.parse,
            )
        outcome.outcome = "completed" if gen_result.category == "received_completed" else (
            "incomplete" if gen_result.category == "received_incomplete" else "generation_failed"
        )

    # -- attempts for one request class -----------------------------------
    def _attempts(self, pair, receipt, fixture, request_class, outcome):
        body = pair.count_body if request_class == "count" else pair.generation_body
        cap = (
            self.limits.max_count_attempts
            if request_class == "count"
            else self.limits.max_generation_attempts
        )
        for attempt in range(1, self.limits.max_attempts_per_logical + 1):
            halt = self._halt()
            if halt is not None:
                self._stop_reason = halt["reason"]
                outcome.reason = halt["reason"]
                return None
            if self._stop_reason is not None:
                outcome.reason = self._stop_reason
                return None
            remaining = self.remaining_seconds()
            if not math.isfinite(remaining) or remaining <= 0:
                self._persist_stop("deadline_exhausted")
                outcome.reason = "deadline_exhausted"
                return None
            used = self.attempts_used(request_class)
            if used >= cap:
                self._persist_stop(f"{request_class}_attempt_cap_reached")
                outcome.reason = f"{request_class}_attempt_cap_reached"
                return None

            key = f"{E9_ARM}:{E9_BLOCK}:{fixture.batch}:{fixture.logical}:{request_class}:{attempt}"
            reservation = self.journal.reserve(
                "transport",
                key,
                block=E9_BLOCK,
                arm=E9_ARM,
                batch=fixture.batch,
                logical=fixture.logical,
                attempt=attempt,
                request_class=request_class,
                body_sha256=hashlib.sha256(body).hexdigest(),
                fixture=fixture.name,
            )
            context = DispatchContext(
                E9_BLOCK, E9_ARM, fixture.batch, fixture.logical, request_class, attempt,
                reservation,
            )
            timeout = min(float(self.limits.attempt_timeout_seconds), remaining)
            started = self.clock()
            if request_class == "generation" and outcome.generation_started_monotonic is None:
                outcome.generation_started_monotonic = started
            if request_class == "count":
                outcome.count_attempts += 1
            else:
                outcome.generation_attempts += 1

            result = (
                self.provider.count(pair, context, timeout)
                if request_class == "count"
                else self.provider.generate(pair, receipt, context, timeout)
            )
            if not isinstance(result, AttemptResult):
                self.journal.complete(
                    reservation,
                    status="invalid_provider_result",
                    request_class=request_class,
                    dispatched=None,
                    usage=None,
                    metadata={},
                    counted_tokens=None,
                    text=None,
                )
                self._persist_stop("invalid_provider_result")
                outcome.reason = "invalid_provider_result"
                return None

            metadata = copy.deepcopy(result.metadata or {})
            self.journal.complete(
                reservation,
                status=result.category,
                request_class=request_class,
                dispatched=None,
                usage=result.usage,
                metadata=metadata,
                counted_tokens=result.counted_tokens,
                text=result.text,
            )

            # A documented billing/spend rejection is classified FIRST, so the
            # recorded reason and the e9_spend_limit_rejection event are the same
            # whether or not patches/0001-spend-limit-not-retryable.diff has been
            # applied to the provider. Unpatched, the provider offers this as a
            # retryable 429; patched, it offers a credential halt. Either way the
            # launcher stops here with the specific code.
            billing = self.billing_rejection(metadata)
            if billing is not None:
                self.journal.append(
                    "e9_spend_limit_rejection",
                    arm=E9_ARM,
                    block=E9_BLOCK,
                    batch=fixture.batch,
                    logical=fixture.logical,
                    fixture=fixture.name,
                    request_class=request_class,
                    error_code=billing,
                    http_status=metadata.get("http_status"),
                    response_record=metadata.get("response_record"),
                    provider_category=result.category,
                    provider_halt_reason=result.halt_reason,
                )
                self._persist_stop(f"spend_limit_halt:{billing}")
                outcome.reason = f"spend_limit_halt:{billing}"
                return None
            if result.halt_reason:
                self._stop_reason = result.halt_reason
                outcome.reason = result.halt_reason
                return None
            if "halt_credential" in result.category or "contract_anomaly" in result.category:
                self._persist_stop(result.category)
                outcome.reason = result.category
                return None
            halt = self._halt()
            if halt is not None:
                self._stop_reason = halt["reason"]
                outcome.reason = halt["reason"]
                return None
            if result.category == "count_ok" or result.category in RECEIVED:
                return result, context
            if result.category not in RETRYABLE:
                outcome.reason = result.category
                return None

            retry_after = None
            finding = None
            if not result.retry_after_valid:
                finding = "retry_after_malformed"
            elif result.retry_after_seconds is not None:
                retry_after = math.ceil(result.retry_after_seconds)
            retry, wait, reason = C.retry_decision(
                attempt, retry_after, finding, self.remaining_seconds()
            )
            self.journal.append(
                "e9_retry_decision",
                arm=E9_ARM,
                block=E9_BLOCK,
                batch=fixture.batch,
                logical=fixture.logical,
                fixture=fixture.name,
                request_class=request_class,
                attempt=attempt,
                retry=bool(retry),
                wait_seconds=wait,
                decision_reason=reason,
                server_minimum_seconds=retry_after,
                remaining_seconds=self.remaining_seconds(),
            )
            if not retry:
                outcome.reason = reason
                return None
            self.sleep(wait)
        outcome.reason = f"{request_class}_exhausted"
        return None
