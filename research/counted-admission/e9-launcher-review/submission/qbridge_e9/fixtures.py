"""Load and bind the four committed E9 fixtures.

Every check is recorded so the report can show a traceable mapping from an A1
requirement to the code that enforced it. Nothing here selects, edits or
re-renders a fixture: the committed bytes are authoritative and the provider's
own ``prepare`` must reproduce them exactly.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from pathlib import Path

from counted_responses_provider import contract as C

MANIFEST_NAME = "manifest.json"

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
    """A committed fixture, hash or profile field does not verify."""


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
    provider=None,
    repo_root=None,
) -> FixtureSet:
    """Verify the manifest, the eight payload hashes, the request profile and,
    when ``provider`` is supplied, that the provider's own ``prepare`` step
    reproduces the committed bytes for both request classes.

    ``repo_root`` additionally verifies the builder and source hashes recorded
    in the manifest against the files actually present at that root.
    """
    fixtures_dir = Path(fixtures_dir)
    manifest_path = fixtures_dir / MANIFEST_NAME
    manifest_raw = manifest_path.read_bytes()
    manifest = _strict_json(manifest_raw, MANIFEST_NAME)
    manifest_sha = sha256_hex(manifest_raw)
    checks = []

    def record(requirement, detail, passed):
        checks.append(Check(requirement, detail, bool(passed)))
        if not passed:
            raise FixtureError(f"{requirement}: {detail}")

    if not isinstance(manifest, dict):
        raise FixtureError("manifest must be a JSON object")

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

    order = manifest.get("fixture_order")
    entries = manifest.get("fixtures")
    if not isinstance(order, list) or not isinstance(entries, list) or len(order) != len(entries):
        raise FixtureError("manifest fixture_order and fixtures must be parallel lists")
    record(
        "A1.11 exactly four fixed fixtures",
        f"fixture_order={order}",
        len(order) == 4
        and order == ["F1_short", "F2_maximal_renderer", "F3_repeat_of_F2",
                      "F4_correction_no_valid_vectors"],
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
            path = fixtures_dir / spec["path"]
            data = path.read_bytes()
            record(
                "eight committed payload hashes bound",
                f"{spec['path']} sha256={sha256_hex(data)}",
                sha256_hex(data) == spec["sha256"],
            )
            record(
                "eight committed payload byte lengths bound",
                f"{spec['path']} bytes={len(data)}",
                len(data) == spec["bytes"],
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

        # The count body must be the exact projection of the generation body.
        try:
            C.verify_pair(gen_body, count_body, reasoning_effort=reasoning_effort)
            paired = True
            reason = "count body is the exact five-key projection"
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

    if repo_root is not None:
        repo_root = Path(repo_root)
        builder = repo_root / "research" / "counted-admission" / "build_e9_inputs.py"
        record(
            "builder hash bound",
            f"build_e9_inputs.py sha256={sha256_hex(builder.read_bytes())}",
            sha256_hex(builder.read_bytes()) == manifest["builder_sha256"],
        )
        for relative, expected in sorted(manifest.get("source_sha256", {}).items()):
            path = repo_root / relative
            actual = sha256_hex(path.read_bytes()) if path.exists() else None
            record(
                "manifest source hashes bound",
                f"{relative} sha256={actual}",
                actual == expected,
            )

    return FixtureSet(tuple(loaded), manifest, manifest_sha, tuple(checks))
