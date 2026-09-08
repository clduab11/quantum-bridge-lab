import json
import math

import pytest

from qbridge.proposals import parse_response, render_user, system_prompt


def payload():
    return {"proposals": [[0.0] * 20 for _ in range(10)]}


def test_per_slot_salvage_does_not_pack_later_candidates():
    body = payload()
    body["proposals"][1] = [True] * 20
    body["proposals"][2][0] = 0.125
    result = parse_response(json.dumps(body))
    assert len(result.vectors) == 10
    assert result.vectors[1] is None
    assert result.vectors[2][0] == 0.125
    assert result.valid_count == 9
    assert result.reason is None
    assert not result.schema_valid


@pytest.mark.parametrize("count", [9, 11, 30])
def test_wrong_envelope_count_loses_whole_response(count):
    result = parse_response(json.dumps({"proposals": [[0] * 20] * count}))
    assert result.reason == "invalid_envelope"
    assert result.valid_count == 0


@pytest.mark.parametrize("text", [
    '{"proposals":[],"proposals":[]}',
    '{"proposals":[{"x":0,"x":1}]}',
    '{"proposals":[NaN]}',
    '{"proposals":[]} trailing',
    '```\n{"proposals":[]}\n```',
    '```JSON\n{"proposals":[]}\n```',
    '{"proposals":',
])
def test_invalid_json_precedes_envelope_or_slot_salvage(text):
    result = parse_response(text)
    assert result.reason == "invalid_json"
    assert result.valid_count == 0


def test_exact_json_fence_and_large_finite_raw_domain():
    body = payload()
    body["proposals"][0][0] = float.fromhex("0x1.fffffffffffffp+1023")
    result = parse_response(" \n```json\n" + json.dumps(body) + "\n```\n")
    assert result.schema_valid and result.valid_count == 10
    assert math.isfinite(result.vectors[0][0])


@pytest.mark.parametrize("value", ['"1"', "true", "null", "1e999"])
def test_non_numeric_or_unrepresentable_values_forfeit_slots(value):
    text = '{"proposals":[' + ','.join(['[' + ','.join([value] * 20) + ']'] * 10) + ']}'
    result = parse_response(text)
    assert result.reason == "no_valid_vectors"
    assert result.valid_count == 0


def test_rendered_history_orders_by_objective_then_original_slot_and_keeps_repr():
    rows = [
        {"index": 3, "theta": [0.0] * 20, "value": 0.2},
        {"index": 2, "theta": [0.1] * 20, "value": 0.1},
        {"index": 1, "theta": [0.2] * 20, "value": 0.1},
    ]
    rendered = render_user(rows, 1)
    assert rendered.index("1 0.1 0.2") < rendered.index("2 0.1 0.1")
    assert rendered.index("2 0.1 0.1") < rendered.index("3 0.2 0.0")
    assert "Best objective so far: 0.1 at index 1." in rendered
    assert "after this batch is evaluated: 180." in rendered
    assert "after this batch is evaluated: 0." in render_user(rows, 19)
    assert "{history_table}" not in rendered
    assert "exactly 10 new parameter vectors" in system_prompt()


@pytest.mark.parametrize("rows,batch", [([], 1), ([{"index": 1,"theta": [0.] * 20,"value": 0.2}], 0)])
def test_render_rejects_missing_incumbent_or_invalid_batch(rows, batch):
    with pytest.raises(ValueError):
        render_user(rows, batch)
