# Single-attempt Responses provider — compatibility report and limitations

Date: 2026-09-09. Author: Claude Science (bounded offline work order). Reviewer during
construction: Codex (independent challenge messages, all findings listed in §6).

**Status.** Offline implementation and challenge only. Nothing here selects a provider,
adopts an amendment, closes a gate, freezes a manifest, launches E9 or the study,
reads an API key, or authorizes spending. Every response body, count, fee, rate, date
and authority value in the tests is fabricated and marked synthetic. **No experimental or
API request was sent** to any provider endpoint. Network was used only to retrieve the
source repository from GitHub at the immutable commit (§1). Every test request that is
dispatched goes through `httpx.MockTransport`; negative tests also *construct* a non-mock
`httpx.HTTPTransport` to show that the provider refuses a synthetic authority with it — that
transport is never invoked (asserted: no `provider_dispatch_intent`, no raw record).

## 1. Inputs (all bytes fetched from the immutable commit, hashed in HASH_MANIFEST.json)

Repository `clduab11/quantum-bridge-lab`, commit `1129a6037a20e1935a34cc210e61431eb3b5f99b`.
Files read: `src/qbridge/counted_runner.py`, `request_records.py`, `journal.py`,
`runner.py`, `tests/test_counted_runner.py`, `research/counted-admission/STATUS.md`,
`research/counted-admission/claude-science/counted_responses_reference.py` (rev 4),
`test_counted_responses_reference.py` (152 tests),
`counted_responses_request_accounting_contract_2026-09-08.md`, and the earlier
`research/execution-preparation/claude-science/qbridge_ext/sol_chat_adapter.py` (conventions
only; nothing imported from it). Companion documents NOT read in this session:
`research/counted-admission/BUDGET.md` and `AMENDMENTS.md` (the per-class maxima 12/4,560 are
taken from STATUS.md and the accounting contract as recalled; Codex confirmed them in review).

Codex's integration note (local, not pushed at the time): `CountedArmRunner._halted` now
ranks IVF > non-accounting halt > accounting; `_halt` persists stricter later findings; the
current-text accounting exception requires the selected durable halt itself to be
accounting-only; runner suite 18 tests; no public interface change. This package was built
against the published commit and independently applies the same ranking on the provider side
(§3.6), so it does not depend on the unpublished runner delta.

## 2. Package layout

```
counted_responses_provider/
  contract.py     operational copy of the reference (fixes F1-F8; diff in reference_to_contract.diff)
  authority.py    AuthorityRecord: fail-closed dispatch authority, validated on construction
  ledger.py       MoneyLedger: durable exact-Fraction reservations, two request classes
  transport.py    RecordingTransport: pre-send verification, retention before dispatch, one wire call
  provider.py     SingleAttemptResponsesProvider: prepare / count / generate for CountedArmRunner
tests/            support.py (synthetic fixtures), 113 tests (see §5)
reference_preserved/   byte-identical reference module + its 152 tests (unchanged)
logs/             pytest / ruff / environment logs from this sandbox
HASH_MANIFEST.json     SHA-256 of every file, recomputed from final bytes
```

Import path: `PYTHONPATH=<repo>/src:<pkg>:<pkg>/tests`. Requires openai 3.9.0 and httpx 0.28.1
exactly (checked at construction and again before every dispatch); httpx2 2.12.0 is present
as the SDK's dependency but the SDK is given an explicit legacy `httpx.Client`.

## 3. Design decisions and the evidence behind them

### 3.1 Wire path (empirical SDK probes, this sandbox, openai 3.9.0 + httpx 0.28.1)
- The SDK accepts a legacy `httpx.Client` through its compatibility layer and hands the
  transport a legacy `httpx.Request`; body bytes are compact JSON with sorted keys, so the
  actual wire bytes equal the canonical bytes in every fabricated case (the transport still
  verifies by strict re-parse and canonical comparison, never by assuming this).
- Any exception raised inside the transport surfaces as `openai.APIConnectionError` with the
  cause attached; `httpx.ReadTimeout` maps to `APITimeoutError`; 3xx as well as 4xx/5xx
  raise `APIStatusError` (redirects are therefore never followed: `follow_redirects=False`
  on the client and a 3xx is classified as a contract anomaly).
