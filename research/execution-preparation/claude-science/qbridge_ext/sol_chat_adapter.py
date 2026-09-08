"""Candidate OpenAI Chat Completions adapter for the protocol v0.4 LLM arm.

Status: CANDIDATE request contract and offline-testable adapter. It has never
sent a live request. Nothing here selects a provider for the study, closes a
readiness gate, authorizes spending, or freezes the manifest.

Contract (documentation retrieved 2026-09-08 from developers.openai.com; see
sol_chat_request_contract_2026-09-08.md for sources and hashes):

* endpoint  POST https://api.openai.com/v1/chat/completions (no regional base URL)
* model     "gpt-5.6-sol" exactly; the "gpt-5.6" routing alias is never sent
* messages  [{"role": "developer", "content": <system_v0.3.txt bytes>},
             {"role": "user",      "content": <rendered user message bytes>}]
            content is a plain string, so no content-part object exists on
            which a prompt_cache_breakpoint could be placed
* reasoning_effort      one explicit value fixed before any call (default
                        candidate "medium" = the documented Sol default, sent
                        explicitly so the request does not depend on the
                        omitted-default contract)
* max_completion_tokens 8192 (documented as inclusive of reasoning tokens)
* n 1, stream False, store False, service_tier "default"
* prompt_cache_options {"mode": "explicit"} with zero breakpoints, which the
  prompt-caching guide documents as not using caching or creating cache writes
* OMITTED (never sent): temperature, top_p, seed, tools, tool_choice,
  response_format, logprobs, top_logprobs, stop, prediction, metadata, user,
  safety_identifier, prompt_cache_key, prompt_cache_retention, verbosity,
  modalities, audio, web_search_options, parallel_tool_calls,
  frequency_penalty, presence_penalty, logit_bias, max_tokens (deprecated)

Transport: official openai-python SDK with max_retries=0; the per-attempt
timeout is supplied by the runner (<= 300 s) and enforced by the runner's
process executor as the outer boundary. The SDK timeout here is only an inner
hint. Retries, backoff, attempt caps and deadlines remain the runner's.

Mapping to qbridge.runner.TransportResponse:
  HTTP 2xx           -> TransportResponse(status, text, metadata, usage)
  HTTP 4xx/5xx/429   -> TransportResponse(status, "", metadata(error), None)
                        (runner retries only 429/5xx)
  connection failure -> ConnectionError  (runner retries)
  timeout            -> TimeoutError     (runner retries)
  anything else      -> ordinary exception (runner: client_error, no retry)
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import stat
import time
from datetime import datetime, timezone
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path

from qbridge_ext.study_coordinator import SpendLedger, validate_count, validate_money

ENDPOINT = "https://api.openai.com/v1/chat/completions"
MODEL = "gpt-5.6-sol"
MAX_COMPLETION_TOKENS = 8192
SUPPORTED_EFFORTS = ("none", "low", "medium", "high", "xhigh", "max")
CORRECTION_REASONS = ("invalid_json", "invalid_envelope", "no_valid_vectors")
FORBIDDEN_FIELDS = frozenset(
    {
        "temperature",
        "top_p",
        "seed",
        "tools",
        "tool_choice",
        "functions",
        "function_call",
        "response_format",
        "logprobs",
        "top_logprobs",
        "stop",
        "prediction",
        "metadata",
        "user",
        "safety_identifier",
        "prompt_cache_key",
        "prompt_cache_retention",
        "verbosity",
        "modalities",
        "audio",
        "web_search_options",
        "parallel_tool_calls",
        "frequency_penalty",
        "presence_penalty",
        "logit_bias",
        "max_tokens",
        "stream_options",
        "reasoning",
        "previous_response_id",
        "conversation",
    }
)
USAGE_CATEGORIES = (
    "prompt_tokens",
    "completion_tokens",
    "total_tokens",
    "reasoning_tokens",
    "cached_tokens",
    "cache_write_tokens",
    "prompt_text_tokens",
    "prompt_audio_tokens",
    "prompt_image_tokens",
    "completion_text_tokens",
    "completion_audio_tokens",
    "accepted_prediction_tokens",
    "rejected_prediction_tokens",
)


class ContractViolation(ValueError):
    """The request the runner supplied cannot be expressed under the contract."""


def build_request_body(request: dict, *, reasoning_effort: str) -> dict:
    """Translate the runner's {"system","user","max_tokens"} request literally.

    Prompt bytes are copied unchanged. Any deviation from the fixed contract
    raises instead of being silently repaired.
    """
    if set(request) != {"system", "user", "max_tokens"}:
        raise ContractViolation("runner request must have exactly system, user, max_tokens")
    if request["max_tokens"] != MAX_COMPLETION_TOKENS:
        raise ContractViolation("output cap must be exactly 8192")
    if reasoning_effort not in SUPPORTED_EFFORTS:
        raise ContractViolation("reasoning_effort must be one documented Sol value")
    for key in ("system", "user"):
        text = request[key]
        if not isinstance(text, str) or not text:
            raise ContractViolation(f"{key} must be a nonempty str")
        text.encode("ascii")  # prompts are ASCII by construction; refuse anything else
    body = {
        "model": MODEL,
        "messages": [
            {"role": "developer", "content": request["system"]},
            {"role": "user", "content": request["user"]},
        ],
        "reasoning_effort": reasoning_effort,
        "max_completion_tokens": MAX_COMPLETION_TOKENS,
        "n": 1,
        "stream": False,
        "store": False,
        "service_tier": "default",
        "prompt_cache_options": {"mode": "explicit"},
    }
    assert not (FORBIDDEN_FIELDS & body.keys())
    return body


def canonical_bytes(body: dict) -> bytes:
    return json.dumps(
        body, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False
    ).encode("ascii")


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def verify_serialized_body(sent: bytes, body: dict) -> None:
    """Assert the bytes an HTTP client actually sent equal the contract body."""
    parsed = json.loads(sent.decode("utf-8"))
    if parsed != body:
        raise ContractViolation("serialized request differs from contract body")
    if FORBIDDEN_FIELDS & parsed.keys():
        raise ContractViolation("forbidden field present in serialized request")
    for message in parsed["messages"]:
        if not isinstance(message["content"], str):
            raise ContractViolation("content must be a plain string (no breakpoint parts)")


def _int_or_none(value):
    return value if type(value) is int and value >= 0 else None


def usage_from_payload(payload: dict) -> dict:
    """Map Chat usage into the journal's flat category dict; absent -> None (unknown)."""
    usage = payload.get("usage") or {}
    ptd = usage.get("prompt_tokens_details") or {}
    ctd = usage.get("completion_tokens_details") or {}
    mapped = {
        "prompt_tokens": _int_or_none(usage.get("prompt_tokens")),
        "completion_tokens": _int_or_none(usage.get("completion_tokens")),
        "total_tokens": _int_or_none(usage.get("total_tokens")),
        "reasoning_tokens": _int_or_none(ctd.get("reasoning_tokens")),
        "cached_tokens": _int_or_none(ptd.get("cached_tokens")),
        "cache_write_tokens": _int_or_none(ptd.get("cache_write_tokens")),
        "prompt_text_tokens": _int_or_none(ptd.get("text_tokens")),
        "prompt_audio_tokens": _int_or_none(ptd.get("audio_tokens")),
        "prompt_image_tokens": _int_or_none(ptd.get("image_tokens")),
        "completion_text_tokens": _int_or_none(ctd.get("text_tokens")),
        "completion_audio_tokens": _int_or_none(ctd.get("audio_tokens")),
        "accepted_prediction_tokens": _int_or_none(ctd.get("accepted_prediction_tokens")),
        "rejected_prediction_tokens": _int_or_none(ctd.get("rejected_prediction_tokens")),
    }
    assert set(mapped) == set(USAGE_CATEGORIES)
    return mapped


