"""Pre-dispatch gate for a live E9 run.

Every requirement is evaluated independently and reported. An unresolved
requirement is a FAILURE, never a default: missing files, absent fields, unknown
versions and unverified fees all fail. A proposal, a candidate document or a
synthetic authority cannot satisfy this gate.

The gate never reads, stores, echoes or logs credential material. It records
only whether the named environment variable is present and non-empty, and the
caller must pass the environment explicitly - offline paths pass an empty one.

Review findings fixed here:

* **3** - Git containment was tested by looking for a parent literally named
  ``.git``, which misses every real repository. :func:`git_worktree_root` now
  walks both the literal and the resolved path for a ``.git`` directory **or
  file** (linked worktrees and submodules use a file), and additionally
  consults ``git rev-parse --show-toplevel`` when the binary is available.
  The records directory is also rejected if it sits under the verified
  repository root.
* **6** - ``approved_at_utc`` was only tested for truthiness. UTC instants are
  now parsed, ordered against the dispatch instant, and the approval must be
  **bound to the reviewed authority** by carrying its digest.

Hash integrity is not verification of external billing or of user approval: a
matching digest shows a retained file is the one that was recorded, nothing
more about what an account will actually charge or what a person agreed to.
"""

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

from counted_responses_provider import contract as C
from counted_responses_provider.authority import (
    HTTPX_VERSION,
    SDK_VERSION,
    AuthorityRecord,
    parse_utc,
    profile_sha256,
)

from qbridge_e9.fixtures import sha256_hex

API_KEY_ENV = "OPENAI_API_KEY"
GIT_QUERY_TIMEOUT_S = 10

# Words that mark a document as a proposal or candidate rather than an adopted
# record. Their presence in an adoption or authorization field fails the gate.
PROPOSAL_MARKERS = (
    "propose",
    "proposed",
    "proposal",
    "candidate",
    "draft",
    "synthetic",
    "fabricated",
    "placeholder",
    "example",
    "hypothetical",
    "illustrative",
    "template",
    "unapproved",
    "not an authorization",
    "not authorized",
    "mock",
    "dummy",
    "simulated",
    "invented",
    "for testing",
    "test fixture",
    "tbd",
)


class GateFailed(RuntimeError):
    """A live dispatch was requested while at least one requirement failed."""


def git_worktree_root(path):
    """The Git worktree root containing ``path``, or None.

    Covers a normal repository (``.git`` directory), a linked worktree or
    submodule (``.git`` FILE holding a ``gitdir:`` pointer) and symlinked
    paths, then falls back to asking Git itself.
    """
    candidates = []
    literal = Path(path)
    for base in (literal, literal.resolve()):
        candidates.extend([base, *base.parents])
    seen = set()
    for base in candidates:
        if base in seen:
            continue
        seen.add(base)
        marker = base / ".git"
        if marker.is_dir() or marker.is_file():
            return base
    if literal.is_dir():
        try:
            found = subprocess.run(
                ["git", "-C", str(literal), "rev-parse", "--show-toplevel"],
                capture_output=True,
                text=True,
                timeout=GIT_QUERY_TIMEOUT_S,
            )
        except (OSError, subprocess.SubprocessError):
            return None
        if found.returncode == 0 and found.stdout.strip():
            return Path(found.stdout.strip())
    return None


@dataclass(frozen=True)
class Requirement:
    key: str
    requirement: str
    status: str  # "pass" | "fail"
    detail: str

    @property
    def passed(self):
        return self.status == "pass"

    def as_dict(self):
        return {
            "key": self.key,
            "requirement": self.requirement,
            "status": self.status,
            "detail": self.detail,
        }


@dataclass(frozen=True)
class GateResult:
    mode: str
    requirements: tuple

    @property
    def failures(self):
        return tuple(r for r in self.requirements if not r.passed)

    @property
    def may_dispatch_live(self):
        return self.mode == "live" and not self.failures

    def status_of(self, key):
        for requirement in self.requirements:
            if requirement.key == key:
                return requirement.status
        return None

    def as_dict(self):
        return {
            "mode": self.mode,
            "may_dispatch_live": self.may_dispatch_live,
            "requirements_total": len(self.requirements),
            "requirements_passed": sum(r.passed for r in self.requirements),
            "requirements_failed": len(self.failures),
            "failed_keys": [r.key for r in self.failures],
            "requirements": [r.as_dict() for r in self.requirements],
        }