- `responses.input_tokens.with_raw_response.count(...)` exists and posts to
  `/v1/responses/input_tokens`.
- `max_retries=0` is set on construction and asserted before arming the transport.

### 3.2 Single wire call per provider method
`RecordingTransport` is armed for exactly one attempt. It refuses (before any inner call):
a request while disarmed, a second request in one attempt, a method/URL mismatch, bytes that
are not strict JSON (duplicate keys anywhere), bytes whose canonical form differs from the
bound body, and — after those checks, at the wire boundary — a failed re-read of the durable
halt / authority / price validity / ledger (review fix R3). Rejected bytes are retained as
`<prefix>.rejected_request.json`. Retention of the outgoing bytes happens before the inner
transport is invoked; the raw response body and filtered headers are retained before the SDK
parses anything. Authorization-bearing headers are never written.

### 3.3 Authority (fail-closed)
`AuthorityRecord` requires every dispatch-relevant fact and rejects unknowns: scope (`e9` or
`study`), synthetic flag, profile hash equal to the frozen request profile hash, exact model,
Sol effort, input ceiling ≤ 272,000, `max_output_tokens == 8192`, per-class attempt caps
bounded by the prospective scope maxima (12/12 E9, 4,560/4,560 study — a larger cap needs a
separately adopted amendment), positive USD ceiling, four positive bounded rates with source
hash and validity instant, count-fee ceiling with its own evidence hash, validity instant and an
explicit `covers_failed_and_rejected == True` flag, pinned SDK/httpx versions, and
`recorded_at ≤ both validity endpoints`. `price_valid_at(when)` requires a finite native float
inside `[recorded_at, min(price_valid_through, count_fee_valid_through)]`. Authority JSON is
parsed with duplicate-key rejection. The provider binds the authority hash into the journal on
construction, refuses a different authority for the same scope, and re-validates the (frozen)
record plus the journal binding before every dispatch and again at the wire boundary, so an
in-memory mutation or an expired instant blocks dispatch.

### 3.4 Money
Two request classes, one durable `MoneyLedger` per scope in the runner's `DurableJournal`.
Count attempts reserve the verified per-count fee ceiling and always retain it
(`retained_ceiling`); generation attempts reserve exact input + full 8,192-token output cap.
Settlement outcomes: `released_not_dispatched`, `retained_unknown`, `retained_ceiling`,
`retained_unreconciled`, `settled_actual`, `overrun_recorded`. Review fix R1: an unreconciled
report (contradictory total) books `max(reserved, known category charge)` and flags an
overrun when the known charge exceeds the reservation, so the bound never understates a known
charge. Overruns are recorded unclipped and halt the ledger. Amounts are exact Fractions
serialized as `numerator/denominator` with a bounded grammar; `billing_reconciled` is always
`null` because no invoice is ever inspected here. A crashed child leaves its reservation open,
and open reservations count in full against the ceiling in every later process.

### 3.5 Every 2xx object is settled before classification
Strict parse → `settle_response` (usage findings, exact charge, reconciliation) → ledger
settlement → profile echo validation → identity vector and comparison → status/error
classification → halt ranking → runner result. Refusal parts or reasoning-only output yield
`""` (zero valid vectors) and never a halt.

### 3.6 Halt ranking (independent of the runner delta)
`ivf` (inferential_failure) > compatibility/credential/authority > accounting. A stricter
finding is persisted as `provider_halted` even when a weaker halt already exists;
`provider_halt_detail` carries the class, findings and `transport_reservation`. The
current-text accounting exception (`accept_received_on_halt=True`) is returned only when the
object has no stricter finding of its own and no stricter halt is durable at return time
(including one persisted by another process during the attempt). In E9 scope every halt is an
`e9_fail:*` and the exception is never granted.

