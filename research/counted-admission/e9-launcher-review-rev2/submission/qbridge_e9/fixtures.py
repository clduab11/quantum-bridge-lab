"""Load and bind the four committed E9 fixtures.

Review finding 4 (fixed here). The previous revision treated the
caller-supplied ``manifest.json`` as its own authority: changing a committed
prompt and updating its declared digest passed all checks, and an empty
``source_sha256`` mapping passed too. The reviewed digests are now **pinned in
this module** and the manifest is checked against them, so the manifest can
only confirm what was reviewed, never redefine it.

Three independent authorities are now enforced on **every** executable path:

1. ``REVIEWED_MANIFEST_SHA256`` - the digest of the reviewed manifest bytes.
2. ``REVIEWED_PAYLOAD_SHA256`` - the eight reviewed payload digests and byte
   lengths, checked directly against the files, not via the manifest.
3. ``REVIEWED_SOURCE_SHA256`` / ``REVIEWED_BUILDER_SHA256`` - the complete
   reviewed source set, which must be present in full and verified against a
   repository root. ``repo_root`` is a REQUIRED argument; there is no path that
   skips source verification.

A self-consistent replacement fixture therefore fails before any dispatch.
Nothing here selects, edits or re-renders a fixture: the committed bytes are
authoritative and the provider's own ``prepare`` must reproduce them exactly.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from pathlib import Path

from counted_responses_provider import contract as C

MANIFEST_NAME = "manifest.json"

# ---------------------------------------------------------------------------
# Pinned reviewed digests. These are the authority; the manifest is not.
# Source: research/counted-admission/e9-inputs at engineering baseline
# a8c3e1e83c28db80642ab0123dd1fbf4d9ff5bc2 (branch research/counted-admission).
# ---------------------------------------------------------------------------
REVIEWED_MANIFEST_SHA256 = "f6c1cafce927cde8617b72dd2b404b698a891b2f907b20520d58ff72def9bf63"
REVIEWED_BUILDER_SHA256 = "f45043d9a63542c5dae85fa887d98881c3e353ea4a486744a0a7c27063fabb9f"
REVIEWED_PAYLOAD_SHA256 = {
    "F1_short.count.json": ("751142f6baa44caa83d26c691a8a5d9549aa689c571a998722859d332cb7b868", 4854),
    "F1_short.generation.json": ("3c256227ecd71d1fa6c0612fcd9592f26092dd45df6f5c984c4f546cb0e62685", 4976),
    "F2_maximal_renderer.count.json": ("d71cd4794d8c56317c9bc329ade5f490e7f9e5a8ca3ebac581e57da60e9611c4", 103571),
    "F2_maximal_renderer.generation.json": ("4b2ca00dab4ac94f48c1b3c939c6a52817f9149d51e8b03b58d94adeff1cdf6d", 103693),
    "F3_repeat_of_F2.count.json": ("d71cd4794d8c56317c9bc329ade5f490e7f9e5a8ca3ebac581e57da60e9611c4", 103571),
    "F3_repeat_of_F2.generation.json": ("4b2ca00dab4ac94f48c1b3c939c6a52817f9149d51e8b03b58d94adeff1cdf6d", 103693),
    "F4_correction_no_valid_vectors.count.json": ("e4b9269d707b6d9ef6904310ca77931b9b3c84880868ae4351e2ad1470f4fecf", 103668),
    "F4_correction_no_valid_vectors.generation.json": ("cfe7b7e37ef9a8aea950d26f7eb2720bc613b01c52bb6c108ad91b530be5e450", 103790),
}
REVIEWED_SOURCE_SHA256 = {
    "research/counted-admission/claude-science/counted_responses_reference.py": "9804ad049dcb9cc2e367e7734bced79b377945a00350b2af0b8c4cab2670d0f4",
    "research/execution-preparation/claude-science/qbridge_ext/e9_fixtures.py": "16c89cc2cb8f86b7443e8648c9ed80457427b02e91e86c83d1533df18d4c06d5",
    "src/qbridge/prompts/system_v0.3.txt": "5165cfc31f62b008e0cb7f88c24ea72b286da75f43cc5d6e4e3f36e7d6397f7e",
    "src/qbridge/prompts/user_template_v0.3.txt": "80aa634b5511134e9a741614f60d341422f38143e05136da3f3f2e159bf44ba1",
    "src/qbridge/proposals.py": "2129c2f167f7cee3289c7fc5129fe7f3b6565203e07bc8e37d89d26732cd2254",
}


REVIEWED_FIXTURE_ORDER = (
    "F1_short",
    "F2_maximal_renderer",
    "F3_repeat_of_F2",
    "F4_correction_no_valid_vectors",
)

# Fields of manifest.json that state the frozen request profile. A mismatch
# against the reviewed contract constants is a load failure, not a warning.
PROFILE_EXPECTATIONS = {
    "model": C.MODEL,
    "max_output_tokens": C.MAX_OUTPUT_TOKENS,
    "reasoning_effort": "medium",
    "admission_limit": 272000,
    "deadline_seconds": 7400,
    "max_count_attempts": 12,
    "max_generation_attempts": 12,
}

# Fields that must still assert an unexecuted, unadopted, unpriced state.
PROSPECTIVE_EXPECTATIONS = {
    "execution_authorized": False,
    "protocol_adopted": False,
    "count_fee_verified": False,
    "counted_input_tokens": None,
    "provider_count_calls": 0,
    "provider_generation_calls": 0,
    "study_objective_candidate_evaluations": 0,
}


class FixtureError(ValueError):
    """A committed fixture, hash, profile field or reviewed source does not verify."""


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


@dataclass(frozen=True)
class Check:
    """One recorded verification step."""

    requirement: str
    detail: str
    passed: bool

    def as_dict(self):
        return {"requirement": self.requirement, "detail": self.detail, "passed": self.passed}


@dataclass(frozen=True)
class E9Fixture:
    name: str
    order: int
    batch: int
    logical: int
    history_rows: int
    count_bytes: bytes
    generation_bytes: bytes
    count_sha256: str
    generation_sha256: str
    system_text: str
    user_text: str
    system_sha256: str
    user_sha256: str

    @property
    def pair(self):
        from qbridge.counted_runner import RequestPair

        return RequestPair(self.count_bytes, self.generation_bytes)

    def runner_request(self):
        """The exact runner request the provider's pure prepare step accepts."""
        return {
            "system": self.system_text,
            "user": self.user_text,
            "max_tokens": C.MAX_OUTPUT_TOKENS,
        }

    def as_dict(self):
        return {
            "fixture": self.name,
            "order": self.order,
            "batch": self.batch,
            "logical": self.logical,
            "history_rows": self.history_rows,
            "count_sha256": self.count_sha256,
            "generation_sha256": self.generation_sha256,
            "count_bytes_len": len(self.count_bytes),
            "generation_bytes_len": len(self.generation_bytes),
            "system_sha256": self.system_sha256,
            "user_sha256": self.user_sha256,
        }