def _marker_hits(text):
    lowered = str(text).lower()
    return sorted({m for m in PROPOSAL_MARKERS if m in lowered})


def _utc_or_none(value):
    """Parse a UTC instant, or return None. Never raises."""
    if not isinstance(value, str) or not value:
        return None
    try:
        return parse_utc(value)
    except (ValueError, TypeError):
        return None


def _load_json(path, label):
    if path is None:
        return None, f"{label} path not supplied"
    path = Path(path)
    if not path.is_file():
        return None, f"{label} file is absent: {path}"
    body, error = C.parse_json_strict(path.read_bytes())
    if error is not None:
        return None, f"{label} is not strict JSON: {error}"
    if not isinstance(body, dict):
        return None, f"{label} must be a JSON object"
    return body, None


def _installed_versions():
    try:
        import httpx
        import openai

        return openai.__version__, httpx.__version__
    except Exception as exc:  # pragma: no cover - import failure is itself a failure
        return None, f"import failed: {type(exc).__name__}"


def evaluate_gate(
    *,
    mode: str,
    authority: AuthorityRecord | None,
    limits,
    now_utc: float,
    env,
    adoption_evidence=None,
    billing_evidence=None,
    authorization_record=None,
    specification_path=None,
    records_dir=None,
    repo_root=None,
) -> GateResult:
    """Evaluate every live-dispatch requirement and return the full record.

    ``env`` is REQUIRED and explicit: offline callers pass ``{}`` so no
    credential variable is read at all (review finding 8).
    """
    if mode not in ("dry-run", "live"):
        raise ValueError("mode must be 'dry-run' or 'live'")
    if env is None or not hasattr(env, "get"):
        raise ValueError("env must be an explicit mapping; offline callers pass {}")
    out = []

    def add(key, requirement, ok, detail):
        out.append(Requirement(key, requirement, "pass" if ok else "fail", detail))

    # --- authority record ------------------------------------------------
    if not isinstance(authority, AuthorityRecord):
        add(
            "authority.present",
            "A validated AuthorityRecord is supplied",
            False,
            "no AuthorityRecord was supplied",
        )
        for key, requirement in (
            ("authority.not_synthetic", "authority.synthetic is False"),
            ("authority.scope", "authority scope is the E9 halt policy"),
            ("authority.caps", "attempt caps equal the E9 allowance"),
            ("authority.profile", "frozen request profile matches the reviewed contract"),
            ("authority.price_validity", "recorded prices are valid at dispatch time"),
            ("authority.count_fee", "count fee is verified and covers failed/rejected calls"),
            ("authority.numeric_ceiling", "an explicit positive USD ceiling is recorded"),
            (
                "authority.conservative_ceiling",
                "the ceiling covers the conservative worst case for every allowed attempt",
            ),
        ):
            add(key, requirement, False, "not evaluated: no AuthorityRecord")
    else:
        add(
            "authority.present",
            "A validated AuthorityRecord is supplied",
            True,
            f"authority sha256={authority.sha256()}",
        )
        add(
            "authority.not_synthetic",
            "authority.synthetic is False",
            authority.synthetic is False,
            f"synthetic={authority.synthetic!r}"
            + (
                " (a synthetic authority is refused at the transport boundary by"
                " provider._preflight and cannot dispatch live)"
                if authority.synthetic
                else ""
            ),
        )
        add(
            "authority.scope",
            "authority scope is the E9 halt policy",
            authority.scope == "e9",
            f"scope={authority.scope!r}",
        )
        caps_ok = (
            authority.count_attempt_cap == limits.max_count_attempts
            and authority.generation_attempt_cap == limits.max_generation_attempts
            and authority.count_attempt_cap <= 12
            and authority.generation_attempt_cap <= 12
        )
        add(
            "authority.caps",
            "attempt caps equal the E9 allowance",
            caps_ok,
            f"count_attempt_cap={authority.count_attempt_cap}, "
            f"generation_attempt_cap={authority.generation_attempt_cap}, "
            f"limits={limits.max_count_attempts}/{limits.max_generation_attempts}",
        )
        profile_ok = (
            authority.model == C.MODEL
            and authority.reasoning_effort == limits.reasoning_effort
            and authority.profile_sha256 == profile_sha256(limits.reasoning_effort)
            and authority.max_output_tokens == C.MAX_OUTPUT_TOKENS
            and authority.input_token_ceiling == limits.admission_limit
        )
        add(
            "authority.profile",
            "frozen request profile matches the reviewed contract",
            profile_ok,
            f"model={authority.model!r}, effort={authority.reasoning_effort!r}, "
            f"input_token_ceiling={authority.input_token_ceiling}, "
            f"max_output_tokens={authority.max_output_tokens}, "
            f"profile_sha256={authority.profile_sha256}",
        )
        add(
            "authority.price_validity",
            "recorded prices are valid at dispatch time",
            authority.price_valid_at(now_utc),
            f"recorded_at={authority.recorded_at_utc}, "
            f"price_valid_through={authority.price_valid_through_utc}, "
            f"count_fee_valid_through={authority.count_fee_valid_through_utc}",
        )
        add(
            "authority.count_fee",
            "count fee is verified and covers failed/rejected calls",
            authority.count_fee_verified is True
            and authority.count_fee_covers_failed_and_rejected is True
            and not _marker_hits(authority.count_fee_evidence),
            f"count_fee_ceiling_usd={authority.count_fee_ceiling_usd}, "
            f"verified={authority.count_fee_verified}, "
            f"covers_failed_and_rejected={authority.count_fee_covers_failed_and_rejected}, "
            f"evidence markers={_marker_hits(authority.count_fee_evidence)}",
        )
        add(
            "authority.numeric_ceiling",
            "an explicit positive USD ceiling is recorded",
            authority.ceiling() > 0 and not _marker_hits(authority.authorized_by),
            f"usd_ceiling={authority.usd_ceiling}, "
            f"authorized_by markers={_marker_hits(authority.authorized_by)}",
        )
        # Review finding 5: the ceiling must cover the CONSERVATIVE worst case
        # for every attempt the caps allow, not the optimistic reservation.
        from qbridge_e9.money import conservative_e9_ceiling

        needed = conservative_e9_ceiling(authority, limits)
        add(
            "authority.conservative_ceiling",
            "the ceiling covers the conservative worst case for every allowed attempt",
            authority.ceiling() >= needed,
            f"usd_ceiling={authority.usd_ceiling}, conservative requirement="
            f"{C.money_str(needed)} (every applicable billing category at the"
            " admission limit, for every allowed count and generation attempt)",
        )

    # --- adoption evidence -----------------------------------------------
    adoption, error = _load_json(adoption_evidence, "adoption evidence")
    if adoption is None:
        add("adoption.record", "Amendment A1 adoption is recorded", False, error)
        add(
            "adoption.operative_protocol",
            "the operative protocol file matches its hash",
            False,
            "not evaluated: no adoption record",
        )
    else:
        adopted = adoption.get("amendment_adopted")
        markers = _marker_hits(adoption.get("status", "")) + _marker_hits(
            adoption.get("amendment_file", "")
        )
        adopted_at = _utc_or_none(adoption.get("adopted_at_utc"))
        timing_ok = adoption.get("adopted_at_utc") is None or (
            adopted_at is not None and adopted_at <= now_utc
        )
        add(
            "adoption.record",
            "Amendment A1 adoption is recorded",
            adopted is True and not markers and timing_ok,
            f"amendment_adopted={adopted!r}, status={adoption.get('status')!r}, "
            f"adopted_at_utc={adoption.get('adopted_at_utc')!r} "
            f"(parsed={adopted_at is not None}, not in the future={timing_ok}), "
            f"proposal markers={sorted(set(markers))}",
        )
        expected = adoption.get("operative_protocol_sha256")
        actual = None
        if specification_path is not None and Path(specification_path).is_file():
            actual = sha256_hex(Path(specification_path).read_bytes())
        add(
            "adoption.operative_protocol",
            "the operative protocol file matches its hash",
            bool(expected) and actual == expected,
            f"recorded={expected!r}, file={actual!r}, path={specification_path}",
        )

    # --- billing evidence -------------------------------------------------
    billing, error = _load_json(billing_evidence, "billing evidence")
    if billing is None:
        for key, requirement in (
            ("billing.rate_source", "the model rate source is retained and hashed"),
            ("billing.count_fee_source", "count-request charging evidence is retained and hashed"),
            ("billing.account_terms", "account billing terms are recorded"),
        ):
            add(key, requirement, False, error)
    else:

        def _source_ok(section, expected_sha):
            spec = billing.get(section)
            if not isinstance(spec, dict):
                return False, f"{section} section absent"
            path = spec.get("retained_path")
            if not path or not Path(path).is_file():
                return False, f"{section} retained_path absent: {path!r}"
            actual = sha256_hex(Path(path).read_bytes())
            if expected_sha is not None and actual != expected_sha:
                return False, f"{section} sha256={actual} != authority {expected_sha}"
            if spec.get("covers_failed_and_rejected") is False:
                return False, f"{section} does not cover failed/rejected attempts"
            through = _utc_or_none(spec.get("valid_through_utc"))
            if through is None:
                return False, (
                    f"{section} valid_through_utc is not a UTC instant: "
                    f"{spec.get('valid_through_utc')!r}"
                )
            if through < now_utc:
                return False, (
                    f"{section} validity {spec.get('valid_through_utc')!r} does not cover"
                    " dispatch time"
                )
            return True, (
                f"{section} sha256={actual}, valid_through={spec.get('valid_through_utc')}"
                " (a matching digest shows the retained file is the recorded one; it is"
                " not verification of what the account will charge)"
            )

        rate_sha = authority.rate_source_sha256 if isinstance(authority, AuthorityRecord) else None
        fee_sha = (
            authority.count_fee_evidence_sha256
            if isinstance(authority, AuthorityRecord)
            else None
        )
        ok, detail = _source_ok("model_rates", rate_sha)
        add("billing.rate_source", "the model rate source is retained and hashed", ok, detail)
        ok, detail = _source_ok("count_request_charges", fee_sha)
        add(
            "billing.count_fee_source",
            "count-request charging evidence is retained and hashed",
            ok,
            detail,
        )
        terms = billing.get("account_terms")
        required_terms = (
            "billing_mode",
            "usage_tier",
            "monthly_usage_limit_usd",
            "taxes",
            "existing_month_to_date_spend_usd",
            "concurrent_project_traffic",
        )
        missing = [
            k
            for k in required_terms
            if not isinstance(terms, dict) or terms.get(k) in (None, "", "unknown", "UNKNOWN")
        ]
        add(
            "billing.account_terms",
            "account billing terms are recorded",
            not missing,
            f"missing or unknown account terms: {missing}" if missing else f"recorded: {terms}",
        )

    # --- explicit numeric E9 authorization --------------------------------
    authz, error = _load_json(authorization_record, "E9 authorization record")
    if authz is None:
        add(
            "authorization.explicit_e9",
            "an explicit numeric E9-only authority exists",
            False,
            error,
        )
        add(
            "authorization.bound_and_timed",
            "the approval is a valid, non-expired UTC record bound to this authority",
            False,
            "not evaluated: no authorization record",
        )
    else:
        markers = _marker_hits(authz.get("status", "")) + _marker_hits(authz.get("approved_by", ""))
        limit = authz.get("e9_usd_limit")
        matches = (
            isinstance(authority, AuthorityRecord)
            and isinstance(limit, str)
            and re.fullmatch(r"[0-9]{1,20}(\.[0-9]{1,20})?", limit)
            and authority.ceiling() == C._to_fraction(limit, "e9_usd_limit")
        )
        add(
            "authorization.explicit_e9",
            "an explicit numeric E9-only authority exists",
            authz.get("approved") is True
            and authz.get("scope") == "e9"
            and bool(authz.get("approved_by"))
            and not markers
            and bool(matches),
            f"approved={authz.get('approved')!r}, scope={authz.get('scope')!r}, "
            f"e9_usd_limit={limit!r}, matches_authority_ceiling={bool(matches)}, "
            f"proposal markers={sorted(set(markers))}",
        )
        approved_at = _utc_or_none(authz.get("approved_at_utc"))
        expires_at = _utc_or_none(authz.get("expires_at_utc"))
        bound_digest = authz.get("authority_sha256")
        bound = (
            isinstance(authority, AuthorityRecord)
            and isinstance(bound_digest, str)
            and bound_digest == authority.sha256()
        )
        timing_ok = approved_at is not None and approved_at <= now_utc
        expiry_ok = authz.get("expires_at_utc") is None or (
            expires_at is not None and expires_at > now_utc
        )
        add(
            "authorization.bound_and_timed",
            "the approval is a valid, non-expired UTC record bound to this authority",
            timing_ok and expiry_ok and bound,
            f"approved_at_utc={authz.get('approved_at_utc')!r} "
            f"(parsed={approved_at is not None}, not in the future={timing_ok}), "
            f"expires_at_utc={authz.get('expires_at_utc')!r} (valid={expiry_ok}), "
            f"authority_sha256 bound={bound}. A parsed digest and timestamp are not"
            " evidence that a person approved a charge.",
        )

    # --- environment and profile -----------------------------------------
    sdk, httpx_version = _installed_versions()
    add(
        "environment.sdk_versions",
        f"installed openai=={SDK_VERSION} and httpx=={HTTPX_VERSION}",
        sdk == SDK_VERSION and httpx_version == HTTPX_VERSION,
        f"installed openai={sdk!r}, httpx={httpx_version!r}",
    )
    if isinstance(authority, AuthorityRecord):
        add(
            "environment.authority_pins",
            "the authority pins the installed SDK versions",
            authority.sdk_version == sdk and authority.httpx_version == httpx_version,
            f"authority pins openai={authority.sdk_version!r}, httpx={authority.httpx_version!r}",
        )
    else:
        add(
            "environment.authority_pins",
            "the authority pins the installed SDK versions",
            False,
            "not evaluated: no AuthorityRecord",
        )

    # --- credential presence (never the value) ----------------------------
    key_present = bool(str(env.get(API_KEY_ENV, "")).strip())
    add(
        "credential.present",
        f"{API_KEY_ENV} is present in the supplied environment",
        key_present,
        f"{API_KEY_ENV} present={key_present} (value never read, stored or logged;"
        " offline callers pass an empty environment)",
    )

    # --- private records store --------------------------------------------
    if records_dir is None:
        add(
            "records.private",
            "raw records are stored privately outside any Git worktree",
            False,
            "records directory not supplied",
        )
    else:
        path = Path(records_dir)
        try:
            mode_bits = oct(path.stat().st_mode & 0o777) if path.is_dir() else None
        except OSError as exc:
            mode_bits = f"stat failed: {type(exc).__name__}"
        worktree = git_worktree_root(path)
        under_repo = False
        if repo_root is not None:
            try:
                under_repo = path.resolve().is_relative_to(Path(repo_root).resolve())
            except (OSError, ValueError):
                under_repo = True
        add(
            "records.private",
            "raw records are stored privately outside any Git worktree",
            path.is_dir() and mode_bits == "0o700" and worktree is None and not under_repo,
            f"path={path}, resolved={path.resolve() if path.exists() else None}, "
            f"mode={mode_bits}, git_worktree_root={worktree}, "
            f"under_verified_repo_root={under_repo}",
        )

    return GateResult(mode, tuple(out))
