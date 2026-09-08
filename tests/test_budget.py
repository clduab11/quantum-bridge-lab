"""Hand-calculated planning scenarios; no model or study objective is invoked."""

import json
import os
import subprocess
import sys
from decimal import Decimal, localcontext
from pathlib import Path

import pytest


def scenario(**changes):
    from qbridge.budget import calculate_budget

    options = {
        "input_token_ceiling": 1000,
        "input_usd_per_million": "2",
        "output_usd_per_million": "3",
        "extra_usd_reserve": "0.001",
        "max_e9_attempts": 2,
    }
    options.update(changes)
    return calculate_budget(**options)


def test_both_stages_include_corrections_retries_and_separate_e9():
    result = scenario()
    assert result["protocol"] == {
        "stages": 2,
        "blocks": 40,
        "all_arms_allotted_objective_slots": 24000,
        "scheduled_calls": 760,
        "logical_call_ceiling": 1520,
        "transport_attempt_ceiling": 4560,
    }
    scheduled = result["scheduled_no_retry"]
    assert scheduled["attempts"] == 760
    assert scheduled["input_tokens"] == 760000
    assert scheduled["output_tokens"] == 6225920
    assert Decimal(scheduled["input_usd"]) == Decimal("1.52")
    assert Decimal(scheduled["output_usd"]) == Decimal("18.67776")
    assert Decimal(scheduled["token_usd"]) == Decimal("20.19776")
    maximum = result["retry_correction_ceiling"]
    assert maximum["attempts"] == 4560
    assert maximum["input_tokens"] == 4560000
    assert maximum["output_tokens"] == 37355520
    assert Decimal(maximum["token_usd"]) == Decimal("121.18656")
    assert result["e9"]["attempts"] == 2
    assert result["e9"]["input_tokens"] == 2000
    assert result["e9"]["output_tokens"] == 16384
    assert Decimal(result["e9"]["token_usd"]) == Decimal("0.053152")
    assert result["combined_totals_usd"] == {
        "scheduled_plus_e9_and_reserve": "20.26",
        "retry_correction_plus_e9_and_reserve": "121.25",
    }


def test_tiny_positive_reserve_is_rounded_up_and_explicit_zero_stays_zero():
    options = {"input_usd_per_million": "0", "output_usd_per_million": "0"}
    tiny = scenario(**options, max_e9_attempts=0, extra_usd_reserve="0.000000000001")
    assert tiny["combined_totals_usd"]["retry_correction_plus_e9_and_reserve"] == "0.01"
    zero = scenario(**options, max_e9_attempts=0, extra_usd_reserve="0")
    assert zero["combined_totals_usd"]["scheduled_plus_e9_and_reserve"] == "0.00"
    assert Decimal(zero["e9"]["token_usd"]) == 0


def test_caller_decimal_context_cannot_round_the_scenario_down():
    with localcontext() as context:
        context.prec = 3
        result = scenario()
    assert Decimal(result["retry_correction_ceiling"]["token_usd"]) == Decimal("121.18656")
    assert result["combined_totals_usd"]["retry_correction_plus_e9_and_reserve"] == "121.25"


def test_caller_decimal_exponent_limits_cannot_overflow_valid_money():
    with localcontext() as context:
        context.Emax = 2
        context.Emin = -2
        result = scenario()
    assert result["combined_totals_usd"]["retry_correction_plus_e9_and_reserve"] == "121.25"


def test_result_retains_assumptions_and_never_implies_verified_authority():
    result = scenario()
    assert result["kind"] == "conditional_budget_scenario"
    assert result["currency"] == "USD"
    assert result["tokenizer_cap_verified"] is False
    assert result["spending_authorized"] is False
    assert result["billing_complete"] is False
    assert result["assumptions"] == {
        "input_token_ceiling": 1000,
        "output_token_ceiling": 8192,
        "input_usd_per_million": "2",
        "output_usd_per_million": "3",
        "extra_usd_reserve": "0.001",
        "max_e9_attempts": 2,
    }


@pytest.mark.parametrize(
    "field,bad_values",
    [
        ("input_token_ceiling", [None, True, "1000", 1000.0, 0, -1, 1_000_000_001]),
        ("max_e9_attempts", [None, False, "2", 2.0, -1, 1_000_001]),
    ],
)
def test_token_and_attempt_counts_require_bounded_native_integers(field, bad_values):
    for value in bad_values:
        with pytest.raises(ValueError, match=field):
            scenario(**{field: value})


