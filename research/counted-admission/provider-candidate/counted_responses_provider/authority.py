"""Dispatch authority record for the single-attempt Responses provider.

Every fact a live dispatch depends on is bound here and validated on
construction. Nothing is defaulted: a missing, unknown, expired or unverified
fact makes construction fail, and construction failure means no dispatch.

The record never verifies the truth of account evidence; it only refuses to
run without it. `synthetic=True` records are accepted ONLY together with an
httpx.MockTransport (checked at every dispatch by the provider), so a
fabricated ceiling, date or fee can never license a live request.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, fields
from datetime import datetime, timezone
from fractions import Fraction
from pathlib import Path

from .contract import (
    COUNT_ENDPOINT,
    GENERATION_ENDPOINT,
    MAX_OUTPUT_TOKENS,
    MODEL,
    RATE_NAMES,
    SUPPORTED_EFFORTS,
    ContractViolation,
    _to_fraction,
    canonical_bytes,
    parse_json_strict,
    rates_per_million,
    sha256,
)

SDK_VERSION = "3.9.0"
HTTPX_VERSION = "0.28.1"
PROSPECTIVE_ADMISSION_LIMIT = 272000
SCOPES = ("e9", "study")
# Prospective per-class attempt maxima from research/counted-admission/BUDGET.md and
# STATUS.md (E9: <=12 count + <=12 generation; study: up to 4,560 of each across both
# stages). A larger cap needs a separately adopted amendment, not a bigger number here.
CLASS_CAP_MAXIMA = {"e9": 12, "study": 4560}
UTC_INSTANT = r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z"


def parse_utc(value) -> float:
    """Strict 'YYYY-MM-DDTHH:MM:SSZ' -> POSIX seconds; anything else is refused."""
    if not isinstance(value, str) or not re.fullmatch(UTC_INSTANT, value):
        raise ValueError("UTC instant must be 'YYYY-MM-DDTHH:MM:SSZ'")
    return datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc).timestamp()


def profile_sha256(reasoning_effort: str) -> str:
    """Hash of the full frozen request profile (everything except the two texts)."""
    if reasoning_effort not in SUPPORTED_EFFORTS:
        raise ContractViolation("reasoning effort must be one documented Sol value")
    profile = {
        "count_endpoint": COUNT_ENDPOINT,
        "generation_endpoint": GENERATION_ENDPOINT,
        "model": MODEL,
        "input_roles": ["developer", "user"],
        "reasoning": {"effort": reasoning_effort},
        "text": {"verbosity": "medium"},
        "truncation": "disabled",
        "max_output_tokens": MAX_OUTPUT_TOKENS,
        "store": False,
        "stream": False,
        "service_tier": "default",
        "prompt_cache_options": {"mode": "explicit"},
        "sdk": {"openai": SDK_VERSION, "httpx": HTTPX_VERSION},
    }
    return sha256(canonical_bytes(profile))


def _nonempty(value, name):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a nonempty string naming the actual fact")


def _strict_int(value, name, low, high):
    if isinstance(value, bool) or not isinstance(value, int) or not low <= value <= high:
        raise ValueError(f"{name} must be an int in [{low}, {high}]")


def _hex64(value, name):
    if not isinstance(value, str) or not re.fullmatch(r"[0-9a-f]{64}", value):
        raise ValueError(f"{name} must be a 64-hex SHA-256")


@dataclass(frozen=True)
class AuthorityRecord:
    """All dispatch-relevant facts; see module docstring.

    Money fields are bounded plain decimal strings (contract F5 grammar).
    `count_fee_ceiling_usd` is the VERIFIED maximum charge of one count
    attempt including failed and rejected counts; it is reserved in full for
    every count attempt and never settled to an observed amount.
    """

    scope: str
    synthetic: bool
    authorized_by: str
    recorded_at_utc: str
    purpose: str
    profile_sha256: str
    model: str
    reasoning_effort: str
    input_token_ceiling: int
    max_output_tokens: int
    count_attempt_cap: int
    generation_attempt_cap: int
    usd_ceiling: str
    input_usd_per_million: str
    cached_input_usd_per_million: str
    cache_write_usd_per_million: str
    output_usd_per_million: str
    billing_categories: tuple
    rate_source: str
    rate_source_sha256: str
    price_valid_through_utc: str
    count_fee_ceiling_usd: str
    count_fee_evidence: str
    count_fee_evidence_sha256: str
    count_fee_valid_through_utc: str
    count_fee_covers_failed_and_rejected: bool
    count_fee_verified: bool
    sdk_version: str
    httpx_version: str

    def __post_init__(self):
        if self.scope not in SCOPES:
            raise ValueError("scope must be 'e9' or 'study' (it names the halt policy)")
        if type(self.synthetic) is not bool:
            raise ValueError("synthetic must be a bool")
        for name in ("authorized_by", "purpose", "rate_source", "count_fee_evidence"):
            _nonempty(getattr(self, name), name)
        recorded = parse_utc(self.recorded_at_utc)
        if parse_utc(self.price_valid_through_utc) < recorded:
            raise ValueError("price_valid_through_utc must not precede recorded_at_utc")
        if parse_utc(self.count_fee_valid_through_utc) < recorded:
            raise ValueError("count_fee_valid_through_utc must not precede recorded_at_utc")
        if self.model != MODEL:
            raise ValueError("model must be exactly gpt-5.6-sol (no routing alias)")
        if self.reasoning_effort not in SUPPORTED_EFFORTS:
            raise ValueError("reasoning_effort must be one documented Sol value")
        _hex64(self.profile_sha256, "profile_sha256")
        if self.profile_sha256 != profile_sha256(self.reasoning_effort):
            raise ValueError("profile_sha256 does not match the frozen request profile")
        _strict_int(self.input_token_ceiling, "input_token_ceiling", 1, PROSPECTIVE_ADMISSION_LIMIT)
        if self.max_output_tokens != MAX_OUTPUT_TOKENS or type(self.max_output_tokens) is not int:
            raise ValueError("max_output_tokens must be the int 8192")
        maximum = CLASS_CAP_MAXIMA[self.scope]
        _strict_int(self.count_attempt_cap, "count_attempt_cap", 1, maximum)
        _strict_int(self.generation_attempt_cap, "generation_attempt_cap", 1, maximum)
        if _to_fraction(self.usd_ceiling, "usd_ceiling") <= 0:
            raise ValueError("usd_ceiling must be strictly positive")
        self.rates()  # strictly positive, bounded, exactly four categories
        if tuple(self.billing_categories) != RATE_NAMES:
            raise ValueError(f"billing_categories must be exactly {RATE_NAMES}")
        _hex64(self.rate_source_sha256, "rate_source_sha256")
        if _to_fraction(self.count_fee_ceiling_usd, "count_fee_ceiling_usd") < 0:
            raise ValueError("count_fee_ceiling_usd must be non-negative")
        _hex64(self.count_fee_evidence_sha256, "count_fee_evidence_sha256")
        if self.count_fee_covers_failed_and_rejected is not True:
            raise ValueError(
                "count fee evidence must explicitly cover failed and rejected attempts"
            )
        if self.count_fee_verified is not True:
            raise ValueError(
                "count_fee_verified must be True; an unverified count fee blocks dispatch"
            )
        if self.sdk_version != SDK_VERSION or self.httpx_version != HTTPX_VERSION:
            raise ValueError(f"record must pin openai {SDK_VERSION} and httpx {HTTPX_VERSION}")

    # -- derived exact values -------------------------------------------------
    def rates(self) -> dict:
        return rates_per_million(
            self.input_usd_per_million,
            self.cached_input_usd_per_million,
            self.cache_write_usd_per_million,
            self.output_usd_per_million,
        )

    def ceiling(self) -> Fraction:
        return _to_fraction(self.usd_ceiling, "usd_ceiling")

    def count_fee_ceiling(self) -> Fraction:
        return _to_fraction(self.count_fee_ceiling_usd, "count_fee_ceiling_usd")

    def price_valid_at(self, when) -> bool:
        """True iff `when` is a finite native time inside BOTH validity intervals:
        recorded_at_utc <= when <= min(price_valid_through_utc, count_fee_valid_through_utc)."""
        if type(when) not in (int, float) or not math.isfinite(when):
            return False
        start = parse_utc(self.recorded_at_utc)
        end = min(
            parse_utc(self.price_valid_through_utc), parse_utc(self.count_fee_valid_through_utc)
        )
        return start <= when <= end

    def as_dict(self) -> dict:
        data = {f.name: getattr(self, f.name) for f in fields(self)}
        data["billing_categories"] = list(self.billing_categories)
        return data

    def sha256(self) -> str:
        return sha256(canonical_bytes(self.as_dict()))

    @classmethod
    def from_dict(cls, data) -> AuthorityRecord:
        names = {f.name for f in fields(cls)}
        if not isinstance(data, dict) or set(data) != names:
            raise ValueError("authority record requires exactly " + ", ".join(sorted(names)))
        data = dict(data)
        if not isinstance(data["billing_categories"], list):
            raise TypeError("billing_categories must be a list")
        data["billing_categories"] = tuple(data["billing_categories"])
        return cls(**data)

    @classmethod
    def load(cls, path) -> AuthorityRecord:
        data, error = parse_json_strict(Path(path).read_bytes())  # duplicate keys refused
        if error is not None:
            raise ValueError(f"authority file is not strict JSON: {error}")
        return cls.from_dict(data)
