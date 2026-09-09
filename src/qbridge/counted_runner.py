"""Prospective counted-admission control flow with an injected provider.

This preserves ArmRunner's slot, correction, deadline and no-replay lifecycle.
It owns count/generation attempt caps and admission, but is NOT a live adapter:
the injected provider must enforce the reviewed wire profile, spending and
price authority, durable pre-send retention, accounting and identity checks.
No provider implementation or live-study entry point is supplied here.
"""

from __future__ import annotations

import copy
import hashlib
import json
import math
from dataclasses import dataclass, field

from qbridge.runner import ATTEMPT_SECONDS, ArmRunner, WorkerCrashed


@dataclass(frozen=True)
class RequestPair:
    """Immutable bytes already validated by the provider's pure prepare step."""

    count_body: bytes
    generation_body: bytes

    def __post_init__(self):
        if any(
            type(body) is not bytes or not body for body in (self.count_body, self.generation_body)
        ):
            raise ValueError("prepared request bodies must be nonempty immutable bytes")


@dataclass(frozen=True)
class DispatchContext:
    block: int
    arm: str
    batch: int
    logical: int
    request_class: str
    attempt: int
    reservation: str

    @property
    def logical_key(self):
        return f"{self.arm}:{self.block}:{self.batch}:{self.logical}"


@dataclass(frozen=True)
class CountReceipt:
    logical_key: str
    count_body_sha256: str
    counted_tokens: int
    reservation: str


@dataclass(frozen=True)
class AttemptResult:
    """Classified, accounted result from one injected provider attempt.

    The provider returns usage/metadata only after retaining the raw response
    and settling or preserving its monetary reservation. Retry-After parsing
    belongs to the provider; malformed values set retry_after_valid=False.
    halt_reason prevents all later provider dispatch; ivf additionally records
    an inferential validity failure. Transports must persist a halt before
    returning, too, so a child crash cannot erase it.
    """

    category: str
    counted_tokens: int | None = None
    text: str | None = None
    usage: dict | None = None
    metadata: dict = field(default_factory=dict)
    retry_after_seconds: float | None = None
    retry_after_valid: bool = True
    halt_reason: str | None = None
    ivf: bool = False
    accept_received_on_halt: bool = False


_RETRYABLE = {"count_retryable", "gen_retryable", "gen_failed_retryable"}
_RECEIVED = {"received_completed", "received_incomplete"}
_CATEGORIES = {
    "count": {
        "count_ok",
        "count_retryable",
        "count_terminal",
        "count_contract_anomaly",
        "count_halt_credential",
    },
    "generation": {
        "gen_retryable",
        "gen_terminal",
        "gen_contract_anomaly",
        "gen_halt_credential",
        "gen_failed_retryable",
        "gen_failed_terminal",
        *_RECEIVED,
    },
}


def _valid_result(result, request_class):
    if (
        not isinstance(result, AttemptResult)
        or not isinstance(result.category, str)
        or result.category not in _CATEGORIES[request_class]
    ):
        return False
    if type(result.ivf) is not bool or type(result.retry_after_valid) is not bool:
        return False
    if type(result.accept_received_on_halt) is not bool:
        return False
    if result.accept_received_on_halt and (
        result.halt_reason != "accounting_halt" or result.ivf or result.category not in _RECEIVED
    ):
        return False
    if result.halt_reason is not None and (
        not isinstance(result.halt_reason, str) or not result.halt_reason
    ):
        return False
    if result.ivf and result.halt_reason is None:
        return False
    if result.category == "count_ok" and (
        type(result.counted_tokens) is not int or result.counted_tokens < 0
    ):
        return False
    if result.category in _RECEIVED and not isinstance(result.text, str):
        return False
    if not isinstance(result.metadata, dict):
        return False
    if result.usage is not None and (
        not isinstance(result.usage, dict)
        or any(
            not isinstance(k, str) or not k or (v is not None and (type(v) is not int or v < 0))
            for k, v in result.usage.items()
        )
    ):
        return False
    if result.retry_after_seconds is not None and (
        type(result.retry_after_seconds) not in (int, float)
        or not math.isfinite(result.retry_after_seconds)
        or result.retry_after_seconds < 0
    ):
        return False
    try:
        json.dumps(result.metadata, allow_nan=False)
    except (ValueError, TypeError):
        return False
    return True