### 3.7 Identity baseline: provisional (E9) versus accepted (study)
The provider never writes `identity_baseline`. In E9 scope a clean completed object records a
provisional `identity_observation` (`provisional: true, accepted: false`); later E9 responses
are compared against the first observation, so drift within E9 is still an `e9_fail`. Study
scope refuses dispatch (authority-class halt) unless the journal carries an
`identity_baseline` with `scope: study` and `accepted_from_e9: true` whose vector validates
structurally; `seed_identity_baseline(journal, vector=..., source=..., accepted_from_e9=True)`
is the assembly helper Codex calls after a recorded E9 acceptance. Acceptance itself is not
implemented here.

### 3.8 Receipt binding
`generate` requires the `CountReceipt` to match: the runner's `reserved` event of that exact
transport reservation (class count, same arm/block/batch/logical, `body_sha256` equal to the
receipt digest equal to `sha256(pair.count_body)`), its `completed` event (`count_ok`, same
`counted_tokens`), the provider's own `provider_attempt` for that reservation (`count_ok`,
same `counted_tokens`, same canonical hash) and exactly one matching `count_receipt`. A forged
token value tied to a genuine count attempt, a swapped logical key, a substituted digest, or
an appended `count_receipt` without a genuine attempt behind it all refuse without dispatch
(tested).

### 3.9 Journal keys
Provider events use `transport_reservation` (the runner's reservation id) and
`money_reservation`; the top-level `reservation` key is never written by this package.
`provider_dispatch_intent` carries `transport_reservation = context.reservation` and the raw
record filename prefix separately as `record_prefix` (Codex provenance correction).

## 4. Reference defects fixed in the operational copy (reference itself unchanged)

| id | defect in rev 4 | fix |
|----|-----------------|-----|
| F1 | `canonical_bytes` emitted `NaN`/`Infinity` (invalid JSON) | `allow_nan=False` |
| F2 | `parse_json_strict` accepted `NaN`/`Infinity` literals | `parse_constant` rejects; `RecursionError` mapped |
| F3 | non-ASCII text raised `UnicodeEncodeError` | uniform `ContractViolation` |
| F4 | Retry-After `str.isdigit()` accepted non-ASCII digits / unbounded length; float ceil | ASCII `[0-9]{1,15}`, `math.ceil`, bounded HTTP-date delta |
| F5 | money strings like `1e999999999` hung in `Fraction(Decimal)` | bounded plain-decimal grammar (≤20+20 digits, no sign/exponent) |
| F7 | identity tags were tuples; a journal JSON round trip yields lists → every stored baseline compared unequal (13 false changes; Codex reproduction) | tags are lists `["absent"]` / `["present", canonical]`; `compare_identity` normalizes both sides; `validate_identity_vector` added |
| F8 | `money_str`/`_to_fraction` used `localcontext()` which inherits ambient `Emax`/`Emin`/traps (Overflow under `prec=2, Emax=1`); `Decimal("1." + "0"*100 + "1")` passed the `adjusted()` bound with a 10**101 denominator | integer-only arithmetic and fixed-point rendering; Decimal inputs bounded by coefficient length and raw exponent (≤40) |

(F6 was an internal note about `_lookup` on list-valued nested objects; the reference already
guarded it, so no code change was made and the id is retired.)

**Compatibility with the preserved 152 reference tests** (aliased to the final `contract.py`;
`logs/pytest_reference_aliased_to_contract.log`, shim in `logs/alias_shim_counted_responses_reference.py`):
150 passed, 2 failed — `test_absent_optional_safe_fields_are_acceptable` (expects the tuple
`("absent",)` for `tools`) and `test_identity_vector_is_presence_tagged_and_covers_whole_frozen_objects`
(expects `("present", "null")` for `temperature`). Both are representation assertions changed
deliberately by F7; Codex reproduced the same 150/2 result on an earlier snapshot
(`345b6ff2…`, before F8). The equivalent absent / present-null / whole-object semantics with
list tags are covered by `test_f7_list_tag_semantics_absent_present_null_and_whole_objects`.
The preserved module passes its own 152 tests unchanged (`logs/pytest_reference_preserved_152.log`).

## 5. Verification in this sandbox (`logs/`)

Three environments must be kept distinct:
1. **This sandbox** (`qbridge` conda env): CPython 3.11.16, openai 3.9.0, httpx 0.28.1,
   httpx2 2.12.0, pytest 9.1.1, ruff 0.16.6 (`logs/environment_versions.txt`). All results in
   `logs/` come from here.
2. **Codex's reviewed local environment**: Python 3.11.15 (Codex's statement). Results from it
   are reported in §5.1 as Codex's statements, not re-run here.
