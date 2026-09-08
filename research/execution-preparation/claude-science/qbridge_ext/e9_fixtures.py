"""Four synthetic E9 fixtures (fabricated numbers; no objective, no optimizer).

F1 short      : batch 1, the 10 initial-slot rows, fabricated values
F2 maximal    : batch 19, 190 rows, every coordinate the 24-byte negative
                minimum-normal float, objective the minimum-normal float
                (the renderer's maximal legal request; NOT the 200-row grammar
                boundary, which the renderer cannot produce)
F3 repeat     : byte-identical to F2 (cache-off observation on a repeated prompt)
F4 correction : F2 user text + the runner's exact correction suffix with the
                one normative 16-byte reason "no_valid_vectors" (+96 B). Note:
                "invalid_envelope" is also 16 bytes; the two are equally maximal,
                neither is uniquely longest (Codex's package uses the other).

The values are not evaluations of anything. They exercise the request path only.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from qbridge.proposals import render_user, system_prompt

NEG_MIN_NORMAL = -2.2250738585072014e-308  # repr length 24
MIN_NORMAL = 2.2250738585072014e-308  # repr length 23, inside [0, 1]
CORRECTION_PREFIX = "\nPREVIOUS RESPONSE REJECTED: "
CORRECTION_SUFFIX = ". Respond again following the output rules exactly."


def _row(index, value, coord):
    return {"index": index, "theta": [coord] * 20, "value": value}


def short_history():
    # ten distinct fabricated objective values in (0,1), distinct coordinates in the disk
    return [
        _row(i, 0.05 * i + 0.011, 0.1 * ((i % 5) + 1) * (1 if i % 2 else -1)) for i in range(1, 11)
    ]


def maximal_history():
    return [_row(i, MIN_NORMAL, NEG_MIN_NORMAL) for i in range(1, 191)]


def correction_text(user: str, reason: str) -> str:
    assert reason in ("invalid_json", "invalid_envelope", "no_valid_vectors")
    return user + CORRECTION_PREFIX + reason + CORRECTION_SUFFIX


def build_fixtures() -> dict:
    system = system_prompt()
    f1 = render_user(short_history(), 1)
    f2 = render_user(maximal_history(), 19)
    f4 = correction_text(f2, "no_valid_vectors")
    fixtures = {
        "F1_short": {"system": system, "user": f1, "max_tokens": 8192},
        "F2_maximal_renderer": {"system": system, "user": f2, "max_tokens": 8192},
        "F3_repeat_of_F2": {"system": system, "user": f2, "max_tokens": 8192},
        "F4_correction_no_valid_vectors": {"system": system, "user": f4, "max_tokens": 8192},
    }
    return fixtures


def describe(fixtures: dict) -> dict:
    out = {}
    for name, req in fixtures.items():
        s, u = req["system"].encode("ascii"), req["user"].encode("ascii")
        out[name] = {
            "system_bytes": len(s),
            "user_bytes": len(u),
            "combined_text_bytes": len(s) + len(u),
            "system_sha256": hashlib.sha256(s).hexdigest(),
            "user_sha256": hashlib.sha256(u).hexdigest(),
            "history_rows": {
                "F1_short": 10,
                "F2_maximal_renderer": 190,
                "F3_repeat_of_F2": 190,
                "F4_correction_no_valid_vectors": 190,
            }[name],
            "batch": {"F1_short": 1}.get(name, 19),
        }
    return out


def write_fixtures(directory) -> dict:
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    fixtures = build_fixtures()
    for name, req in fixtures.items():
        (directory / f"{name}.user.txt").write_bytes(req["user"].encode("ascii"))
    (directory / "system_v0.3.txt").write_bytes(fixtures["F1_short"]["system"].encode("ascii"))
    summary = describe(fixtures)
    (directory / "fixtures_summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True))
    return summary