def usage_checks(usage: dict, *, expect_no_cache: bool = True) -> list[str]:
    """Return contract findings (empty = none). Unknown categories are findings."""
    findings = []
    for key in ("prompt_tokens", "completion_tokens", "total_tokens"):
        if usage[key] is None:
            findings.append(f"{key}_unknown")
    completion = usage["completion_tokens"]
    if completion is not None and completion > MAX_COMPLETION_TOKENS:
        findings.append("completion_tokens_exceed_cap")
    reasoning = usage["reasoning_tokens"]
    if reasoning is not None and completion is not None and reasoning > completion:
        findings.append("reasoning_not_subset_of_completion")
    prompt, total = usage["prompt_tokens"], usage["total_tokens"]
    if None not in (prompt, completion, total) and prompt + completion != total:
        findings.append("total_mismatch")
    if expect_no_cache:
        for key in ("cached_tokens", "cache_write_tokens"):
            if usage[key] is None:
                findings.append(f"{key}_unknown")
            elif usage[key] != 0:
                findings.append(f"{key}_nonzero")
    return findings


def metadata_from_response(payload: dict, headers, *, status: int, raw_body: bytes) -> dict:
    """Identity and provenance fields recorded before parsing the text."""
    choices = payload.get("choices") or []
    first = choices[0] if choices else {}
    message = first.get("message") or {}
    lower = {str(k).lower(): v for k, v in dict(headers).items()}
    return {
        "http_status": status,
        "model": payload.get("model"),
        "system_fingerprint": payload.get("system_fingerprint"),
        "response_id": payload.get("id"),
        "created": payload.get("created"),
        "object": payload.get("object"),
        "service_tier": payload.get("service_tier"),
        "finish_reason": first.get("finish_reason"),
        "choice_count": len(choices),
        "refusal": message.get("refusal"),
        "content_is_string": isinstance(message.get("content"), str),
        "request_id_header": lower.get("x-request-id"),
        "processing_ms_header": lower.get("openai-processing-ms"),
        "ratelimit_remaining_requests": lower.get("x-ratelimit-remaining-requests"),
        "ratelimit_remaining_tokens": lower.get("x-ratelimit-remaining-tokens"),
        "raw_body_sha256": sha256(raw_body),
        "raw_body_bytes": len(raw_body),
        "requested_model": MODEL,
        "requested_endpoint": ENDPOINT,
    }


