"""Generate fabricated E9 inputs and offline manifest inputs; never dispatch."""

from decimal import Decimal, ROUND_CEILING
import hashlib
import importlib.metadata
import json
import math
from pathlib import Path
import platform
import sys

from qbridge.budget import calculate_budget
from qbridge.proposals import render_user, system_prompt
from qbridge.seeds import seed_manifest


ROOT = Path.cwd()
OUT = ROOT / "research/execution-preparation"
BASE = "b89297cfbbca1a922110ef22c9c157e3f63f7fa7"
SUFFIX = (
    "\nPREVIOUS RESPONSE REJECTED: invalid_envelope. "
    "Respond again following the output rules exactly."
)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def dump(name, value):
    data = (json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n").encode()
    path = OUT / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return {"path": name, "sha256": digest(data), "bytes": len(data)}


stored = json.loads((ROOT / "research/provider/verification.json").read_text())
for name, expected in stored["source_sha256"].items():
    assert digest((ROOT / name).read_bytes()) == expected, name
assert sys.version_info[:2] == (3, 11)
literal_system = (ROOT / "prompts/system_v0.3.txt").read_text()
assert system_prompt() == literal_system
assert (ROOT / "prompts/user_template_v0.3.txt").read_bytes() == (
    ROOT / "src/qbridge/prompts/user_template_v0.3.txt"
).read_bytes()
assert (
    SUFFIX.lstrip("\n").replace("invalid_envelope", "{reason}")
    in (ROOT / "specification/ai_quantum_control_protocol_v0.4.md").read_text()
)

short = [{"index": i, "theta": [i / 100, 0.0] * 10, "value": i / 100} for i in range(1, 11)]
long = [
    {"index": i, "theta": [-sys.float_info.min] * 20, "value": sys.float_info.min}
    for i in range(1, 191)
]
for rows in (short, long):
    assert [row["index"] for row in rows] == list(range(1, len(rows) + 1))
    for row in rows:
        assert 0 <= row["value"] <= 1
        assert len(row["theta"]) == 20
        assert all(math.isfinite(x) for x in row["theta"])
        assert all(math.hypot(*row["theta"][k : k + 2]) <= 1 for k in range(0, 20, 2))

u1 = render_user(short, 1)
u2 = render_user(long, 19)
users = (u1, u2, u2, u2 + SUFFIX)
records = []
for index, user in enumerate(users, 1):
    payload = {
        "model": "gpt-5.6-sol",
        "messages": [
            {"role": "developer", "content": literal_system},
            {"role": "user", "content": user},
        ],
        "reasoning_effort": "medium",
        "max_completion_tokens": 8192,
        "n": 1,
        "stream": False,
        "store": False,
        "service_tier": "default",
        "prompt_cache_options": {"mode": "explicit", "ttl": "30m"},
    }
    record = dump(f"fixtures/F{index}.json", payload)
    record.update(
        {
            "fixture": f"F{index}",
            "history_rows": 10 if index == 1 else 190,
            "batch": 1 if index == 1 else 19,
            "system_sha256": digest(literal_system.encode()),
            "user_sha256": digest(user.encode()),
            "user_bytes": len(user.encode()),
            "synthetic_correction": index == 4,
        }
    )
    records.append(record)
assert records[1]["sha256"] == records[2]["sha256"]
assert users[3][: -len(SUFFIX)] == users[1]
dump("fabricated-histories.json", {"F1": short, "F2_F3_F4": long})

scenarios = []
for label, limit, p, q in (
    ("hypothetical_50000_tokens", 50_000, "4", "20"),
    ("hypothetical_tokens_equal_byte_bound_not_token_proof", 108_835, "4", "20"),
    ("documented_model_input_maximum_conditional_reserve_only", 922_000, "8", "30"),
):
    result = calculate_budget(
        input_token_ceiling=limit,
        input_usd_per_million=p,
        output_usd_per_million=q,
        extra_usd_reserve="0",
        max_e9_attempts=12,
    )
    exact = Decimal(4572) * (Decimal(limit) * Decimal(p) + Decimal(8192) * Decimal(q)) / 1_000_000
    assert result["combined_totals_usd"]["retry_correction_plus_e9_and_reserve"] == format(
        exact.quantize(Decimal("0.01"), rounding=ROUND_CEILING), "f"
    )
    result["scenario_label"] = label
    result["excluded_unknowns"] = [
        "account-specific charges, region adjustments and tax",
        "rejected-request billing and any unpriced categories",
        "complete input-token and price-validity guarantee",
    ]
    scenarios.append(result)
dump("conditional-budgets.json", scenarios)
seeds = [seed_manifest(block) for block in range(40)]
assert all(1 <= row["cma_seed"] < 2**31 and row["llm_seed_sent"] is False for row in seeds)
assert seeds == [seed_manifest(block) for block in range(40)]
dump("candidate-seeds.json", {"source_commit": BASE, "frozen": False, "blocks": seeds})
dump(
    "candidate-environment.json",
    {
        "python": sys.version,
        "platform": platform.platform(),
        "packages": {
            name: importlib.metadata.version(name)
            for name in ("numpy", "scipy", "cma", "pytest", "ruff")
        },
        "lock_sha256": digest((ROOT / "uv.lock").read_bytes()),
        "source_commit": BASE,
        "selected_for_study": False,
        "frozen": False,
        "note": "Existing Codex candidate runtime; Claude Science must record its actual chosen runtime separately.",
    },
)
dump(
    "manifest.json",
    {
        "kind": "offline_e9_preparation",
        "preparation_script_sha256": digest(Path(__file__).read_bytes()),
        "source_commit": BASE,
        "fixture_policy": "four fixed logical fixtures; transport retries only; no automatic schema correction beyond F4",
        "fixture_records": records,
        "logical_fixture_calls": 4,
        "max_transport_attempts": 12,
        "attempt_timeout_seconds": 300,
        "backoff_seconds": [5, 20],
        "proposed_overall_deadline_seconds": 3700,
        "deadline_note": "Outer deadline includes overhead and can forfeit unfinished fixtures; no completion guarantee.",
        "transport_calls_executed": 0,
        "provider_token_count_calls": 0,
        "study_objective_evaluations": 0,
        "real_mapping_created": False,
        "execution_authorized": False,
        "billing_complete": False,
        "tokenizer_cap_verified": False,
        "frozen": False,
        "source_sha256": stored["source_sha256"],
        "open_requirements": [
            "effective decoding semantics",
            "actual adequate fingerprint",
            "Chat input admission proof",
            "account access and all billing categories",
            "numerical monetary authority and durable cap enforcement",
        ],
        "performed_checks": [
            "27 source hashes match",
            "literal prompt equality",
            "fabricated history indexes and domain valid",
            "existing renderer accepts F1 and F2",
            "F3 exactly repeats F2",
            "F4 exact normative suffix",
            "budget arithmetic independently checked with Decimal",
            "all 40 seed records deterministic",
        ],
    },
)
print(
    json.dumps(
        {
            "output": str(OUT),
            "fixture_hashes": records,
            "conditional_combined_usd": [x["combined_totals_usd"] for x in scenarios],
        },
        indent=2,
    )
)
