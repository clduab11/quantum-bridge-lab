"""Reference (non-integrated) functions for the PROPOSED counted-Responses
admission contract, revision 2 (after Codex technical review, 2026-09-08).

Status: draft for review; never sent a request; not part of qbridge or
qbridge_ext; does not select a provider, close a gate, authorize spending,
freeze anything, or claim integration with the existing components.

Documentation basis (retrieved 2026-09-08, hashes in
documentation_sources_2026-09-08.json): POST /v1/responses/input_tokens
"accepts the same input format as the Responses API" and "returns the exact
count the model will receive"; its response carries only `object` and
`input_tokens` (SDK 3.9.0 InputTokenCountResponse) - no model field.
openai-python 3.9.0 InputTokenCountParams keys = {conversation, input,
instructions, model, parallel_tool_calls, personality, previous_response_id,
reasoning, text, tool_choice, tools, truncation}.
"""

from __future__ import annotations

import copy
import hashlib
import json
import math
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation, localcontext
from email.utils import parsedate_to_datetime
from fractions import Fraction

GENERATION_ENDPOINT = "https://api.openai.com/v1/responses"
COUNT_ENDPOINT = "https://api.openai.com/v1/responses/input_tokens"
MODEL = "gpt-5.6-sol"
MAX_OUTPUT_TOKENS = 8192
# Model-specific set from the gpt-5.6-sol model page (sol_model.md, SHA-256 6aaf0b71...):
# "Reasoning.effort supports: none, low, medium (default), high, xhigh, and max".
# The generic Responses enum also lists "minimal"; it is NOT documented for Sol and is
# therefore refused here rather than assumed (same set as the Chat candidate adapter).
SUPPORTED_EFFORTS = ("none", "low", "medium", "high", "xhigh", "max")
ATTEMPT_TIMEOUT_S = 300
FIXED_BACKOFF_S = {1: 5, 2: 20}  # after attempt 1, after attempt 2
DISPATCH_MARGIN_S = (
    1  # fixed by the amendment (§7.2): wait + 1 s must fit the remaining deadline
)

COUNT_SCHEMA_KEYS = frozenset(
    {
        "conversation",
        "input",
        "instructions",
        "model",
        "parallel_tool_calls",
        "personality",
        "previous_response_id",
        "reasoning",
        "text",
        "tool_choice",
        "tools",
        "truncation",
    }
)
COUNT_PROJECTION_KEYS = frozenset({"model", "input", "reasoning", "text", "truncation"})
GENERATION_ONLY_ALLOWED = frozenset(
    {"max_output_tokens", "store", "stream", "service_tier", "prompt_cache_options"}
)


class ContractViolation(ValueError):
    """The request cannot be expressed under the contract; nothing is dispatched."""


# ----------------------------------------------------------------- helpers
def _strict_int(v) -> bool:
    return isinstance(v, int) and not isinstance(v, bool)


def _strict_bool(v) -> bool:
    return isinstance(v, bool)