def identity_checks(metadata: dict, *, expected_effort: str) -> list[str]:
    findings = []
    if metadata.get("model") != MODEL:
        findings.append("model_mismatch")
    if metadata.get("system_fingerprint") in (None, ""):
        findings.append("system_fingerprint_absent")
    if metadata.get("service_tier") != "default":
        findings.append("service_tier_not_default")
    if metadata.get("choice_count") != 1:
        findings.append("choice_count_not_one")
    if metadata.get("finish_reason") == "length":
        findings.append("truncated_at_cap")
    if metadata.get("refusal"):
        findings.append("refusal_returned")
    # Chat Completions does not echo reasoning_effort; the effective decoding
    # setting is therefore only the request value, never a returned one.
    findings.append(f"effective_decoding_not_echoed:{expected_effort}")
    return findings


def profile_sha256(reasoning_effort: str) -> str:
    """Hash of the fixed request profile an authority record is bound to."""
    profile = {
        "endpoint": ENDPOINT,
        "model": MODEL,
        "reasoning_effort": reasoning_effort,
        "max_completion_tokens": MAX_COMPLETION_TOKENS,
        "n": 1,
        "store": False,
        "service_tier": "default",
        "prompt_cache_options": {"mode": "explicit"},
        "roles": ["developer", "user"],
    }
    return sha256(canonical_bytes(profile))


def _parse_utc(value) -> float:
    """Strict ISO-8601 UTC instant 'YYYY-MM-DDTHH:MM:SSZ' -> POSIX seconds."""
    if not isinstance(value, str) or not re.fullmatch(
        r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", value
    ):
        raise ValueError("price_valid_through_utc must be 'YYYY-MM-DDTHH:MM:SSZ'")
    return datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc).timestamp()


class PriceValidityExpired(RuntimeError):
    """The recorded rate-validity instant has passed; no dispatch without a new record."""


