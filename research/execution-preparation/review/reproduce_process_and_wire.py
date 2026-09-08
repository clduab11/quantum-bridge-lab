import hashlib
import json
import sys
import tempfile
from pathlib import Path
import httpx
from qbridge.journal import DurableJournal
from qbridge.runner import ProcessExecutor
from qbridge_ext.sol_chat_adapter import (
    AuthorityRecord,
    ProtectedStore,
    SolChatTransport,
    E9_POLICY,
    profile_sha256,
)
from qbridge_ext.study_coordinator import SpendLedger

REQ = {"system": "SYSTEM\n", "user": "USER\n", "max_tokens": 8192}
PAYLOAD = {
    "id": "synthetic",
    "object": "chat.completion",
    "created": 1,
    "model": "wrong-model",
    "service_tier": "default",
    "system_fingerprint": "fp-test",
    "choices": [
        {"index": 0, "finish_reason": "stop", "message": {"role": "assistant", "content": "{}"}}
    ],
    "usage": {
        "prompt_tokens": 10,
        "completion_tokens": 10,
        "total_tokens": 20,
        "prompt_tokens_details": {"cached_tokens": 0, "cache_write_tokens": 0},
        "completion_tokens_details": {"reasoning_tokens": 0},
    },
}


class ChangeEffort(httpx.Auth):
    def auth_flow(self, request):
        body = json.loads(request.content)
        body["reasoning_effort"] = "low"
        body["messages"][1]["content"] = "ALTERED"
        yield httpx.Request(
            request.method, request.url, headers=request.headers, content=json.dumps(body).encode()
        )


def setup(root, auth=None):
    root.mkdir()
    (root / "public").mkdir()
    (root / "private").mkdir(mode=0o700)
    path = root / "authority.json"
    path.write_text(
        json.dumps(
            {
                "usd_ceiling": "10",
                "attempt_cap": 12,
                "authorized_by": "SYNTHETIC TEST ONLY",
                "recorded_at": "1970-01-01T00:00:00Z",
                "purpose": "unit test",
                "price_valid_through_utc": "2099-01-01T00:00:00Z",
                "rate_source": "SYNTHETIC",
                "scope": "v2",
                "profile_sha256": profile_sha256("medium"),
            }
        )
    )
    authority = AuthorityRecord.load(path)
    journal = DurableJournal(root / "journal")
    ledger = SpendLedger.from_authority(
        journal,
        authority,
        input_token_ceiling=1000,
        input_usd_per_million="5",
        output_usd_per_million="20",
    )

    def handler(req):
        journal.append(
            "mock_http_dispatch", sent_effort=json.loads(req.content)["reasoning_effort"]
        )
        return httpx.Response(200, json=PAYLOAD, request=req)

    client = httpx.Client(transport=httpx.MockTransport(handler), auth=auth)
    transport = SolChatTransport(
        reasoning_effort="medium",
        authority=authority,
        ledger=ledger,
        store=ProtectedStore(root / "private", public_repo=root / "public"),
        policy=E9_POLICY,
        http_client=client,
        api_key="synthetic-not-a-credential",
    )
    return transport, journal


out = {"scope": "synthetic HTTP only; no provider or objective call", "source_sha256": {}}
for name in ("sol_chat_adapter.py", "study_coordinator.py"):
    path = Path(sys.argv[1]) / name
    out["source_sha256"][name] = hashlib.sha256(path.read_bytes()).hexdigest()
with tempfile.TemporaryDirectory(prefix="qbridge-v2-review-") as tmp:
    t, j = setup(Path(tmp) / "fork")
    executor = ProcessExecutor()
    first = executor.call(lambda: t(REQ, 5), timeout=5)
    second = executor.call(lambda: t(REQ, 5), timeout=5)
    out["halt_lost_across_fork"] = {
        "first_reported_halt": first.metadata["halted_after_this_attempt"],
        "second_http_status": second.status,
        "mock_dispatches": sum(e["kind"] == "mock_http_dispatch" for e in j.read_events()),
    }
    j.close()
    t, j = setup(Path(tmp) / "wire", ChangeEffort())
    result = t(REQ, 5)
    out["modified_wire_accepted"] = {
        "reported_sent_bytes_violation": result.metadata.get(
            "sent_bytes_contract_violation", False
        ),
        "mock_efforts": [
            e["sent_effort"] for e in j.read_events() if e["kind"] == "mock_http_dispatch"
        ],
    }
    j.close()
print(json.dumps(out, indent=2))
