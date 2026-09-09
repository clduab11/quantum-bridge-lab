# counted_responses_provider — bounded offline package (2026-09-09)

Single-attempt OpenAI Responses provider (`prepare` / `count` / `generate`) for
`qbridge.counted_runner.CountedArmRunner`, built from immutable commit
`1129a6037a20e1935a34cc210e61431eb3b5f99b` of `clduab11/quantum-bridge-lab`.

Read `COMPATIBILITY_AND_LIMITATIONS.md` first. Nothing in this package is adopted,
frozen, or authorized to spend; no request was ever sent.

## Run the tests

```
export PYTHONPATH=<repo>/src:<this dir>:<this dir>/tests
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest -q -p no:cacheprovider tests
```

Expected: 113 collected. Against the unpatched core at the commit, 112 pass and
`test_child_killed_after_request_retention_keeps_reservation_open` fails on a
runner-side `os.killpg` EPERM (report §7.1) — reproduced in the Claude Science sandbox
(CPython 3.11.16) and in Codex's 3.11.15 environment; the test is intentionally strict and
passes against Codex's locally verified core correction (report §5.1, Codex's statement).
No experimental request is sent by any test: dispatched requests use `httpx.MockTransport`;
negative tests construct but never invoke a non-mock transport.

Preserved reference (unchanged): `cd reference_preserved && python -m pytest -q test_counted_responses_reference.py`
→ 152 passed. Aliased to the operational contract (shim in `logs/`): 150 passed, 2
representation-only failures (report §4).

## Assembly hooks for Codex

- `AuthorityRecord.load(path)` — strict JSON, duplicate keys refused, every field required.
- `seed_identity_baseline(journal, vector=..., source=..., accepted_from_e9=True)` — the only
  way a study journal receives a baseline; the provider never writes one.
- `SingleAttemptResponsesProvider(journal=, records=, authority=, transport_factory=,
  api_key_provider=, wall_clock=)` — `transport_factory` must return `httpx.MockTransport`
  for `synthetic=True` authorities; `api_key_provider` is called only inside the dispatching
  process and its value is never journaled.
