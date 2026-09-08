"""Synthetic records only: no optimizer or physical objective is invoked."""

import json
import math
import subprocess
import sys
from pathlib import Path

import pytest

from qbridge.analysis import analyze_masked, summarize_stage


def rows():
    return [
        {"label": label, "block": block, "y": value}
        for block in range(40)
        for label, value in (("A", -3.0), ("B", -2.0), ("C", -1.0))
    ]


def test_exact_ranks_and_descriptive_median():
    values = [float(i - 10) for i in range(20)]
    result = summarize_stage(values[::-1])
    assert result["differences"] == values[::-1]
    assert result["interval"] == [-5.0, 4.0]
    assert result["sample_median"] == -0.5
    assert result["exact_ties"] == 1
    assert result["nominal_category"] == "inconclusive"


@pytest.mark.parametrize(
    "value,category",
    [
        (-1.0, "supports"),
        (0.0, "excludes"),
        (-math.log10(2), "inconclusive"),
        (math.nextafter(-math.log10(2), -math.inf), "supports"),
        (math.nextafter(-math.log10(2), math.inf), "excludes"),
    ],
)
def test_strict_margin_and_ties(value, category):
    result = summarize_stage([value] * 20)
    assert result["interval"] == [value, value]
    assert result["nominal_category"] == category
    assert result["confirmatory_category"] == category


@pytest.mark.parametrize(
    "values",
    [
        [-1.0] * 19,
        [-1.0] * 21,
        [True] * 20,
        [math.nan] * 20,
        [math.inf] * 20,
        ["-1"] * 20,
    ],
)
def test_stage_rejects_bad_shape_and_values(values):
    with pytest.raises(ValueError):
        summarize_stage(values)


def test_missing_d_is_not_dropped_or_imputed():
    result = summarize_stage([-1.0] * 19 + [None])
    assert result["differences"][-1] is None
    assert result["n_defined"] == 19
    assert result["interval"] is None
    assert result["sample_median"] is None
    assert result["nominal_category"] == "noncomputable"
    assert result["confirmatory_category"] == "invalid"


@pytest.mark.parametrize("value", [-1.0, 0.0])
def test_invalidity_disables_both_directions(value):
    result = summarize_stage([value] * 20, invalid=True)
    assert result["nominal_category"] in {"supports", "excludes"}
    assert result["confirmatory_category"] == "invalid"


def test_all_six_pairs_each_stage_without_pooling():
    result = analyze_masked(rows())
    assert set(result["stages"]) == {"1", "2"}
    for stage in result["stages"].values():
        assert set(stage["pairs"]) == {"A-B", "A-C", "B-A", "B-C", "C-A", "C-B"}
        assert stage["pairs"]["A-B"]["differences"] == [-1.0] * 20
        assert stage["pairs"]["B-A"]["nominal_category"] == "excludes"
    assert result["pair_decisions"]["A-B"] == "replicated_support"
    assert result["pair_decisions"]["B-A"] == "replicated_exclusion"
    assert "pooled" not in result


def test_two_stage_discordance_is_reported():
    data = rows()
    for row in data:
        if row["block"] >= 20 and row["label"] == "A":
            row["y"] = -1.0
    result = analyze_masked(data)
    assert result["pair_decisions"]["A-B"] == "stage_1_supports;stage_2_excludes"


@pytest.mark.parametrize("flag", ["svf", "ivf"])
def test_global_invalidity_applies_both_stages_and_directions(flag):
    result = analyze_masked(rows(), **{flag: True})
    assert set(result["pair_decisions"].values()) == {"invalid"}
    for stage in result["stages"].values():
        assert all(p["confirmatory_category"] == "invalid" for p in stage["pairs"].values())


def test_missing_rs_preserves_primary_nominal_comparison_and_blocks_confirmation():
    data = rows()
    data[2]["y"] = None
    result = analyze_masked(data)
    assert result["validity"]["missing_endpoints"] == [{"label": "C", "block": 0}]
    assert result["stages"]["1"]["pairs"]["A-B"]["interval"] == [-1.0, -1.0]
    assert result["stages"]["1"]["pairs"]["A-C"]["interval"] is None
    assert result["pair_decisions"]["A-B"] == "invalid"


@pytest.mark.parametrize(
    "change",
    [
        lambda data: data.pop(),
        lambda data: data.append(data[0].copy()),
        lambda data: data[0].update(identity="AI"),
        lambda data: data[0].update(label="AI"),
        lambda data: data[0].update(block=40),
        lambda data: data[0].update(block=True),
        lambda data: data[0].update(y=-12.1),
        lambda data: data[0].update(y=0.1),
        lambda data: data[0].update(y=math.nan),
        lambda data: data[0].update(y=True),
        lambda data: data[0].update(y="-2"),
    ],
)
def test_masked_contract_rejects_invalid_records(change):
    data = rows()
    change(data)
    with pytest.raises(ValueError):
        analyze_masked(data)


def test_floor_boundary_count_is_truthful_about_masked_information():
    data = rows()
    data[0]["y"] = -12.0
    result = analyze_masked(data)
    assert result["stages"]["1"]["floor_boundary_counts"] == {"A": 1, "B": 0, "C": 0}
    assert "cannot distinguish" in result["floor_count_note"]


@pytest.mark.parametrize(
    "values",
    [
        [-1.0] * 14 + [-math.log10(2)] * 6,
        [-math.log10(2)] * 6 + [0.0] * 14,
    ],
)
def test_equality_at_either_interval_endpoint_is_inconclusive(values):
    assert summarize_stage(values)["nominal_category"] == "inconclusive"


@pytest.mark.parametrize("flag", [1, None, "false"])
def test_invalidity_flags_are_not_coerced(flag):
    with pytest.raises(ValueError):
        summarize_stage([0.0] * 20, invalid=flag)
    with pytest.raises(ValueError):
        analyze_masked(rows(), svf=flag)


def test_locked_cli_synthetic_file_roundtrip(tmp_path):
    source = tmp_path / "masked.json"
    source.write_text(json.dumps({"rows": rows(), "svf": False, "ivf": False}))
    output = tmp_path / "sealed.json"
    script = Path(__file__).resolve().parents[1] / "analysis" / "locked_analysis.py"
    result = subprocess.run(
        [sys.executable, str(script), str(source), str(output)],
        capture_output=True,
        text=True,
        check=True,
    )
    assert len(result.stdout.strip()) == 64
    assert json.loads(output.read_text()) == analyze_masked(rows())


def test_locked_cli_rejects_duplicate_json_keys(tmp_path):
    source = tmp_path / "bad.json"
    source.write_text('{"rows":[],"rows":[],"svf":false,"ivf":false}')
    output = tmp_path / "must-not-exist.json"
    script = Path(__file__).resolve().parents[1] / "analysis" / "locked_analysis.py"
    result = subprocess.run(
        [sys.executable, str(script), str(source), str(output)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode != 0
    assert "duplicate JSON object key" in result.stderr
    assert not output.exists()
