"""Shared synthetic fixtures. Everything here is fabricated and offline.

The authority values are SYNTHETIC placeholders for tests; they are not
evidence of any account, fee, rate, date or signature. The transport is
always httpx.MockTransport.
"""

from __future__ import annotations

import hashlib
import os
import stat

import httpx

from counted_responses_provider.authority import AuthorityRecord, profile_sha256
from counted_responses_provider.provider import SingleAttemptResponsesProvider
from qbridge.counted_runner import CountedArmRunner
from qbridge.request_records import RequestRecords
from qbridge.runner import InlineExecutor

SYNTHETIC_KEY = "sk-SYNTHETIC-OFFLINE-NEVER-VALID"
RECORDED = "2026-09-09T00:00:00Z"
VALID_THROUGH = "2026-11-21T00:00:00Z"
FAKE_HASH = hashlib.sha256(b"synthetic test evidence placeholder").hexdigest()


def synthetic_authority(**overrides) -> AuthorityRecord:
    data = {
        "scope": "study",
        "synthetic": True,
        "authorized_by": "SYNTHETIC test fixture; not an authorization",
        "recorded_at_utc": RECORDED,
        "purpose": "offline MockTransport tests",
        "profile_sha256": profile_sha256("medium"),
        "model": "gpt-5.6-sol",
        "reasoning_effort": "medium",
        "input_token_ceiling": 272000,
        "max_output_tokens": 8192,
        "count_attempt_cap": 4560,
        "generation_attempt_cap": 4560,
        "usd_ceiling": "100",
        "input_usd_per_million": "4",
        "cached_input_usd_per_million": "0.4",
        "cache_write_usd_per_million": "5",
        "output_usd_per_million": "20",
        "billing_categories": ("input", "cached_input", "cache_write", "output"),
        "rate_source": "SYNTHETIC placeholder for sol_model.md/pricing.md",
        "rate_source_sha256": FAKE_HASH,
        "price_valid_through_utc": VALID_THROUGH,
        "count_fee_ceiling_usd": "0.01",
        "count_fee_evidence": "SYNTHETIC placeholder; no real fee evidence exists",
        "count_fee_evidence_sha256": FAKE_HASH,
        "count_fee_valid_through_utc": VALID_THROUGH,
        "count_fee_covers_failed_and_rejected": True,
        "count_fee_verified": True,
        "sdk_version": "3.9.0",
        "httpx_version": "0.28.1",
    }
    data.update(overrides)
    return AuthorityRecord(**data)


def private_dir(path):
    path.mkdir()
    os.chmod(path, stat.S_IRWXU)
    return path


class Clock:
    def __init__(self, wall=None):  # default: 2026-09-09T12:00:00Z, inside validity
        wall = 1_788_955_200.0 if wall is None else wall
        self.now, self.wall, self.waits = 0.0, wall, []

    def __call__(self):
        return self.now

    def sleep(self, seconds):
        self.waits.append(seconds)
        self.now += seconds

    def time(self):
        return self.wall


def count_ok(tokens=42, **extra):
    body = {"object": "response.input_tokens", "input_tokens": tokens, **extra}
    return httpx.Response(200, json=body, headers={"x-request-id": "req_count_synthetic"})


def usage(inp=42, out=3, total=None, cached=0, written=0, reasoning=0):
    return {
        "input_tokens": inp,
        "output_tokens": out,
        "total_tokens": inp + out if total is None else total,
        "input_tokens_details": {"cached_tokens": cached, "cache_write_tokens": written},
        "output_tokens_details": {"reasoning_tokens": reasoning},
    }


def response_object(
    output_text="good", *, status="completed", usage_obj=None, effort="medium", **extra
):
    body = {
        "object": "response",
        "id": "resp_synthetic",
        "status": status,
        "model": "gpt-5.6-sol",
        "service_tier": "default",
        "truncation": "disabled",
        "max_output_tokens": 8192,
        "store": False,
        "reasoning": {"effort": effort, "summary": None},
        "text": {"verbosity": "medium", "format": {"type": "text"}},
        "prompt_cache_options": {"mode": "explicit"},
        "output": [
            {"type": "reasoning", "summary": []},
            {
                "type": "message",
                "role": "assistant",
                "content": [{"type": "output_text", "text": output_text}],
            },
        ],
        "usage": usage() if usage_obj is None else usage_obj,
    }
    body.update(extra)
    return body


def gen_ok(output_text="good", **kw):
    return httpx.Response(
        200, json=response_object(output_text, **kw), headers={"x-request-id": "req_gen_synthetic"}
    )


class Fabricated:
    """MockTransport handler: fabricated count/generation responses, no network."""

    def __init__(self, count=None, generation=None):
        self.count = count or (lambda request: count_ok())
        self.generation = generation or (lambda request: gen_ok())
        self.requests = []

    def __call__(self, request):
        self.requests.append((str(request.url), bytes(request.read())))
        if request.url.path.endswith("/input_tokens"):
            return self.count(request)
        return self.generation(request)


def make_provider(tmp_path, journal, handler, *, authority=None, clock=None, api_key=SYNTHETIC_KEY):
    records = RequestRecords(private_dir(tmp_path / "raw"), public_repo=tmp_path / "repo")
    clock = clock or Clock()
    return (
        SingleAttemptResponsesProvider(
            journal=journal,
            records=records,
            authority=authority or synthetic_authority(),
            transport_factory=lambda: httpx.MockTransport(handler),
            api_key_provider=lambda: api_key,
            wall_clock=clock.time,
        ),
        records,
        clock,
    )


def make_runner(journal, clock, *, block=0, executor=None, admission_limit=100):
    return CountedArmRunner(
        journal,
        block=block,
        arm="AI",
        objective=lambda _: 0.5,
        map_action=lambda x: x,
        clock=clock,
        sleep=clock.sleep,
        executor=executor or InlineExecutor(),
        admission_limit=admission_limit,
    )


class Parsed:
    def __init__(self, vectors, valid_count, reason, schema_valid):
        self.vectors, self.valid_count, self.reason, self.schema_valid = (
            vectors,
            valid_count,
            reason,
            schema_valid,
        )


def parse(text):
    if text == "good":
        return Parsed(((0.0,) * 20,) * 10, 10, None, True)
    return Parsed((None,) * 10, 0, "invalid_json", False)


def run(runner, provider):
    runner.initialize([[0.0] * 20] * 10)
    return runner.run_llm(
        provider,
        parse_response=parse,
        render_user=lambda _history, batch: f"fabricated user {batch}",
        system_prompt=lambda: "fabricated system",
    )


def events(journal, kind):
    return [e for e in journal.read_events() if e["kind"] == kind]