3. **The eventual frozen study environment**: not yet defined. The isolated SDK lock at
   `research/execution-preparation/claude-science/uv.lock` (verified at the commit) already
   resolves openai 3.9.0 and httpx 0.28.1 under `requires-python = "==3.11.*"`; neither that
   lock nor `.python-version` (`3.11`) pins a patch version, and this package does not claim one.

- Provider suite (sandbox, historical, preserved): **112 passed, 1 failed** of 113
  (`logs/pytest_provider_suite_sandbox.log`). The failure is
  `test_child_killed_after_request_retention_keeps_reservation_open`, kept STRICT on Codex's
  instruction; see §5.1 and §7.1. The core clone used for this run is the unpatched commit.
- Repo core suite at the commit, same env: 280 passed (`logs/pytest_repo_core_sandbox.log`).
- Ruff (repo configuration): all checks passed; formatted (`logs/ruff_*.log`). `contract.py`
  keeps the reference's formatting so the diff stays limited to the F-hunks.

### 5.1 Reported local results (Codex's statements; not re-run in this sandbox)
- Unchanged provider suite on the unpatched core, Codex's 3.11.15 environment: 112 passed /
  1 failed in 34.04 s — the same abrupt-child-exit case, confirming §7.1 is not sandbox-specific.
- Root core correction (Codex-owned, `qbridge/runner.py` `ProcessExecutor`): reaps an exited
  worker before `killpg`, polls its exit status in bounded 50 ms waits (a non-detached
  descendant can hold the sentinel pipe open), and rejects non-finite timeouts. Locally
  verified by 8 focused cancellation/crash tests plus all 5 unchanged provider fork/crash tests
  (5/5 strict, including the previously failing test). Final combined run pending at the time
  of this report; the import record will identify the verified core fix.

Coverage by work-order item: MockTransport + real `ProcessExecutor` children for both bodies;
one HTTP request per attempt across every retryable status (runner retries observed as separate
attempts, each with `requests_seen == 1`); redirects and SDK retries disabled; tampered wire
body → zero inner dispatch, rejected bytes retained, compatibility halt, reservation released;
request bytes durable before the mocked dispatch (asserted from inside the handler);
timeout/connection → full reservation retained; overrun unclipped; R1 contradictory total;
authority construction failures (23 parameterized), expiry, mutation, second authority, synthetic
authority with a non-mock transport; forged receipts (5 variants); missing credential; E9 class
cap at the 13th attempt; monetary ceiling refusal before dispatch; baseline drift, profile drift,
appearance/disappearance; identical responses across successive forked children and after
close/reopen (no false halt); E9 provisional observation and study-without-baseline refusal;
simultaneous IVF + accounting findings ranked IVF; stricter halt persisted during an attempt
suppresses the accounting exception; failed/incomplete/unexpected-status objects; duplicate-key
bodies; refusal/reasoning-only text; Retry-After delta, HTTP-date, malformed and `retry-after-ms`
retention; response-retention failure after dispatch; child IVF halt surviving the fork and
blocking the next block; killed child leaving the reservation open (strict, §7.1).

## 6. Review findings received and their disposition

