"""Normative response parsing and literal prompt rendering for protocol v0.4."""

from dataclasses import dataclass
from importlib.resources import files
import math
import json
import re
from numbers import Real


@dataclass(frozen=True)
class ParseResult:
    vectors: tuple[tuple[float, ...] | None, ...]
    reason: str | None
    schema_valid: bool

    @property
    def valid_count(self) -> int:
        return sum(vector is not None for vector in self.vectors)


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate key")
        result[key] = value
    return result


def _reject_constant(value):
    raise ValueError("nonstandard JSON constant")


def _invalid(reason):
    return ParseResult((None,) * 10, reason, False)


def parse_response(text: str) -> ParseResult:
    """Validate the whole envelope, then preserve each proposal's original slot."""
    if not isinstance(text, str):
        return _invalid("invalid_json")
    text = text.strip()
    fenced = re.fullmatch(r"```json\r?\n([\s\S]*)\r?\n```", text)
    if fenced:
        text = fenced.group(1)
    try:
        body = json.loads(
            text,
            object_pairs_hook=_unique_object,
            parse_constant=_reject_constant,
            parse_int=float,
            parse_float=float,
        )
    except (ValueError, RecursionError, OverflowError):
        return _invalid("invalid_json")
    if (
        not isinstance(body, dict)
        or set(body) != {"proposals"}
        or not isinstance(body["proposals"], list)
        or len(body["proposals"]) != 10
    ):
        return _invalid("invalid_envelope")
    vectors = []
    for candidate in body["proposals"]:
        if (
            isinstance(candidate, list)
            and len(candidate) == 20
            and all(type(x) is float and math.isfinite(x) for x in candidate)
        ):
            vectors.append(tuple(candidate))
        else:
            vectors.append(None)
    count = sum(vector is not None for vector in vectors)
    return ParseResult(tuple(vectors), "no_valid_vectors" if count == 0 else None, count == 10)


def render_user(history: list[dict], batch: int) -> str:
    """Render valid mapped observations; never infer missing incumbents or round values."""
    if type(batch) is not int or not 1 <= batch <= 19 or not history:
        raise ValueError("valid history and batch 1..19 required")
    seen = set()
    clean = []
    for row in history:
        if set(row) != {"index", "theta", "value"}:
            raise ValueError("unexpected history fields")
        index, theta, value = row["index"], row["theta"], row["value"]
        if type(index) is not int or not 1 <= index <= 10 * batch or index in seen:
            raise ValueError("duplicate or out-of-range history index")
        if (
            isinstance(value, bool)
            or not isinstance(value, Real)
            or not math.isfinite(value)
            or not 0 <= value <= 1
        ):
            raise ValueError("invalid history objective")
        if len(theta) != 20 or any(
            isinstance(x, bool) or not isinstance(x, Real) or not math.isfinite(x) for x in theta
        ):
            raise ValueError("invalid mapped history vector")
        if any(
            math.hypot(float(theta[k]), float(theta[k + 1])) > 1 + 16 * 2**-52
            for k in range(0, 20, 2)
        ):
            raise ValueError("history vector is outside mapped domain")
        seen.add(index)
        clean.append((float(value), index, tuple(float(x) for x in theta)))
    clean.sort(key=lambda row: (row[0], row[1]))
    table = "\n".join(
        " ".join([str(index), repr(value), *(repr(x) for x in theta)])
        for value, index, theta in clean
    )
    template = files("qbridge").joinpath("prompts/user_template_v0.3.txt").read_text()
    replacements = {
        "history_table": table,
        "best_I": repr(clean[0][0]),
        "best_index": str(clean[0][1]),
        "remaining_after": str(200 - 10 * (batch + 1)),
    }
    # Literal replacement leaves the mathematical set braces in the normative text intact.
    for name, value in replacements.items():
        template = template.replace("{" + name + "}", value)
    return template


def system_prompt() -> str:
    return files("qbridge").joinpath("prompts/system_v0.3.txt").read_text()
