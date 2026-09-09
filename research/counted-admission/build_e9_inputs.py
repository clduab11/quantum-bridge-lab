"""Build prospective E9 payloads from preserved, pure reference functions.

All histories are fabricated. No provider, token counter, objective or optimizer
is invoked. These files are inputs for review, not adoption or execution authority.
Run with PYTHONPATH=src and a new output directory as the only argument.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import runpy
import sys

ROOT = Path(__file__).resolve().parents[2]
SOURCES = (
    "research/execution-preparation/claude-science/qbridge_ext/e9_fixtures.py",
    "research/counted-admission/claude-science/counted_responses_reference.py",
    "src/qbridge/proposals.py",
    "src/qbridge/prompts/system_v0.3.txt",
    "src/qbridge/prompts/user_template_v0.3.txt",
)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def build(directory):
    fixture_code = runpy.run_path(str(ROOT / SOURCES[0]))
    reference = runpy.run_path(str(ROOT / SOURCES[1]))
    fixtures = fixture_code["build_fixtures"]()
    descriptions = fixture_code["describe"](fixtures)
    payloads = {}
    rows = []
    for name, request in fixtures.items():
        generation = reference["build_generation_body"](
            request["system"], request["user"], reasoning_effort="medium"
        )
        pair = reference["bind_pair"](generation, reasoning_effort="medium")
        count = json.loads(pair["count_bytes"])
        reference["verify_pair"](generation, count, reasoning_effort="medium")
        if generation["input"] != count["input"]:
            raise ValueError("count/generation input mismatch")
        if generation["input"] != [
            {"role": "developer", "content": request["system"]},
            {"role": "user", "content": request["user"]},
        ]:
            raise ValueError("literal fixture text changed")
        row = {"fixture": name, **descriptions[name], "files": {}}
        for request_class, key in (("count", "count_bytes"), ("generation", "generation_bytes")):
            filename = f"{name}.{request_class}.json"
            data = pair[key]
            payloads[filename] = data
            row["files"][request_class] = {
                "path": filename,
                "bytes": len(data),
                "sha256": digest(data),
            }
        rows.append(row)
    for request_class in ("count", "generation"):
        if (
            payloads[f"F2_maximal_renderer.{request_class}.json"]
            != payloads[f"F3_repeat_of_F2.{request_class}.json"]
        ):
            raise ValueError("repeat fixture changed")
    record = {
        "status": "prospective_offline_inputs_only",
        "protocol_adopted": False,
        "execution_authorized": False,
        "provider_count_calls": 0,
        "provider_generation_calls": 0,
        "study_objective_candidate_evaluations": 0,
        "model": "gpt-5.6-sol",
        "reasoning_effort": "medium",
        "admission_limit": 272000,
        "max_output_tokens": 8192,
        "max_count_attempts": 12,
        "max_generation_attempts": 12,
        "deadline_seconds": 7400,
        "counted_input_tokens": None,
        "count_fee_verified": False,
        "fixture_order": list(fixtures),
        "fixtures": rows,
        "source_sha256": {source: digest((ROOT / source).read_bytes()) for source in SOURCES},
        "builder_sha256": digest(Path(__file__).read_bytes()),
        "limitations": [
            "Byte length is not a token count or universal context-fit proof.",
            "No model compliance, cache behavior, identity or cost was measured.",
            "F2/F3 repeat timing must be observed during a separately authorized E9.",
            "The correction reason is fixed to no_valid_vectors before observations.",
            "The monotonic deadline may expire before every allowed attempt fits.",
        ],
    }
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=False)
    for name, data in payloads.items():
        (directory / name).write_bytes(data)
    (directory / "manifest.json").write_text(json.dumps(record, indent=2, sort_keys=True) + "\n")
    print(
        json.dumps(
            {"fixtures": len(rows), "payload_files": len(payloads), "output": str(directory)}
        )
    )


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: PYTHONPATH=src python build_e9_inputs.py NEW_OUTPUT_DIRECTORY")
    build(sys.argv[1])