class CountedArmRunner(ArmRunner):
    """Two independently capped classes inside the same monotonic arm deadline.

    The explicit admission limit must be bound by the eventual frozen run
    configuration. Smaller limits are useful for synthetic tests; construction
    is not scientific adoption or authority to make a provider request.
    """

    def __init__(self, *args, admission_limit, **kwargs):
        if type(admission_limit) is not int or not 0 < admission_limit <= 272000:
            raise ValueError("admission limit must be an explicit integer from 1 to 272000")
        self.admission_limit = admission_limit
        self._last_failure = "logical_call_failed"
        super().__init__(*args, **kwargs)

    def _halted(self):
        halts = [e for e in self.journal.read_events() if e["kind"] == "provider_halted"]
        # The accounting exception may preserve already-received text only
        # when no stricter failure was durably recorded by the worker.
        return next(
            (e for e in halts if e.get("inferential_failure")),
            next(
                (e for e in halts if e.get("reason") != "accounting_halt"),
                halts[0] if halts else None,
            ),
        )

    def _halt(self, reason, *, ivf=False):
        existing = self._halted()
        if (
            existing is None
            or (ivf and not existing.get("inferential_failure"))
            or (reason != "accounting_halt" and existing["reason"] == "accounting_halt")
        ):
            self._event("provider_halted", reason=reason, inferential_failure=ivf)
        if ivf:
            self._flag("ivf", reason)
        self._last_failure = reason

    def _forfeit(self, slots, reason):
        super()._forfeit(slots, self._last_failure if reason == "logical_call_failed" else reason)

    def _wait_retry(self, result, attempt):
        if not result.retry_after_valid:
            self._last_failure = "retry_after_malformed"
            return False
        wait = max((5.0, 20.0)[attempt - 1], result.retry_after_seconds or 0.0)
        remaining = self._remaining()
        if wait > ATTEMPT_SECONDS:
            self._last_failure = "retry_after_exceeds_wait_limit"
            return False
        if not math.isfinite(remaining) or wait + 1.0 > remaining:
            self._last_failure = "deadline_insufficient_for_retry"
            return False
        self.sleep(wait)
        return self._live()

    def _attempts(self, provider, pair, receipt, batch, logical, request_class):
        body = pair.count_body if request_class == "count" else pair.generation_body
        for attempt in range(1, 4):
            if not self._live():
                return None
            halted = self._halted()
            if halted:
                self._last_failure = halted["reason"]
                if halted.get("inferential_failure"):
                    self._flag("ivf", halted["reason"])
                return None
            key = f"{self.arm}:{self.block}:{batch}:{logical}:{request_class}:{attempt}"
            reservation = self.journal.reserve(
                "transport",
                key,
                block=self.block,
                arm=self.arm,
                batch=batch,
                logical=logical,
                attempt=attempt,
                request_class=request_class,
                body_sha256=hashlib.sha256(body).hexdigest(),
            )
            context = DispatchContext(
                self.block, self.arm, batch, logical, request_class, attempt, reservation
            )
            timeout = min(ATTEMPT_SECONDS, self._remaining())
            try:
                result = self.executor.call(
                    lambda: (
                        provider.count(pair, context, timeout)
                        if request_class == "count"
                        else provider.generate(pair, receipt, context, timeout)
                    ),
                    timeout=timeout,
                )
            except (TimeoutError, ConnectionError) as exc:
                # Neither client timeout nor connection failure proves zero
                # billing. Keep the transport reservation unresolved, too.
                self._event("attempt_uncertain", reservation=reservation, error=type(exc).__name__)
                result = AttemptResult(
                    "count_retryable" if request_class == "count" else "gen_retryable"
                )
            except WorkerCrashed:
                self._recover("transport_interruption")
                return None
            except Exception as exc:
                self._event("attempt_uncertain", reservation=reservation, error=type(exc).__name__)
                self._halt("provider_client_error")
                return None
            else:
                if not _valid_result(result, request_class):
                    self._event(
                        "attempt_uncertain",
                        reservation=reservation,
                        error="invalid_provider_result",
                    )
                    self._halt("invalid_provider_result")
                    return None
                self.journal.complete(
                    reservation,
                    status=result.category,
                    request_class=request_class,
                    dispatched=None,
                    usage=result.usage,
                    metadata=copy.deepcopy(result.metadata),
                    counted_tokens=result.counted_tokens,
                    text=result.text,
                )
            if result.halt_reason:
                self._halt(result.halt_reason, ivf=result.ivf)
                halted = self._halted()
                self._last_failure = halted["reason"]
                if halted.get("inferential_failure") and not result.ivf:
                    self._flag("ivf", halted["reason"])
                if (
                    result.accept_received_on_halt
                    and halted["reason"] == "accounting_halt"
                    and not halted.get("inferential_failure")
                    and self._live()
                ):
                    return result, context
                return None
            if "halt_credential" in result.category or "contract_anomaly" in result.category:
                self._halt(result.category)
                return None
            # A sequential child can persist a halt and die or return an
            # apparently successful value. Durable state wins before parsing.
            halted = self._halted()
            if halted:
                self._last_failure = halted["reason"]
                if halted.get("inferential_failure"):
                    self._flag("ivf", halted["reason"])
                return None
            if not self._live():
                return None
            if result.category == "count_ok" or result.category in _RECEIVED:
                return result, context
            if result.category not in _RETRYABLE:
                self._last_failure = result.category
                return None
            if attempt == 3:
                self._last_failure = f"{request_class}_exhausted"
                return None
            if not self._wait_retry(result, attempt):
                return None
        return None

    def _logical(self, provider, request, batch, logical):
        self._last_failure = "logical_call_failed"
        halted = self._halted()
        if halted:
            self._last_failure = halted["reason"]
            self._event("request_not_sent", batch=batch, logical=logical, reason=self._last_failure)
            if halted.get("inferential_failure"):
                self._flag("ivf", halted["reason"])
            return None
        self._event("logical_started", batch=batch, logical=logical, request=request)
        try:
            pair = provider.prepare(copy.deepcopy(request))
            if not isinstance(pair, RequestPair):
                raise ValueError("prepare did not return immutable request pair")
        except Exception:
            self._halt("request_preparation_failed")
            return None
        counted = self._attempts(provider, pair, None, batch, logical, "count")
        if counted is None:
            return None
        result, context = counted
        receipt = CountReceipt(
            context.logical_key,
            hashlib.sha256(pair.count_body).hexdigest(),
            result.counted_tokens,
            context.reservation,
        )
        self._event("count_receipt", batch=batch, logical=logical, **receipt.__dict__)
        if receipt.counted_tokens > self.admission_limit:
            self._last_failure = "admission_rejected"
            self._event(
                "request_not_sent",
                batch=batch,
                logical=logical,
                reason=self._last_failure,
                counted_tokens=receipt.counted_tokens,
            )
            return None
        generated = self._attempts(provider, pair, receipt, batch, logical, "generation")
        return None if generated is None else generated[0].text