@pytest.mark.parametrize(
    "field", ["input_usd_per_million", "output_usd_per_million", "extra_usd_reserve"]
)
@pytest.mark.parametrize("value", [None, True, 2, 2.0, Decimal("2"), "NaN", "Infinity", "-1"])
def test_every_money_field_rejects_unknown_non_string_or_nonfinite_values(field, value):
    with pytest.raises(ValueError, match=field):
        scenario(**{field: value})


@pytest.mark.parametrize(
    "value",
    ["", " ", " 2", "2 ", "1_000", "1,000", "-0", "1e-13", "1e13", "1000000000001", "0" * 65],
)
def test_money_syntax_and_precision_bounds_fail_closed(value):
    with pytest.raises(ValueError, match="input_usd_per_million"):
        scenario(input_usd_per_million=value)


def test_explicit_boundary_values_remain_exact():
    result = scenario(
        input_token_ceiling=1_000_000_000,
        input_usd_per_million="1e12",
        output_usd_per_million="1e-12",
        extra_usd_reserve="0",
        max_e9_attempts=1_000_000,
    )
    assert Decimal(result["e9"]["input_usd"]) == Decimal("1000000000000000000000")
    assert Decimal(result["e9"]["output_usd"]) == Decimal("0.000000008192")
    assert result["combined_totals_usd"]["retry_correction_plus_e9_and_reserve"] == (
        "1004560000000000000000.01"
    )


def test_unknown_keyword_is_rejected_instead_of_silently_ignoring_a_charge():
    with pytest.raises(TypeError, match="cache_usd"):
        scenario(cache_usd="20")


@pytest.mark.parametrize(
    "missing",
    [
        "input_token_ceiling",
        "input_usd_per_million",
        "output_usd_per_million",
        "extra_usd_reserve",
        "max_e9_attempts",
    ],
)
def test_every_caller_assumption_is_required(missing):
    from qbridge.budget import calculate_budget

    options = {
        "input_token_ceiling": 1000,
        "input_usd_per_million": "2",
        "output_usd_per_million": "3",
        "extra_usd_reserve": "0",
        "max_e9_attempts": 0,
    }
    del options[missing]
    with pytest.raises(TypeError, match=missing):
        calculate_budget(**options)


def cli_arguments():
    return [
        "--input-token-ceiling",
        "1000",
        "--input-usd-per-million",
        "2",
        "--output-usd-per-million",
        "3",
        "--extra-usd-reserve",
        "0.001",
        "--max-e9-attempts",
        "2",
    ]


def run_cli(arguments, cwd, optimize=False):
    src = str(Path(__file__).resolve().parents[1] / "src")
    return subprocess.run(
        [sys.executable, *(["-OO"] if optimize else []), "-m", "qbridge.budget", *arguments],
        cwd=cwd,
        env={**os.environ, "PYTHONPATH": src},
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )


@pytest.mark.parametrize("optimize", [False, True])
def test_cli_emits_conditional_json_without_creating_output_files(tmp_path, optimize):
    result = run_cli(cli_arguments(), tmp_path, optimize=optimize)
    assert result.returncode == 0, result.stderr
    assert result.stdout, "CLI must emit its computed JSON scenario"
    data = json.loads(result.stdout)
    assert data["combined_totals_usd"]["retry_correction_plus_e9_and_reserve"] == "121.25"
    assert data["spending_authorized"] is False
    assert data["conditions"]
    assert result.stderr == ""
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize("omitted_index", [0, 2, 4, 6, 8])
def test_cli_requires_every_price_cap_reserve_and_e9_count(tmp_path, omitted_index):
    arguments = cli_arguments()
    omitted = arguments[omitted_index]
    del arguments[omitted_index : omitted_index + 2]
    result = run_cli(arguments, tmp_path)
    assert result.returncode == 2
    assert omitted in result.stderr
    assert result.stdout == ""


@pytest.mark.parametrize(
    "arguments",
    [
        [*cli_arguments(), "--cache-usd", "20"],
        ["--input-token-ceiling", "1.5", *cli_arguments()[2:]],
        [*cli_arguments()[:2], "--input-usd-per-million", "NaN", *cli_arguments()[4:]],
    ],
)
def test_cli_rejects_unknown_charge_or_invalid_assumption(tmp_path, arguments):
    result = run_cli(arguments, tmp_path)
    assert result.returncode == 2
    assert result.stdout == ""
    assert "error:" in result.stderr