@dataclass(frozen=True)
class AuthorityRecord:
    """Every fact a live adapter needs, validated on construction (not only on load).

    The record binds: numeric ceiling, attempt cap, ledger scope (= policy
    name), request-profile hash, admitted input-token ceiling, the two
    strictly positive rates, the rate source and its validity instant. A
    ledger or transport whose values differ is refused before any dispatch;
    zero or missing rates are refused (a ceiling with unrelated rates is not
    an enforced ceiling).
    """

    usd_ceiling: str
    attempt_cap: int
    authorized_by: str
    recorded_at: str
    purpose: str
    scope: str
    profile_sha256: str
    price_valid_through_utc: str
    rate_source: str
    input_token_ceiling: int
    input_usd_per_million: str
    output_usd_per_million: str
    path: str = "<constructed>"

    FIELDS = (
        "usd_ceiling",
        "attempt_cap",
        "authorized_by",
        "recorded_at",
        "purpose",
        "scope",
        "profile_sha256",
        "price_valid_through_utc",
        "rate_source",
        "input_token_ceiling",
        "input_usd_per_million",
        "output_usd_per_million",
    )
    SCOPES = ("e9", "study")

    def __post_init__(self):
        validate_money(self.usd_ceiling, "usd_ceiling")
        validate_count(self.attempt_cap, "attempt_cap", 1, 1_000_000)
        for key in ("authorized_by", "recorded_at", "purpose", "rate_source"):
            value = getattr(self, key)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{key} must be a nonempty string naming the actual fact")
        if self.scope not in self.SCOPES:
            raise ValueError("scope must be 'e9' or 'study' (it names the halt policy)")
        if not isinstance(self.profile_sha256, str) or not re.fullmatch(
            r"[0-9a-f]{64}", self.profile_sha256
        ):
            raise ValueError("profile_sha256 must be the 64-hex profile hash")
        _parse_utc(self.price_valid_through_utc)
        validate_count(self.input_token_ceiling, "input_token_ceiling", 1, 1_000_000_000)
        for key in ("input_usd_per_million", "output_usd_per_million"):
            if validate_money(getattr(self, key), key) <= 0:
                raise ValueError(f"{key} must be strictly positive; fail closed without a rate")

    @classmethod
    def load(cls, path) -> "AuthorityRecord":
        data = json.loads(Path(path).read_bytes())
        if not isinstance(data, dict) or set(data) != set(cls.FIELDS):
            raise ValueError("authority record requires exactly " + ", ".join(cls.FIELDS))
        return cls(path=str(path), **data)

    def price_valid_at(self, when: float) -> bool:
        """True iff the POSIX time `when` is not after the recorded validity instant."""
        return when <= _parse_utc(self.price_valid_through_utc)

    def ledger(self, journal) -> SpendLedger:
        """The only sanctioned way to build the ledger: every value comes from here."""
        return SpendLedger(
            journal,
            ceiling_usd=self.usd_ceiling,
            input_token_ceiling=self.input_token_ceiling,
            input_usd_per_million=self.input_usd_per_million,
            output_usd_per_million=self.output_usd_per_million,
            scope=self.scope,
        )

    def matches_ledger(self, ledger) -> bool:
        return (
            isinstance(ledger, SpendLedger)
            and ledger.ceiling == Decimal(self.usd_ceiling)
            and ledger.scope == self.scope
            and ledger.L == self.input_token_ceiling
            and ledger.R_in == Decimal(self.input_usd_per_million)
            and ledger.R_out == Decimal(self.output_usd_per_million)
        )


class ProtectedStore:
    """Owner-only (0700) directory outside the public repo for raw request/response bytes.

    Files are written exclusively (never overwritten) BEFORE any parsing. The
    permission check is a protection against other accounts, not evidence of
    blindness (protocol §10.3 limitation applies).
    """

    def __init__(self, directory, *, public_repo):
        self.directory = Path(directory)
        info = self.directory.stat()
        if not stat.S_ISDIR(info.st_mode):
            raise ValueError("protected store must be a directory")
        if info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) & 0o077:
            raise ValueError("protected store must be owner-only (0700)")
        if self.directory.resolve().is_relative_to(Path(public_repo).resolve()):
            raise ValueError("protected store must be outside the public repository")
        self.public_repo = Path(public_repo)

    def write(self, name: str, data: bytes) -> str:
        path = self.directory / name
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        with os.fdopen(fd, "wb") as stream:
            stream.write(data)
        return sha256(data)


@dataclass(frozen=True)
class HaltPolicy:
    """Explicit live-validity transitions. Every field is decided, none defaulted.

    halt = refuse all further dispatch (LiveHalted, persisted in the journal);
    record = journal only.
    """

    name: str
    model_mismatch: str
    fingerprint_absent: str
    fingerprint_changed: str
    service_tier_not_default: str
    cache_nonzero: str
    completion_exceeds_cap: str
    usage_incomplete: str
    other_4xx: str

    def __post_init__(self):
        for key, value in self.__dict__.items():
            if key != "name" and value not in ("halt", "record"):
                raise ValueError(f"{key} must be 'halt' or 'record'")