@dataclass(frozen=True)
class FixtureSet:
    fixtures: tuple
    manifest: dict
    manifest_sha256: str
    repo_root: str
    checks: tuple = field(default=())

    def by_name(self, name):
        for fixture in self.fixtures:
            if fixture.name == name:
                return fixture
        raise KeyError(name)

    @property
    def failed(self):
        return tuple(c for c in self.checks if not c.passed)

    def as_dict(self):
        return {
            "manifest_sha256": self.manifest_sha256,
            "reviewed_manifest_sha256": REVIEWED_MANIFEST_SHA256,
            "manifest_matches_reviewed_pin": self.manifest_sha256 == REVIEWED_MANIFEST_SHA256,
            "repo_root": self.repo_root,
            "fixture_order": [f.name for f in self.fixtures],
            "fixtures": [f.as_dict() for f in self.fixtures],
            "checks": [c.as_dict() for c in self.checks],
            "checks_passed": sum(c.passed for c in self.checks),
            "checks_failed": len(self.failed),
        }


def _strict_json(data: bytes, label: str):
    body, error = C.parse_json_strict(data)
    if error is not None:
        raise FixtureError(f"{label} is not strict JSON: {error}")
    return body


def _text_of(body, index, role, label):
    inp = body.get("input")
    if not isinstance(inp, list) or len(inp) != 2:
        raise FixtureError(f"{label} input must be exactly two items")
    item = inp[index]
    if not isinstance(item, dict) or item.get("role") != role:
        raise FixtureError(f"{label} input[{index}] must have role {role!r}")
    text = item.get("content")
    if not isinstance(text, str) or not text:
        raise FixtureError(f"{label} {role} content must be a nonempty str")
    return text