def canonical_bytes(body) -> bytes:
    return json.dumps(
        body, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("ascii")


def sha256(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def _no_duplicate_keys(pairs):
    d = {}
    for k, v in pairs:
        if k in d:
            raise ValueError(f"duplicate JSON key: {k!r}")
        d[k] = v
    return d


def parse_json_strict(raw: bytes):
    """Parse provider bytes; duplicate keys at any depth are an anomaly, never accepted.
    Returns (obj, None) or (None, reason)."""
    try:
        return json.loads(
            raw.decode("utf-8"), object_pairs_hook=_no_duplicate_keys
        ), None
    except (UnicodeDecodeError, ValueError) as e:
        return None, f"malformed_json:{type(e).__name__}"


# ----------------------------------------------------------- request bodies
def build_generation_body(
    system_text: str, user_text: str, *, reasoning_effort: str
) -> dict:
    """Literal translation of the runner request into the PROPOSED Responses body."""
    if reasoning_effort not in SUPPORTED_EFFORTS:
        raise ContractViolation("reasoning effort must be one documented Sol value")
    for name, text in (("system", system_text), ("user", user_text)):
        if not isinstance(text, str) or not text:
            raise ContractViolation(f"{name} text must be a nonempty str")
        text.encode("ascii")
    return {
        "model": MODEL,
        "input": [
            {"role": "developer", "content": system_text},
            {"role": "user", "content": user_text},
        ],
        "reasoning": {"effort": reasoning_effort},
        "text": {"verbosity": "medium"},
        "truncation": "disabled",
        "max_output_tokens": MAX_OUTPUT_TOKENS,
        "store": False,
        "stream": False,
        "service_tier": "default",
        "prompt_cache_options": {"mode": "explicit"},
    }


def validate_generation_body(g: dict, *, reasoning_effort: str) -> None:
    """Full canonical-profile validation: every key, every value, strict types, no extras."""
    if not isinstance(g, dict):
        raise ContractViolation("generation body must be a dict")
    expected_keys = COUNT_PROJECTION_KEYS | GENERATION_ONLY_ALLOWED
    if set(g) != expected_keys:
        raise ContractViolation(
            f"generation body keys must be exactly {sorted(expected_keys)}"
        )
    if reasoning_effort not in SUPPORTED_EFFORTS:
        raise ContractViolation("reasoning effort must be one documented Sol value")
    if g["model"] != MODEL:
        raise ContractViolation("model must be exactly gpt-5.6-sol")
    inp = g["input"]
    if not (isinstance(inp, list) and len(inp) == 2):
        raise ContractViolation("input must be exactly two items")
    for item, role in zip(inp, ("developer", "user")):
        if not (isinstance(item, dict) and set(item) == {"role", "content"}):
            raise ContractViolation("input items must have exactly role and content")
        if item["role"] != role:
            raise ContractViolation(
                f"input roles must be developer then user, got {item['role']!r}"
            )
        c = item["content"]
        if not isinstance(c, str) or not c:
            raise ContractViolation("content must be a nonempty plain string")
        try:
            c.encode("ascii")
        except UnicodeEncodeError as e:
            raise ContractViolation("content must be ASCII") from e
    if g["reasoning"] != {"effort": reasoning_effort}:
        raise ContractViolation("reasoning must be exactly {'effort': <fixed effort>}")
    if g["text"] != {"verbosity": "medium"}:
        raise ContractViolation("text must be exactly {'verbosity': 'medium'}")
    if g["truncation"] != "disabled":
        raise ContractViolation("truncation must be 'disabled'")
    if not (
        _strict_int(g["max_output_tokens"])
        and g["max_output_tokens"] == MAX_OUTPUT_TOKENS
    ):
        raise ContractViolation("max_output_tokens must be the int 8192")
    if not (_strict_bool(g["store"]) and g["store"] is False):
        raise ContractViolation("store must be the bool False")
    if not (_strict_bool(g["stream"]) and g["stream"] is False):
        raise ContractViolation("stream must be the bool False")
    if g["service_tier"] != "default":
        raise ContractViolation("service_tier must be 'default'")
    if g["prompt_cache_options"] != {"mode": "explicit"}:
        raise ContractViolation(
            "prompt_cache_options must be exactly {'mode': 'explicit'}"
        )


def project_count_body(g: dict, *, reasoning_effort: str) -> dict:
    """Exact projection onto the count schema. Validates the full profile first and
    returns a deep copy (no aliasing of nested objects)."""
    validate_generation_body(g, reasoning_effort=reasoning_effort)
    c = {k: copy.deepcopy(g[k]) for k in sorted(g) if k in COUNT_SCHEMA_KEYS}
    if set(c) != COUNT_PROJECTION_KEYS:
        raise ContractViolation(
            "count projection must be exactly the five input-affecting keys"
        )
    return c


def bind_pair(g: dict, *, reasoning_effort: str) -> dict:
    """Validate G, project C, and bind immutable canonical bytes + hashes for both.
    Later dispatch must send exactly these bytes."""
    c = project_count_body(g, reasoning_effort=reasoning_effort)
    gb, cb = canonical_bytes(g), canonical_bytes(c)
    verify_pair(g, c, reasoning_effort=reasoning_effort)
    return {
        "generation_bytes": gb,
        "count_bytes": cb,
        "generation_sha256": sha256(gb),
        "count_sha256": sha256(cb),
    }


def verify_pair(g: dict, c: dict, *, reasoning_effort: str) -> None:
    """Count-to-send identity with full value validation (not key presence only)."""
    validate_generation_body(g, reasoning_effort=reasoning_effort)
    if not isinstance(c, dict) or set(c) != COUNT_PROJECTION_KEYS:
        raise ContractViolation(
            "count body keys must be exactly the five input-affecting keys"
        )
    expected = project_count_body(g, reasoning_effort=reasoning_effort)
    if canonical_bytes(c) != canonical_bytes(expected):
        raise ContractViolation(
            "count body is not the exact projection of the generation body"
        )


def verify_sent_bytes(sent: bytes, bound: bytes, url: str, expected_url: str) -> None:
    """Pre-send hook semantics: exact bytes and exact URL or no dispatch."""
    if url != expected_url:
        raise ContractViolation(f"wrong endpoint {url!r}")
    if sent != bound:
        raise ContractViolation("outgoing bytes differ from the bound canonical body")


# ---------------------------------------------------------------- admission
def admit(counted_input_tokens, admission_limit) -> str:
    """'admitted' or 'admission_rejected'. Never truncates. Both arguments strict ints."""
    if not _strict_int(counted_input_tokens) or counted_input_tokens < 0:
        raise ContractViolation("counted input_tokens must be a non-negative int")
    if not _strict_int(admission_limit) or admission_limit <= 0:
        raise ContractViolation(
            "admission limit must be a positive int fixed before exposure"
        )
    return (
        "admitted" if counted_input_tokens <= admission_limit else "admission_rejected"
    )


def validate_count_payload(payload) -> tuple[int | None, list[str]]:
    """Returns (input_tokens or None, findings). Only `object` and `input_tokens` are
    documented; missing/invalid fields are anomalies; extra fields are recorded."""
    findings = []
    if not isinstance(payload, dict):
        return None, ["count_payload_not_object"]
    if payload.get("object") != "response.input_tokens":
        findings.append("count_object_field_invalid")
    it = payload.get("input_tokens")
    if not _strict_int(it) or it < 0:
        findings.append("count_input_tokens_invalid")
        it = None
    extra = sorted(set(payload) - {"object", "input_tokens"})
    if extra:
        findings.append(f"count_extra_fields:{','.join(extra)}")
    if "count_object_field_invalid" in findings or it is None:
        return None, findings
    return it, findings


# ------------------------------------------------------- outcome classification
RETRYABLE_TRANSPORT_ERRORS = frozenset({"connection", "timeout"})
RETRYABLE_RESPONSE_ERROR_CODES = frozenset({"server_error", "rate_limit_exceeded"})
CREDENTIAL_STATUSES = frozenset({401, 402, 403})


def _status_bucket(http_status, transport_error):
    """Shared, explicit bucketing. Unknown inputs are anomalies, never retryable."""
    if transport_error is not None:
        if transport_error in RETRYABLE_TRANSPORT_ERRORS:
            return "retryable"
        return "anomaly"
    if not _strict_int(http_status):
        return "anomaly"
    if http_status == 429 or 500 <= http_status <= 599:
        return "retryable"
    if http_status in CREDENTIAL_STATUSES:
        return "credential"
    if 400 <= http_status <= 499:
        return "terminal"
    if 200 <= http_status <= 299:
        return "ok"
    return "anomaly"


def classify_count_outcome(http_status, payload, transport_error=None):
    """(category, retryable) for the COUNT class.
    count_ok | count_retryable | count_halt_credential | count_terminal | count_contract_anomaly"""
    b = _status_bucket(http_status, transport_error)
    if b == "retryable":
        return "count_retryable", True
    if b == "credential":
        return "count_halt_credential", False
    if b == "terminal":
        return "count_terminal", False
    if b == "ok":
        it, _findings = validate_count_payload(payload)
        return (
            ("count_ok", False) if it is not None else ("count_contract_anomaly", False)
        )
    return "count_contract_anomaly", False


def classify_generation_outcome(http_status, payload, transport_error=None):
    """(category, retryable) for the GENERATION class under Responses.
    received_completed | received_incomplete | gen_failed_retryable | gen_failed_terminal |
    gen_retryable | gen_halt_credential | gen_terminal | gen_contract_anomaly.
    A 2xx `failed` object is still an object whose usage/metadata must be recorded
    before any retry (see settle_response)."""
    b = _status_bucket(http_status, transport_error)
    if b == "retryable":
        return "gen_retryable", True
    if b == "credential":
        return "gen_halt_credential", False
    if b == "terminal":
        return "gen_terminal", False
    if b != "ok" or not isinstance(payload, dict):
        return "gen_contract_anomaly", False
    status = payload.get("status")
    if status == "completed":
        return "received_completed", False
    if status == "incomplete":
        return "received_incomplete", False
    if status == "failed":
        err = payload.get("error")
        code = err.get("code") if isinstance(err, dict) else None
        if code in RETRYABLE_RESPONSE_ERROR_CODES:
            return "gen_failed_retryable", True
        return "gen_failed_terminal", False
    return "gen_contract_anomaly", False


# ------------------------------------------------------------ Retry-After
def parse_retry_after(value, response_date_header, receipt_time_utc: datetime):
    """Returns (seconds_or_None, finding_or_None).
    delta-seconds: non-negative integer string. HTTP-date: RFC 7231; the wait is measured
    from the server's Date header when present and parseable, else from receipt time.
    Negative/malformed values are findings, not silently ignored. `retry-after-ms` is
    NOT interpreted (no documentation evidence) - callers record it only."""
    if value is None:
        return None, None
    s = str(value).strip()
    if s.isdigit():
        return int(s), None
    try:
        when = parsedate_to_datetime(s)
    except (TypeError, ValueError, IndexError):
        return None, "retry_after_malformed"
    if when.tzinfo is None:
        when = when.replace(tzinfo=timezone.utc)
    ref = None
    if response_date_header:
        try:
            ref = parsedate_to_datetime(str(response_date_header))
            if ref.tzinfo is None:
                ref = ref.replace(tzinfo=timezone.utc)
        except (TypeError, ValueError, IndexError):
            ref = None
    if ref is None:
        ref = receipt_time_utc
    delta = (when - ref).total_seconds()
    if delta < 0:
        return 0, "retry_after_date_in_past"
    return int(delta + 0.999999), None


def retry_decision(
    attempt_no,
    retry_after_s,
    retry_after_finding,
    remaining_deadline_s,
):
    """Predetermined, non-selective retry rule.
    Returns (retry: bool, wait_s: int | None, reason: str).
    Retry only if attempt_no in {1, 2}, the server minimum (if any) is honoured in full
    (never capped downward), the total wait is <= ATTEMPT_TIMEOUT_S, and wait + margin
    fits a finite, known remaining arm deadline (margin fixed at DISPATCH_MARGIN_S = 1 s).
    Malformed Retry-After => no retry.
    Bool/non-int attempt numbers and non-int waits are contract violations."""
    if not _strict_int(attempt_no) or attempt_no < 1:
        raise ContractViolation("attempt_no must be a positive int (not bool)")
    if retry_after_s is not None and (
        not _strict_int(retry_after_s) or retry_after_s < 0
    ):
        raise ContractViolation("retry_after_s must be None or a non-negative int")
    if attempt_no not in FIXED_BACKOFF_S:
        return False, None, "attempts_exhausted"
    if retry_after_finding == "retry_after_malformed":
        return False, None, "retry_after_malformed"
    if remaining_deadline_s is None or isinstance(remaining_deadline_s, bool):
        return False, None, "remaining_deadline_unknown"
    if not isinstance(remaining_deadline_s, (int, float)) or not math.isfinite(
        remaining_deadline_s
    ):
        return False, None, "remaining_deadline_invalid"
    wait = max(FIXED_BACKOFF_S[attempt_no], retry_after_s or 0)
    if wait > ATTEMPT_TIMEOUT_S:
        return False, None, "retry_after_exceeds_attempt_cap"
    if wait + DISPATCH_MARGIN_S > remaining_deadline_s:
        return False, None, "deadline_insufficient"
    return True, wait, "retry"


# -------------------------------------------------- identity and usage checks
# Required echo fields: must be present and equal the expected profile value (strict type).
REQUIRED_ECHO = {
    "object": "response",
    "model": MODEL,
    "service_tier": "default",
    "truncation": "disabled",
    "max_output_tokens": MAX_OUTPUT_TOKENS,
    "store": False,
}
# Required nested values inside frozen objects (effort bound at validation time).
REQUIRED_NESTED_ECHO = {
    ("reasoning", "effort"): None,
    ("text", "verbosity"): "medium",
    ("prompt_cache_options", "mode"): "explicit",
}
# Optional fields with SAFE value sets: absent or one of the listed values; anything else
# is a profile failure even on the first (baseline) response.
OPTIONAL_SAFE = {
    "background": (False,),
    "tools": ([],),
}
# Optional fields recorded verbatim (any value), then frozen by the baseline.
OPTIONAL_FREE = ("temperature", "top_p")
# Whole frozen objects compared canonically so that new nested fields cannot escape drift checks.
FROZEN_OBJECTS = ("reasoning", "text", "prompt_cache_options")
IDENTITY_KEYS = (
    tuple(REQUIRED_ECHO) + tuple(OPTIONAL_SAFE) + OPTIONAL_FREE + FROZEN_OBJECTS
)

_ABSENT = object()


def _lookup(payload, key):
    if isinstance(key, tuple):
        outer = payload.get(key[0], _ABSENT)
        if not isinstance(outer, dict):
            return _ABSENT
        return outer.get(key[1], _ABSENT)
    return payload.get(key, _ABSENT)


def _tag(v):
    """Presence-tagged canonical value: ('absent',) or ('present', canonical-json-string)."""
    if v is _ABSENT:
        return ("absent",)
    return ("present", canonical_bytes(v).decode("ascii"))


def identity_vector(payload: dict) -> dict:
    """Presence-tagged canonical identity vector over top-level fields and whole frozen
    objects. Not a validation; see validate_expected_profile."""
    if not isinstance(payload, dict):
        raise ContractViolation("identity_vector requires a Response object")
    return {k: _tag(_lookup(payload, k)) for k in IDENTITY_KEYS}


def validate_expected_profile(payload, *, reasoning_effort: str) -> list[str]:
    """Step 1 (before any baseline is accepted): required echo fields equal the frozen
    profile (strict types), required nested values match, optional-safe fields are absent
    or safe, frozen objects are dicts. Findings: profile_echo_missing:<f>,
    profile_echo_mismatch:<f>, profile_unsafe_value:<f>."""
    if reasoning_effort not in SUPPORTED_EFFORTS:
        raise ContractViolation("reasoning effort must be one documented Sol value")
    if not isinstance(payload, dict):
        return ["response_not_object"]
    findings = []
    for k, exp in REQUIRED_ECHO.items():
        v = _lookup(payload, k)
        if v is _ABSENT:
            findings.append(f"profile_echo_missing:{k}")
        elif type(v) is not type(exp) or v != exp:
            findings.append(f"profile_echo_mismatch:{k}")
    nested = dict(REQUIRED_NESTED_ECHO)
    nested[("reasoning", "effort")] = reasoning_effort
    for k, exp in nested.items():
        v = _lookup(payload, k)
        if v is _ABSENT:
            findings.append(f"profile_echo_missing:{k[0]}.{k[1]}")
        elif type(v) is not type(exp) or v != exp:
            findings.append(f"profile_echo_mismatch:{k[0]}.{k[1]}")
    for k, safe in OPTIONAL_SAFE.items():
        v = _lookup(payload, k)
        if v is _ABSENT:
            continue
        if not any(type(v) is type(sv) and v == sv for sv in safe):
            findings.append(f"profile_unsafe_value:{k}")
    for k in FROZEN_OBJECTS:
        v = _lookup(payload, k)
        if v is not _ABSENT and not isinstance(v, dict):
            findings.append(f"profile_echo_mismatch:{k}")
    return findings


def compare_identity(vector: dict, baseline: dict) -> list[str]:
    """Step 2 (study): any change, appearance or disappearance vs the validated baseline,
    over every identity key (a key missing from either side is itself a change)."""
    keys = set(vector) | set(baseline)
    return sorted(
        f"identity_change:{k}" for k in keys if vector.get(k) != baseline.get(k)
    )


# ------------------------------------------------------------------ money
RATE_NAMES = ("input", "cached_input", "cache_write", "output")
MAX_RATE_USD_PER_TOKEN = Fraction(
    1, 1
)  # bounded grammar: no rate may reach 1 USD per token
POLICIES = frozenset({"e9", "study"})


def _to_fraction(v, name):
    """Exact conversion independent of ambient Decimal context. Accepts Fraction, int
    (not bool), Decimal, or a decimal string; rejects floats, NaN, infinities."""
    if isinstance(v, (bool, float)):
        raise ContractViolation(
            f"{name}: floats and bools are not an exact money grammar"
        )
    if isinstance(v, Fraction):
        return v
    if isinstance(v, int):
        return Fraction(v)
    if isinstance(v, Decimal):
        if not v.is_finite():
            raise ContractViolation(f"{name}: non-finite Decimal")
        return Fraction(v)
    if isinstance(v, str):
        try:
            with localcontext() as ctx:
                ctx.prec = 60
                ctx.traps[InvalidOperation] = True
                d = Decimal(v.strip())
        except (InvalidOperation, ValueError) as e:
            raise ContractViolation(f"{name}: not a decimal string") from e
        if not d.is_finite():
            raise ContractViolation(f"{name}: non-finite value")
        return Fraction(d)
    raise ContractViolation(f"{name}: unsupported money type {type(v).__name__}")


def validate_rates(rates) -> dict:
    """USD per TOKEN, exact Fractions, strictly positive, finite, bounded; exactly the four
    documented categories. Returns a fresh validated dict."""
    if not isinstance(rates, dict) or set(rates) != set(RATE_NAMES):
        raise ContractViolation(f"rates must have exactly {RATE_NAMES}")
    out = {}
    for k in RATE_NAMES:
        f = _to_fraction(rates[k], f"rate {k}")
        if f <= 0 or f >= MAX_RATE_USD_PER_TOKEN:
            raise ContractViolation(
                f"rate {k} must be in (0, {MAX_RATE_USD_PER_TOKEN}) USD per token"
            )
        out[k] = f
    return out


def rates_per_million(input_usd, cached_usd, cache_write_usd, output_usd) -> dict:
    """Build per-token rates from documented per-million figures (decimal strings)."""
    m = Fraction(1_000_000)
    return validate_rates(
        {
            "input": _to_fraction(input_usd, "input") / m,
            "cached_input": _to_fraction(cached_usd, "cached_input") / m,
            "cache_write": _to_fraction(cache_write_usd, "cache_write") / m,
            "output": _to_fraction(output_usd, "output") / m,
        }
    )


def money_str(f: Fraction, places: int = 6) -> str:
    """Exact-to-places rendering in a fresh high-precision context (never the ambient one).
    Raises if the value does not terminate within `places` (no silent rounding)."""
    if not isinstance(f, Fraction):
        raise ContractViolation("money_str expects a Fraction")
    scaled = f * (10**places)
    if scaled.denominator != 1:
        raise ContractViolation(
            "value does not terminate at the requested places; do not round silently"
        )
    with localcontext() as ctx:
        ctx.prec = 60
        return str(Decimal(scaled.numerator).scaleb(-places))


def charge_from_usage(usage, rates) -> Fraction | None:
    """Applicable-rate charge, exact Fraction, unclipped; None if any needed category is
    unknown. Rates are validated on every call."""
    r = validate_rates(rates)
    if not isinstance(usage, dict):
        return None
    it, ot = usage.get("input_tokens"), usage.get("output_tokens")
    d = usage.get("input_tokens_details")
    if not (_strict_int(it) and _strict_int(ot) and isinstance(d, dict)):
        return None
    cached, written = d.get("cached_tokens"), d.get("cache_write_tokens")
    if not (_strict_int(cached) and _strict_int(written)):
        return None
    if it < 0 or ot < 0 or cached < 0 or written < 0:
        return None
    ordinary = it - cached - written
    if ordinary < 0:
        return None
    return (
        Fraction(ordinary) * r["input"]
        + Fraction(cached) * r["cached_input"]
        + Fraction(written) * r["cache_write"]
        + Fraction(ot) * r["output"]
    )


def reservation_for_generation(counted_input_tokens, rates) -> Fraction:
    """Exact input at the uncached rate + full output cap at the output rate (Fraction)."""
    r = validate_rates(rates)
    if not _strict_int(counted_input_tokens) or counted_input_tokens < 0:
        raise ContractViolation("counted input tokens must be a non-negative int")
    return (
        Fraction(counted_input_tokens) * r["input"]
        + Fraction(MAX_OUTPUT_TOKENS) * r["output"]
    )


def _validate_reservation(reservation):
    if not isinstance(reservation, Fraction) or reservation <= 0:
        raise ContractViolation(
            "reservation must be a positive Fraction from reservation_for_generation"
        )


MANDATORY_USAGE = ("input_tokens", "output_tokens", "total_tokens")
MANDATORY_DETAILS = ("cached_tokens", "cache_write_tokens")
# Findings that make a usage report NOT fully reconciled (accounting, not IVF).
ACCOUNTING_FINDING_PREFIXES = (
    "usage_missing_unknown",
    "input_tokens_unknown",
    "output_tokens_unknown",
    "total_tokens_unknown",
    "total_tokens_inconsistent",
    "input_tokens_details_unknown",
    "cached_tokens_unknown",
    "cache_write_tokens_unknown",
    "cache_categories_exceed_input",
)
IVF_FINDING_PREFIXES = ("count_usage_mismatch", "cache_activity")


def _nonneg_int(v) -> bool:
    return _strict_int(v) and v >= 0


def usage_checks(payload, counted_input_tokens) -> list[str]:
    """Findings for any 2xx Response object (completed, incomplete or failed).
    Mandatory: input_tokens, output_tokens, total_tokens (strict non-negative ints),
    input_tokens_details.cached_tokens and .cache_write_tokens, and the reconciliation
    total_tokens == input_tokens + output_tokens (the provider's own spending-controller
    check). Unknown or inconsistent values are findings; nothing is substituted by zero.
    output_tokens_details.reasoning_tokens is informational (reasoning is included in
    output_tokens and is never charged again); an impossible value is recorded only."""
    if not isinstance(payload, dict):
        return ["response_not_object"]
    usage = payload.get("usage")
    if not isinstance(usage, dict):
        return ["usage_missing_unknown"]
    findings = []
    for k in MANDATORY_USAGE:
        if not _nonneg_int(usage.get(k)):
            findings.append(f"{k}_unknown")
    it, ot, tt = (
        usage.get("input_tokens"),
        usage.get("output_tokens"),
        usage.get("total_tokens"),
    )
    if _nonneg_int(it) and _nonneg_int(ot) and _nonneg_int(tt) and tt != it + ot:
        findings.append(f"total_tokens_inconsistent:total={tt},input={it},output={ot}")
    details = usage.get("input_tokens_details")
    if not isinstance(details, dict):
        findings.append("input_tokens_details_unknown")
    else:
        for k in MANDATORY_DETAILS:
            v = details.get(k)
            if not _nonneg_int(v):
                findings.append(f"{k}_unknown")
            elif v != 0:
                findings.append(f"cache_activity:{k}={v}")
        c, w = details.get("cached_tokens"), details.get("cache_write_tokens")
        if _nonneg_int(it) and _nonneg_int(c) and _nonneg_int(w) and c + w > it:
            findings.append(
                f"cache_categories_exceed_input:cached={c},written={w},input={it}"
            )
    od = usage.get("output_tokens_details")
    if isinstance(od, dict):
        rt = od.get("reasoning_tokens")
        if rt is not None and (not _nonneg_int(rt) or (_nonneg_int(ot) and rt > ot)):
            findings.append("reasoning_tokens_informational_inconsistent")
    if (
        _nonneg_int(it)
        and _strict_int(counted_input_tokens)
        and it != counted_input_tokens
    ):
        findings.append(
            f"count_usage_mismatch:counted={counted_input_tokens},usage={it}"
        )
    return findings


def settle_response(payload, counted_input_tokens, reservation, rates, *, policy: str):
    """Accounting + contract consequence for ANY 2xx object, BEFORE retry classification or
    parsing. Validates policy, reservation and rates on every call. Returns dict with:
      charge (Fraction|None)  category-based applicable-rate charge when computable, unclipped
      findings                every usage finding (raw inconsistent reports are preserved)
      reconciled (bool)       True only if no accounting or IVF finding exists; a computable
                              charge with an unknown/inconsistent total is NOT reconciled
      halt (None|'ivf_halt'|'accounting_halt'|'e9_fail')
      reservation_retained    True when the charge is unknown OR the report is unreconciled
      overrun (bool)
      usage                   the received usage, preserved verbatim (deep copy)"""
    if policy not in POLICIES:
        raise ContractViolation("policy must be 'e9' or 'study'")
    _validate_reservation(reservation)
    r = validate_rates(rates)
    if not _strict_int(counted_input_tokens) or counted_input_tokens < 0:
        raise ContractViolation("counted input tokens must be a non-negative int")
    findings = usage_checks(payload, counted_input_tokens)
    usage = payload.get("usage") if isinstance(payload, dict) else None
    charge = charge_from_usage(usage, r)
    overrun = charge is not None and charge > reservation
    ivf = any(f.startswith(IVF_FINDING_PREFIXES) for f in findings)
    accounting = (
        any(f.startswith(ACCOUNTING_FINDING_PREFIXES) for f in findings)
        or "response_not_object" in findings
    )
    unknown = charge is None
    reconciled = not (ivf or accounting or unknown)
    halt = None
    if ivf:
        halt = "e9_fail" if policy == "e9" else "ivf_halt"
    elif unknown or accounting or overrun:
        halt = "e9_fail" if policy == "e9" else "accounting_halt"
    return {
        "charge": charge,
        "findings": findings,
        "reconciled": reconciled,
        "halt": halt,
        "reservation_retained": unknown or not reconciled,
        "overrun": overrun,
        "usage": copy.deepcopy(usage),
    }


def handle_generation_response(
    http_status,
    raw_body,
    transport_error,
    counted_input_tokens,
    reservation,
    rates,
    *,
    policy: str,
    reasoning_effort: str,
):
    """Ordered handling of one generation attempt outcome:
      1. strict parse of any 2xx body (duplicate keys => anomaly);
      2. for every 2xx object: settle usage/charges and validate the echoed profile
         (preserved in the returned record) BEFORE
      3. retry/received classification.
    Returns a record dict; classification is None until settlement has happened."""
    if policy not in POLICIES:
        raise ContractViolation("policy must be 'e9' or 'study'")
    _validate_reservation(reservation)
    validate_rates(rates)
    record = {
        "http_status": http_status,
        "transport_error": transport_error,
        "payload": None,
        "parse_error": None,
        "settlement": None,
        "profile_findings": None,
        "classification": None,
    }
    payload = None
    if _status_bucket(http_status, transport_error) == "ok":
        if not isinstance(raw_body, (bytes, bytearray)):
            record["parse_error"] = "body_not_bytes"
        else:
            payload, err = parse_json_strict(bytes(raw_body))
            record["parse_error"] = err
        record["payload"] = payload
        if isinstance(payload, dict):
            record["settlement"] = settle_response(
                payload, counted_input_tokens, reservation, rates, policy=policy
            )
            record["profile_findings"] = validate_expected_profile(
                payload, reasoning_effort=reasoning_effort
            )
    record["classification"] = classify_generation_outcome(
        http_status, payload, transport_error
    )
    if record["settlement"] is not None and record["settlement"]["halt"] is not None:
        # a settlement halt overrides any retry: nothing further is dispatched
        cat, _ = record["classification"]
        record["classification"] = (cat, False)
    return record


HALT_CLASSES = (
    "credential_halt",
    "compatibility_halt",
    "accounting_halt",
    "ivf_halt",
    "e9_fail",
)


def attempt_consequence(category: str, settlement_halt=None, *, policy: str) -> dict:
    """Predetermined consequence of one classified attempt (pre-exposure method selection,
    amendment §7.3/§7.4). Returns:
      halt: None | one of HALT_CLASSES  (a halt stops ALL future LLM dispatch for the run)
      retry_allowed: bool               (subject to retry_decision and the attempt cap)
      evaluate_received_text: bool      (parse/evaluate the current text's valid vectors)
      forfeit_batch_scope: 'none' | 'batch' | 'run'
      raw_retained: True                (always)
    Rules: ordinary failures (count exhaustion / terminal HTTP) forfeit only the batch;
    malformed count/body/wire evidence => compatibility_halt (not automatically IVF);
    accounting_halt on a received text => evaluate it, suppress corrections/new calls,
    forfeit remaining slots; IVF/identity/credential/compatibility halts => the current
    proposal is NOT evaluated, raw text retained for audit."""
    if policy not in POLICIES:
        raise ContractViolation("policy must be 'e9' or 'study'")
    if settlement_halt is not None and settlement_halt not in HALT_CLASSES:
        raise ContractViolation("unknown settlement halt class")
    base = {
        "halt": None,
        "retry_allowed": False,
        "evaluate_received_text": False,
        "forfeit_batch_scope": "none",
        "raw_retained": True,
    }
    received = category in ("received_completed", "received_incomplete")
    if category in ("count_retryable", "gen_retryable", "gen_failed_retryable"):
        base["retry_allowed"] = settlement_halt is None
    elif category in (
        "count_terminal",
        "gen_terminal",
        "gen_failed_terminal",
        "admission_rejected",
    ):
        base["forfeit_batch_scope"] = "batch"
    elif category in ("count_halt_credential", "gen_halt_credential"):
        base["halt"], base["forfeit_batch_scope"] = "credential_halt", "run"
    elif category in (
        "count_contract_anomaly",
        "gen_contract_anomaly",
        "contract_violation",
    ):
        base["halt"], base["forfeit_batch_scope"] = "compatibility_halt", "run"
    elif received:
        base["evaluate_received_text"] = True
    elif category == "count_ok":
        pass
    else:
        raise ContractViolation(f"unknown attempt category {category!r}")
    if settlement_halt is not None:
        if policy == "e9":
            (
                base["halt"],
                base["evaluate_received_text"],
                base["forfeit_batch_scope"],
            ) = "e9_fail", False, "run"
        elif settlement_halt == "accounting_halt":
            base["halt"], base["forfeit_batch_scope"] = "accounting_halt", "run"
            base["evaluate_received_text"] = (
                received  # received text is still evaluated; no new calls
            )
        else:  # ivf_halt (identity/profile/mismatch/cache): discard the current proposal
            (
                base["halt"],
                base["evaluate_received_text"],
                base["forfeit_batch_scope"],
            ) = settlement_halt, False, "run"
        base["retry_allowed"] = False
    return base


def may_dispatch_generation(
    *,
    count_category: str,
    admission: str,
    pair_bound: bool,
    profile_valid: bool,
    halted: bool,
) -> bool:
    """No generation unless count evidence exists, admission passed, the pair is bound,
    the profile validated and no halt is journaled."""
    return (
        count_category == "count_ok"
        and admission == "admitted"
        and pair_bound
        and profile_valid
        and not halted
    )