# E9: identity absence is recorded (G-MODEL stays open) but contract breaks halt.
E9_POLICY = HaltPolicy(
    name="e9",
    model_mismatch="halt",
    fingerprint_absent="record",
    fingerprint_changed="halt",
    service_tier_not_default="halt",
    cache_nonzero="halt",
    completion_exceeds_cap="halt",
    usage_incomplete="record",
    other_4xx="halt",
)
# Study: identity changes are the runner's IVF business (§7.4, outcomes preserved);
# billing-contract breaks still halt spend.
STUDY_POLICY = HaltPolicy(
    name="study",
    model_mismatch="record",
    fingerprint_absent="record",
    fingerprint_changed="record",
    service_tier_not_default="halt",
    cache_nonzero="halt",
    completion_exceeds_cap="halt",
    usage_incomplete="record",
    other_4xx="record",
)
POLICIES = {"e9": E9_POLICY, "study": STUDY_POLICY}


class LiveHalted(RuntimeError):
    """The transport halted on a policy transition; no further requests are sent."""


class SolChatTransport:
    """Callable transport(request, timeout) for qbridge.runner.ArmRunner.

    Durable state: halt reason and fingerprint baseline live in the JOURNAL
    (events `live_halt`, `fingerprint_baseline`, scoped), never only in
    instance memory, because qbridge.runner.ProcessExecutor forks each attempt
    and discards the child's memory. Both are re-read before every dispatch.

    Pre-send enforcement: an httpx request hook compares the bytes actually
    about to leave the process with the intended contract body (every field,
    role and prompt string) and the endpoint URL; a mismatch persists the
    attempted bytes and reason durably, halts, and raises before dispatch.
    """

    def __init__(
        self,
        *,
        reasoning_effort: str,
        authority: AuthorityRecord,
        ledger: SpendLedger,
        store: ProtectedStore,
        policy: HaltPolicy,
        http_client=None,
        api_key_env: str = "QBRIDGE_OPENAI_API_KEY",
        api_key: str | None = None,
        wall_clock=time.time,
    ):
        if reasoning_effort not in SUPPORTED_EFFORTS:
            raise ContractViolation("reasoning_effort must be one documented Sol value")
        if not isinstance(authority, AuthorityRecord):
            raise ValueError("an AuthorityRecord is required")
        if not authority.matches_ledger(ledger):
            raise ValueError("ledger ceiling/scope/rates/input ceiling do not match the authority")
        if authority.profile_sha256 != profile_sha256(reasoning_effort):
            raise ValueError("authority record is bound to a different request profile")
        if not isinstance(store, ProtectedStore):
            raise ValueError("a ProtectedStore is required")
        if not isinstance(policy, HaltPolicy):
            raise ValueError("an explicit HaltPolicy is required")
        if policy != POLICIES.get(authority.scope):
            raise ValueError("policy must be the preset named by the authority scope")
        key = api_key if api_key is not None else os.environ.get(api_key_env)
        if not key:
            raise RuntimeError(
                f"no API key in {api_key_env}; live transport refused (no credential evidence)"
            )
        import httpx
        from openai import OpenAI  # lazy so offline modules never need the SDK

        self.effort = reasoning_effort
        self.authority = authority
        self.ledger = ledger
        self.journal = ledger.journal
        self.store = store
        self.policy = policy
        self.wall_clock = wall_clock
        self._intended = None  # (body dict, tag) for the in-flight attempt
        self._last_sent = None
        self._rejected = None

        if http_client is None:
            http_client = httpx.Client()
        hooks = list(http_client.event_hooks.get("request", []))
        http_client.event_hooks["request"] = hooks + [self._pre_send_hook]
        self.client = OpenAI(
            api_key=key,
            max_retries=0,
            base_url="https://api.openai.com/v1",
            http_client=http_client,
        )
        assert self.client.max_retries == 0

    # -- durable state ------------------------------------------------------

    def halted_reason(self):
        """Re-read from the journal every time (fork-safe)."""
        for event in self.journal.read_events():
            if event.get("kind") == "live_halt" and event.get("scope") == self.authority.scope:
                return event["reason"]
        return None

    def fingerprint_baseline(self):
        for event in self.journal.read_events():
            if (
                event.get("kind") == "fingerprint_baseline"
                and event.get("scope") == self.authority.scope
            ):
                return event["value"]
        return None

    def _halt(self, reason: str, **fields) -> None:
        if self.halted_reason() is None:
            self.journal.append(
                "live_halt",
                scope=self.authority.scope,
                policy=self.policy.name,
                purpose=self.authority.purpose,
                reason=reason,
                **fields,
            )

    # -- pre-send enforcement (runs inside whichever process dispatches) -----

    def _pre_send_hook(self, request) -> None:
        sent = bytes(request.content)
        self._last_sent = sent
        body, tag = self._intended
        reason = None
        if request.method != "POST" or str(request.url) != ENDPOINT:
            reason = "endpoint_or_method_mismatch"
        else:
            try:
                verify_serialized_body(sent, body)
            except (ContractViolation, ValueError, UnicodeDecodeError) as exc:
                reason = f"serialized_request_mismatch:{exc}"
        if reason is not None:
            digest = self.store.write(f"{tag}.rejected_request.json", sent)
            self.journal.append(
                "request_rejected_before_dispatch",
                scope=self.authority.scope,
                key=tag,
                reason=reason,
                attempted_sha256=digest,
                url=str(request.url),
            )
            self._halt("sent_bytes_violate_contract", key=tag)
            self._rejected = (digest, reason)
            raise ContractViolation(reason)

    def _transition(self, findings: list[str], meta: dict) -> None:
        mapping = {
            "model_mismatch": self.policy.model_mismatch,
            "system_fingerprint_absent": self.policy.fingerprint_absent,
            "system_fingerprint_changed": self.policy.fingerprint_changed,
            "service_tier_not_default": self.policy.service_tier_not_default,
            "cached_tokens_nonzero": self.policy.cache_nonzero,
            "cache_write_tokens_nonzero": self.policy.cache_nonzero,
            "completion_tokens_exceed_cap": self.policy.completion_exceeds_cap,
            "usage_incomplete": self.policy.usage_incomplete,
        }
        halts = [f for f in findings if mapping.get(f) == "halt"]
        meta["policy_actions"] = {f: mapping.get(f, "record") for f in findings}
        if halts:
            self._halt(halts[0], findings=findings)
        meta["halted_after_this_attempt"] = self.halted_reason()

    def __call__(self, request: dict, timeout: float):
        import httpx
        import openai

        from qbridge.runner import TransportResponse

        # Re-validate bindings every dispatch: mutable ledger values must not diverge.
        if not self.authority.matches_ledger(self.ledger):
            self._halt("ledger_diverged_from_authority")
            raise LiveHalted("ledger_diverged_from_authority")
        halted = self.halted_reason()
        if halted is not None:
            raise LiveHalted(halted)
        if self.ledger.totals()["halted"]:
            self._halt("ledger_overrun")
            raise LiveHalted("ledger_overrun")
        body = build_request_body(request, reasoning_effort=self.effort)
        # Price validity is checked before EVERY dispatch, including retries and requests
        # inside an already started block. Expiry -> request not sent (forfeit path).
        if not self.authority.price_valid_at(self.wall_clock()):
            raise PriceValidityExpired(self.authority.price_valid_through_utc)
        # Reserve one attempt against the authority BEFORE any network I/O; may raise
        # MonetaryCeilingReached / LedgerHalted (ordinary exceptions -> runner client_error).
        key = self.ledger.reserve_attempt(cap=self.authority.attempt_cap)
        tag = key.replace(":", "_")
        self._intended = (body, tag)
        self._last_sent = None
        self._rejected = None
        started = time.monotonic()
        try:
            raw = self.client.with_options(
                timeout=httpx.Timeout(timeout, connect=min(10.0, timeout)), max_retries=0
            ).chat.completions.with_raw_response.create(**body)
        except openai.APITimeoutError as exc:
            self._retain_request(tag)
            self.ledger.record_outcome(status="timeout", usage=None)
            raise TimeoutError(str(exc)) from exc
        except openai.APIConnectionError as exc:
            if self._rejected is not None:
                # The pre-send hook refused the request: nothing was dispatched.
                digest, reason = self._rejected
                self.ledger.record_outcome(status="rejected_before_dispatch", usage=None)
                raise ContractViolation(reason) from exc
            self._retain_request(tag)
            self.ledger.record_outcome(status="connection_error", usage=None)
            raise ConnectionError(str(exc)) from exc
        except openai.APIStatusError as exc:
            response = exc.response
            raw_body = response.content
            meta = self._retain(tag, raw_body, response.headers, response.status_code)
            payload = _safe_json(raw_body)
            meta.update(
                metadata_from_response(
                    payload, response.headers, status=response.status_code, raw_body=raw_body
                )
            )
            meta["error"] = payload.get("error")
            meta["elapsed_s"] = time.monotonic() - started
            self.ledger.record_outcome(status=f"http_{response.status_code}", usage=None)
            retryable = response.status_code == 429 or 500 <= response.status_code < 600
            if not retryable and self.policy.other_4xx == "halt":
                self._halt(f"http_{response.status_code}", key=tag)
            meta["halted_after_this_attempt"] = self.halted_reason()
            return TransportResponse(
                status=response.status_code, text="", metadata=meta, usage=None
            )
        http_response = raw.http_response
        raw_body = http_response.content
        # Retain original bytes in protected storage BEFORE parsing anything.
        meta = self._retain(tag, raw_body, http_response.headers, http_response.status_code)
        payload = _safe_json(raw_body)
        usage = usage_from_payload(payload)
        meta.update(
            metadata_from_response(
                payload,
                http_response.headers,
                status=http_response.status_code,
                raw_body=raw_body,
            )
        )
        meta["elapsed_s"] = time.monotonic() - started
        findings = usage_checks(usage) + identity_checks(meta, expected_effort=self.effort)
        fp = meta.get("system_fingerprint")
        if fp:
            baseline = self.fingerprint_baseline()
            if baseline is None:
                self.journal.append("fingerprint_baseline", scope=self.authority.scope, value=fp)
            elif fp != baseline:
                findings.append("system_fingerprint_changed")
        verdict = self.ledger.record_outcome(status="response", usage=usage)
        if not verdict["usage_known"]:
            findings.append("usage_incomplete")
        findings += [f"ledger_overrun:{o}" for o in verdict["overrun"]]
        meta["findings"] = findings
        meta["ledger"] = {k: str(v) for k, v in verdict.items()}
        self._transition(findings, meta)
        if verdict["overrun"]:
            self._halt("ledger_overrun", key=tag)
            meta["halted_after_this_attempt"] = self.halted_reason()
        choices = payload.get("choices") or []
        content = choices[0].get("message", {}).get("content") if choices else None
        text = content if isinstance(content, str) else ""
        return TransportResponse(
            status=http_response.status_code, text=text, metadata=meta, usage=usage
        )

    # -- retention helpers -------------------------------------------------

    def _retain_request(self, tag: str) -> dict:
        sent = self._last_sent
        meta = {"sent_request_retained": False, "sent_request_sha256": None}
        if sent is not None:
            meta["sent_request_sha256"] = self.store.write(f"{tag}.request.json", sent)
            meta["sent_request_retained"] = True
            meta["sent_request_verified_pre_send"] = True  # the hook would have raised otherwise
        return meta

    def _retain(self, tag: str, raw_body: bytes, headers, status: int) -> dict:
        meta = self._retain_request(tag)
        meta["response_body_sha256"] = self.store.write(f"{tag}.response.body", raw_body)
        header_bytes = canonical_bytes(
            {
                "status": status,
                "headers": {
                    str(k).lower(): str(v)
                    for k, v in dict(headers).items()
                    if str(k).lower() not in ("authorization", "set-cookie")
                },
            }
        )
        meta["response_headers_sha256"] = self.store.write(
            f"{tag}.response.headers.json", header_bytes
        )
        meta["retained_before_parse"] = True
        return meta


def _safe_json(raw: bytes) -> dict:
    try:
        payload = json.loads(raw.decode("utf-8"))
    except ValueError:
        return {}
    return payload if isinstance(payload, dict) else {}
