"""FABRICATED offline responses for the dry run and for regression tests.

Nothing in this module is evidence. Every token count, usage figure, header and
body is invented so the orchestration can be exercised without a network, a
credential or a charge. A response produced here is marked
``"_fabricated": true`` in its own body so a retained record can never be
mistaken for a provider observation.

The inner transport is always ``httpx.MockTransport``; the provider refuses a
non-synthetic authority with a mock transport and a synthetic authority with a
real transport, so these fixtures cannot reach the network.
"""

from __future__ import annotations

import json

import httpx

from counted_responses_provider import contract as C

FABRICATED_MARKER = "_fabricated"


def fabricated_count_tokens(fixture) -> int:
    """A deterministic invented count. NOT a measurement and not a tokenizer."""
    return len(fixture.user_text) // 4 + len(fixture.system_text) // 4


def fabricated_proposal_text(valid: int = 10) -> str:
    """A syntactically valid section 6.7 envelope with ``valid`` usable vectors."""
    good = [0.1] * 20
    bad = ["x"] * 20
    proposals = [good if i < valid else bad for i in range(10)]
    return json.dumps({"proposals": proposals})


def count_response(tokens: int, *, status: int = 200, extra=None) -> httpx.Response:
    body = {"object": "response.input_tokens", "input_tokens": int(tokens)}
    if extra:
        body.update(extra)
    return httpx.Response(
        status, json=body, headers={"x-request-id": "req_FABRICATED_count"}
    )


def generation_response(
    *,
    counted_tokens: int,
    output_tokens: int = 320,
    cached: int = 0,
    cache_write: int = 0,
    status: str = "completed",
    text: str | None = None,
    effort: str = "medium",
    http_status: int = 200,
    overrides=None,
    headers=None,
) -> httpx.Response:
    body = {
        "object": "response",
        "id": "resp_FABRICATED",
        "status": status,
        "model": C.MODEL,
        "service_tier": "default",
        "truncation": "disabled",
        "max_output_tokens": C.MAX_OUTPUT_TOKENS,
        "store": False,
        "reasoning": {"effort": effort, "summary": None},
        "text": {"verbosity": "medium", "format": {"type": "text"}},
        "prompt_cache_options": {"mode": "explicit"},
        "output": [
            {"type": "reasoning", "summary": []},
            {
                "type": "message",
                "role": "assistant",
                "content": [
                    {
                        "type": "output_text",
                        "text": fabricated_proposal_text() if text is None else text,
                    }
                ],
            },
        ],
        "usage": {
            "input_tokens": counted_tokens,
            "output_tokens": output_tokens,
            "total_tokens": counted_tokens + output_tokens,
            "input_tokens_details": {
                "cached_tokens": cached,
                "cache_write_tokens": cache_write,
            },
            "output_tokens_details": {"reasoning_tokens": min(output_tokens, 64)},
        },
        FABRICATED_MARKER: True,
    }
    if overrides:
        body.update(overrides)
    return httpx.Response(
        http_status,
        json=body,
        headers={"x-request-id": "req_FABRICATED_gen", **(headers or {})},
    )


def error_response(http_status: int, *, code=None, kind=None, message="fabricated", headers=None):
    """A fabricated provider error object (used for 429 spend-limit regressions)."""
    error = {"message": message}
    if code is not None:
        error["code"] = code
    if kind is not None:
        error["type"] = kind
    return httpx.Response(
        http_status,
        json={"error": error, FABRICATED_MARKER: True},
        headers=headers or {},
    )


class ScriptedTransport:
    """MockTransport handler driving count/generation replies per fixture order.

    ``count_plan`` / ``generation_plan`` are lists of callables taking the
    request and returning an ``httpx.Response``; each dispatch consumes the next
    entry, and the final entry repeats. This records the exact requests seen so
    tests can assert how many dispatches happened.
    """

    def __init__(self, count_plan=None, generation_plan=None):
        self.count_plan = list(count_plan or [])
        self.generation_plan = list(generation_plan or [])
        self.count_calls = []
        self.generation_calls = []

    @staticmethod
    def _next(plan, index):
        if not plan:
            raise AssertionError("no scripted response available")
        return plan[min(index, len(plan) - 1)]

    def __call__(self, request):
        body = bytes(request.read())
        if request.url.path.endswith("/input_tokens"):
            handler = self._next(self.count_plan, len(self.count_calls))
            self.count_calls.append((str(request.url), body))
            return handler(request)
        handler = self._next(self.generation_plan, len(self.generation_calls))
        self.generation_calls.append((str(request.url), body))
        return handler(request)


def nominal_plan(fixture_set):
    """A fabricated all-pass E9: count echoed in usage, no cache activity."""
    counts = {f.name: fabricated_count_tokens(f) for f in fixture_set.fixtures}
    order = [f.name for f in fixture_set.fixtures]
    count_plan = [
        (lambda name: (lambda request: count_response(counts[name])))(name) for name in order
    ]
    generation_plan = [
        (
            lambda name: (
                lambda request: generation_response(
                    counted_tokens=counts[name],
                    text=fabricated_proposal_text(
                        0 if name == "F4_correction_no_valid_vectors" else 10
                    ),
                )
            )
        )(name)
        for name in order
    ]
    return ScriptedTransport(count_plan, generation_plan), counts


def count_from_request(request) -> int:
    """Derive the fabricated count from the request body itself.

    Order-independent: a handler built on this returns the same fabricated count
    for the same bytes, so a count and its generation always agree without the
    test having to know the dispatch order.
    """
    body, error = C.parse_json_strict(bytes(request.read()))
    if error is not None:
        raise AssertionError(f"scripted handler received non-canonical JSON: {error}")
    system = body["input"][0]["content"]
    user = body["input"][1]["content"]
    return len(user) // 4 + len(system) // 4


def derived_count(request, **kwargs):
    return count_response(count_from_request(request), **kwargs)


def derived_generation(request, **kwargs):
    """Fabricated generation reply derived from the request bytes.

    The F4 correction fixture carries the fixed ``no_valid_vectors`` reason in
    its user text, so the fabricated reply returns zero valid vectors for it.
    That keeps the section 6.7 parse result faithful to the fixture's purpose
    without the handler needing to know the dispatch order.
    """
    body, error = C.parse_json_strict(bytes(request.read()))
    if error is not None:
        raise AssertionError(f"scripted handler received non-canonical JSON: {error}")
    kwargs.setdefault("counted_tokens", count_from_request(request))
    if "text" not in kwargs and "no_valid_vectors" in body["input"][1]["content"]:
        kwargs["text"] = fabricated_proposal_text(0)
    return generation_response(**kwargs)


def derived_transport(count_plan=None, generation_plan=None):
    """ScriptedTransport whose default entries derive counts from the body."""
    return ScriptedTransport(
        count_plan or [derived_count], generation_plan or [derived_generation]
    )