| source | finding | disposition |
|--------|---------|-------------|
| Codex R1 | ledger booked only the reservation for `retained_unreconciled` even when the known category charge was larger | confirmed; fixed; regression `test_ledger_r1_*` and `test_r1_contradictory_total_*` |
| Codex R2 | `price_valid_at` accepted `-inf` and instants before `recorded_at`; caps bounded at 1e6; count-fee evidence lacked hash/validity/failed-attempt coverage; authority JSON accepted duplicate keys | all confirmed; fixed; tests in `test_contract_fixes_and_authority.py` |
| Codex R3 | re-read authority/halt/ledger at the transport dispatch boundary | confirmed as a small window; guard added inside `RecordingTransport.handle_request` |
| Codex | identity tuple/list round trip (F7) | confirmed; fixed; fork + reopen tests |
| Codex | `_receipt_valid` too weak | confirmed; strengthened (§3.8); forged-receipt tests |
| Codex | E9 provisional vs accepted baseline | confirmed design gap; implemented (§3.7) |
| Codex | `money_str` ambient Decimal context; Decimal coefficient bound (F8) | confirmed; fixed; exact-case tests |
| Codex | `provider_dispatch_intent.transport_reservation` carried the filename prefix | confirmed; fixed; asserted in `test_request_is_durable_before_mocked_dispatch` |
| Codex | expiry tests used 2025-11-21 (before `recorded_at`) | confirmed; both tests now derive the instant from the authority and assert it is after the recorded interval |
| Codex | 150/2 aliased reference compatibility | reproduced on the final bytes (§4) |

## 7. Limitations, environment findings and open items

### 7.1 Runner-side finding (Codex-owned code, not modified here)
`qbridge/runner.py`, `ProcessExecutor._run`, `finally` block: `os.killpg(process.pid,
signal.SIGKILL)` raises `PermissionError: [Errno 1] Operation not permitted` in this sandbox
when the child exited via `os._exit(1)` without sending a result. Context: `received` is False,
so `process.join` is skipped and the child is an unreaped zombie whose `setsid()` process group
has no signalable member; only `ProcessLookupError` is caught, so `WorkerCrashed` is masked and
`CountedArmRunner` records `attempt_uncertain(error=PermissionError)` and halts with
`provider_client_error` instead of recovering with `transport_interruption`. Minimal
reproduction: `ProcessExecutor().call(lambda: os._exit(1), timeout=10)` (macOS 26.5.2 arm64).
**Reproduced independently by Codex in the authorized local Python 3.11.15 environment**
(unchanged suite: 112 passed / 1 failed in 34.04 s, same `provider_client_error`), so this is
stock-macOS behaviour of the core `ProcessExecutor` cleanup — an unreaped exited worker reaches
`killpg` before reaping and `PermissionError` masks `WorkerCrashed` — not a sandbox artifact.
Codex owns the core correction and will add abrupt-exit and descendant-cleanup regressions
before rerunning this strict test; the cloned core used to build this package was not patched,
and the failing log is retained as-is. The provider's durable state is correct in both
environments (request bytes retained, `money_reserved` open and counted against the ceiling, no
false halt written by the provider). The eventual import record identifies the separately
verified root core fix.

### 7.2 What this package does not establish
- No live request was made; SDK behaviour is established only against `MockTransport`.
  Response shapes, header names (`x-request-id`, `retry-after-ms`), the count endpoint's
  billing and the exact `usage` layout for gpt-5.6-sol are fabricated here and remain
  documentation-derived assumptions until E9.
- Software bounds are conditional on provider compliance (count-to-send identity, echo
  fidelity, usage accuracy). `billing_reconciled` is `null` everywhere; only an invoice/usage
  export can close it.
- The identity vector is an observable-metadata standard with no fingerprint; undetectable
  drift is acknowledged (contract_resolution_assessment_2026-09-08.md).
- The authority record verifies structure, not truth: a fabricated-but-well-formed record
  passes construction, which is why `synthetic=True` is required for `MockTransport` and
  refused with any other transport. Real E9 authority values (rates, fee evidence, tier,
  validity) are unknown to this session and were not invented.
- E9 acceptance, manifest assembly, the frozen study environment, the core runner fix and its
  publication are Codex's work; this package has not been imported into the repository.

### 7.3 Environment
Sandbox env `qbridge` (CPython 3.11.16) is neither Codex's reviewed 3.11.15 environment nor a
frozen study environment (§5). tiktoken vocabularies are not reachable here (no local token
estimate was produced, and none would be a provider count). Tarball packed with
`COPYFILE_DISABLE=1 --format=ustar`, cache directories excluded; hashes recomputed from final
bytes after the last documentation edit (`HASH_MANIFEST.json`). Python sources are unchanged
since the 112/1 run (their hashes in the manifest are unchanged from the previous manifest).