def load_fixture_set(
    fixtures_dir,
    *,
    reasoning_effort: str,
    repo_root,
    provider=None,
) -> FixtureSet:
    """Verify the pinned reviewed digests, the manifest, the eight payloads, the
    request profile and the complete reviewed source set.

    ``repo_root`` is REQUIRED: source verification is not optional and there is
    no executable path that skips it. When ``provider`` is supplied, the
    provider's own pure ``prepare`` step must additionally reproduce the
    committed bytes for both request classes.
    """
    fixtures_dir = Path(fixtures_dir)
    if repo_root is None:
        raise FixtureError("repo_root is required: the reviewed source set must be verified")
    repo_root = Path(repo_root)
    checks = []

    def record(requirement, detail, passed):
        checks.append(Check(requirement, detail, bool(passed)))
        if not passed:
            raise FixtureError(f"{requirement}: {detail}")

    # --- 1. the manifest must be the reviewed bytes ----------------------
    manifest_raw = (fixtures_dir / MANIFEST_NAME).read_bytes()
    manifest_sha = sha256_hex(manifest_raw)
    record(
        "pinned reviewed manifest digest",
        f"{MANIFEST_NAME} sha256={manifest_sha} equals the pinned "
        f"{REVIEWED_MANIFEST_SHA256}",
        manifest_sha == REVIEWED_MANIFEST_SHA256,
    )
    manifest = _strict_json(manifest_raw, MANIFEST_NAME)
    if not isinstance(manifest, dict):
        raise FixtureError("manifest must be a JSON object")

    # --- 2. the eight payloads, checked against the PINS not the manifest -
    for relative, (expected_sha, expected_bytes) in sorted(REVIEWED_PAYLOAD_SHA256.items()):
        path = fixtures_dir / relative
        if not path.is_file():
            record("pinned reviewed payload digests", f"{relative} is absent", False)
        data = path.read_bytes()
        record(
            "pinned reviewed payload digests",
            f"{relative} sha256={sha256_hex(data)} bytes={len(data)}",
            sha256_hex(data) == expected_sha and len(data) == expected_bytes,
        )
    extra = sorted(
        p.name
        for p in fixtures_dir.glob("*.json")
        if p.name != MANIFEST_NAME and p.name not in REVIEWED_PAYLOAD_SHA256
    )
    record(
        "no unreviewed payload files present",
        f"unexpected payload files: {extra}" if extra else "only the eight reviewed payloads",
        not extra,
    )

    # --- 3. the complete reviewed source set ------------------------------
    declared = manifest.get("source_sha256")
    record(
        "complete reviewed source set declared",
        f"manifest source_sha256 keys={sorted(declared) if isinstance(declared, dict) else declared!r}",
        isinstance(declared, dict) and set(declared) == set(REVIEWED_SOURCE_SHA256),
    )
    for relative, expected in sorted(REVIEWED_SOURCE_SHA256.items()):
        record(
            "reviewed source digests agree with the pin",
            f"manifest declares {relative}={declared.get(relative)}",
            declared.get(relative) == expected,
        )
        path = repo_root / relative
        actual = sha256_hex(path.read_bytes()) if path.is_file() else None
        record(
            "reviewed source files verified at repo_root",
            f"{relative} sha256={actual}",
            actual == expected,
        )
    builder = repo_root / "research" / "counted-admission" / "build_e9_inputs.py"
    builder_sha = sha256_hex(builder.read_bytes()) if builder.is_file() else None
    record(
        "reviewed builder verified at repo_root",
        f"build_e9_inputs.py sha256={builder_sha}",
        builder_sha == REVIEWED_BUILDER_SHA256
        and manifest.get("builder_sha256") == REVIEWED_BUILDER_SHA256,
    )

    # --- 4. frozen profile and prospective state --------------------------
    for key, expected in PROFILE_EXPECTATIONS.items():
        actual = manifest.get(key)
        record(
            "A1.11 frozen request profile",
            f"manifest {key}={actual!r} equals the reviewed {expected!r}",
            actual == expected and type(actual) is type(expected),
        )
    if reasoning_effort != manifest["reasoning_effort"]:
        raise FixtureError("reasoning effort must equal the manifest's fixed value")
    for key, expected in PROSPECTIVE_EXPECTATIONS.items():
        actual = manifest.get(key)
        record(
            "prospective state preserved",
            f"manifest {key}={actual!r} still {expected!r}",
            actual == expected,
        )

    # --- 5. order and per-fixture structure -------------------------------
    order = manifest.get("fixture_order")
    entries = manifest.get("fixtures")
    if not isinstance(order, list) or not isinstance(entries, list) or len(order) != len(entries):
        raise FixtureError("manifest fixture_order and fixtures must be parallel lists")
    record(
        "A1.11 exactly four fixed fixtures in the reviewed order",
        f"fixture_order={order}",
        tuple(order) == REVIEWED_FIXTURE_ORDER,
    )
    by_name = {e.get("fixture"): e for e in entries}
    record(
        "declared order is the execution order",
        "each ordered name has exactly one manifest entry",
        len(by_name) == len(entries) and all(name in by_name for name in order),
    )

    loaded = []
    for position, name in enumerate(order, start=1):
        entry = by_name[name]
        files = entry.get("files") or {}
        bodies = {}
        for request_class in ("count", "generation"):
            spec = files.get(request_class) or {}
            relative = spec.get("path")
            record(
                "manifest payload paths are the reviewed ones",
                f"{name} {request_class} path={relative!r}",
                relative in REVIEWED_PAYLOAD_SHA256,
            )
            data = (fixtures_dir / relative).read_bytes()
            record(
                "manifest payload digests agree with the pin",
                f"{relative} manifest sha256={spec.get('sha256')}",
                spec.get("sha256") == REVIEWED_PAYLOAD_SHA256[relative][0]
                and spec.get("bytes") == REVIEWED_PAYLOAD_SHA256[relative][1],
            )
            bodies[request_class] = data

        gen_body = _strict_json(bodies["generation"], f"{name} generation body")
        count_body = _strict_json(bodies["count"], f"{name} count body")
        record(
            "committed bytes are canonical",
            f"{name} generation body is canonical JSON",
            C.canonical_bytes(gen_body) == bodies["generation"],
        )
        record(
            "committed bytes are canonical",
            f"{name} count body is canonical JSON",
            C.canonical_bytes(count_body) == bodies["count"],
        )

        system_text = _text_of(gen_body, 0, "developer", f"{name} generation")
        user_text = _text_of(gen_body, 1, "user", f"{name} generation")
        count_system = _text_of(count_body, 0, "developer", f"{name} count")
        count_user = _text_of(count_body, 1, "user", f"{name} count")
        record(
            "developer/user text identical between count and generation",
            f"{name} developer text identical",
            count_system == system_text,
        )
        record(
            "developer/user text identical between count and generation",
            f"{name} user text identical",
            count_user == user_text,
        )

        system_sha = sha256_hex(system_text.encode("ascii"))
        user_sha = sha256_hex(user_text.encode("ascii"))
        record(
            "manifest text hashes bound",
            f"{name} system_sha256={system_sha}",
            system_sha == entry["system_sha256"] and len(system_text) == entry["system_bytes"],
        )
        record(
            "manifest text hashes bound",
            f"{name} user_sha256={user_sha}",
            user_sha == entry["user_sha256"] and len(user_text) == entry["user_bytes"],
        )
        record(
            "developer text is the reviewed system prompt",
            f"{name} system_sha256 equals the reviewed prompt file digest",
            system_sha == REVIEWED_SOURCE_SHA256["src/qbridge/prompts/system_v0.3.txt"],
        )

        try:
            C.verify_pair(gen_body, count_body, reasoning_effort=reasoning_effort)
            paired, reason = True, "count body is the exact five-key projection"
        except C.ContractViolation as exc:
            paired, reason = False, str(exc)
        record("count-to-send identity (contract.verify_pair)", f"{name}: {reason}", paired)

        loaded.append(
            E9Fixture(
                name=name,
                order=position,
                batch=entry["batch"],
                logical=position,
                history_rows=entry["history_rows"],
                count_bytes=bodies["count"],
                generation_bytes=bodies["generation"],
                count_sha256=sha256_hex(bodies["count"]),
                generation_sha256=sha256_hex(bodies["generation"]),
                system_text=system_text,
                user_text=user_text,
                system_sha256=system_sha,
                user_sha256=user_sha,
            )
        )

    f2 = next(f for f in loaded if f.name == "F2_maximal_renderer")
    f3 = next(f for f in loaded if f.name == "F3_repeat_of_F2")
    record(
        "A1.11 F3 is a byte-identical repeat of F2",
        "F2/F3 count bodies byte-identical",
        f2.count_bytes == f3.count_bytes,
    )
    record(
        "A1.11 F3 is a byte-identical repeat of F2",
        "F2/F3 generation bodies byte-identical",
        f2.generation_bytes == f3.generation_bytes,
    )

    if provider is not None:
        for fixture in loaded:
            pair = provider.prepare(fixture.runner_request())
            record(
                "provider.prepare reproduces the committed bytes",
                f"{fixture.name} count bytes reproduced",
                pair.count_body == fixture.count_bytes,
            )
            record(
                "provider.prepare reproduces the committed bytes",
                f"{fixture.name} generation bytes reproduced",
                pair.generation_body == fixture.generation_bytes,
            )

    return FixtureSet(
        tuple(loaded), manifest, manifest_sha, str(repo_root.resolve()), tuple(checks)
    )
