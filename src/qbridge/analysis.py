"""Protocol v0.4 locked endpoint summaries, with no objective evaluations.

All six ordered comparisons are nuisance summaries for custody selection. Only
the precommitted AI-minus-CMA pair may be interpreted after output sealing.
Coverage is conditional on the protocol's iid and stationarity assumptions.
"""

import itertools
import math

LABELS = ("A", "B", "C")
PAIRS = tuple(itertools.permutations(LABELS, 2))
MARGIN = -math.log10(2)
COVERAGE_LOWER_BOUND = 1 - 2 * 21700 / 2**20


def _flag(value, name):
    if type(value) is not bool:
        raise ValueError(f"{name} must be boolean")


def _finite(value):
    if type(value) not in (int, float):
        raise ValueError("endpoint/difference must be a finite number or null")
    try:
        number = float(value)
    except (OverflowError, ValueError) as exc:
        raise ValueError("number outside finite float64 domain") from exc
    if not math.isfinite(number):
        raise ValueError("endpoint/difference must be finite")
    return number


def summarize_stage(differences, *, invalid=False):
    """Retain exactly 20 differences and use ranks 6 and 15 without interpolation.

    A missing difference makes the interval and sample median noncomputable;
    partial-sample inference is never substituted. Invalid nominal calculations
    remain available descriptively, with both confirmatory directions disabled.
    """
    _flag(invalid, "invalid")
    values = list(differences)
    if len(values) != 20:
        raise ValueError("a stage requires exactly 20 differences, including nulls")
    values = [None if value is None else _finite(value) for value in values]
    finite = sorted(value for value in values if value is not None)
    complete = len(finite) == 20
    interval = [finite[5], finite[14]] if complete else None
    median = finite[9] / 2 + finite[10] / 2 if complete else None
    category = "noncomputable"
    zero_position = None
    if complete:
        lower, upper = interval
        category = (
            "supports"
            if upper < MARGIN
            else ("excludes" if lower > MARGIN else "inconclusive")
        )
        zero_position = (
            "below" if upper < 0 else ("above" if lower > 0 else "contains_zero")
        )
    return {
        "differences": values,
        "n_planned": 20,
        "n_defined": len(finite),
        "interval": interval,
        "sample_median": median,
        "exact_ties": sum(value == 0 for value in finite),
        "interval_relative_to_zero": zero_position,
        "nominal_category": category,
        "confirmatory_category": "invalid" if invalid or not complete else category,
        "invalid_for_confirmation": invalid or not complete,
    }


def analyze_masked(rows, *, svf=False, ivf=False):
    """Validate the complete 3 x 40 masked table and summarize separate stages.

    Rows have exactly label, block and y keys. y is the already transformed
    log10 floored endpoint in [-12, 0], or None for an explicitly missing
    endpoint. Missing *records* are errors, rather than implicit missing data.
    """
    _flag(svf, "svf")
    _flag(ivf, "ivf")
    table = {}
    for row in rows:
        if not isinstance(row, dict) or set(row) != {"label", "block", "y"}:
            raise ValueError("masked rows require exactly label, block, y")
        label, block, value = row["label"], row["block"], row["y"]
        if type(label) is not str or label not in LABELS:
            raise ValueError("masked label must be A, B or C")
        if type(block) is not int or not 0 <= block < 40:
            raise ValueError("block must be an integer from 0 through 39")
        if (label, block) in table:
            raise ValueError("duplicate label/block record")
        if value is not None:
            value = _finite(value)
            if not -12 <= value <= 0:
                raise ValueError("y must be log10 floored endpoint in [-12, 0]")
        table[label, block] = value
    if len(table) != 120:
        raise ValueError(
            "all 120 label/block records are required; use explicit null endpoints"
        )
    missing = [
        {"label": label, "block": block}
        for block in range(40)
        for label in LABELS
        if table[label, block] is None
    ]
    invalid = svf or ivf or bool(missing)
    stages = {}
    for stage, start in (("1", 0), ("2", 20)):
        blocks = range(start, start + 20)
        summaries = {}
        for left, right in PAIRS:
            differences = [
                None
                if table[left, block] is None or table[right, block] is None
                else table[left, block] - table[right, block]
                for block in blocks
            ]
            summaries[f"{left}-{right}"] = summarize_stage(differences, invalid=invalid)
        stages[stage] = {
            "blocks": list(blocks),
            "pairs": summaries,
            "floor_boundary_counts": {
                label: sum(table[label, block] == -12 for block in blocks)
                for label in LABELS
            },
        }
    decisions = {}
    for left, right in PAIRS:
        key = f"{left}-{right}"
        first, second = (
            stages[s]["pairs"][key]["nominal_category"] for s in ("1", "2")
        )
        if invalid:
            decision = "invalid"
        elif first == second == "supports":
            decision = "replicated_support"
        elif first == second == "excludes":
            decision = "replicated_exclusion"
        else:
            decision = f"stage_1_{first};stage_2_{second}"
        decisions[key] = decision
    return {
        "schema": "qbridge.locked-analysis.v1",
        "margin": MARGIN,
        "stage_coverage_lower_bound": COVERAGE_LOWER_BOUND,
        "coverage_note": "Separate per-stage intervals, not a joint 95% region; assumes iid/stationarity.",
        "pair_note": "Six nuisance summaries; only the precommitted pair is interpreted after sealing.",
        "floor_count_note": "Counts at y=-12 cannot distinguish exact-floor from below-floor raw endpoints.",
        "validity": {
            "svf": svf,
            "ivf": ivf,
            "missing_endpoints": missing,
            "invalid_for_confirmation": invalid,
        },
        "stages": stages,
        "pair_decisions": decisions,
    }
