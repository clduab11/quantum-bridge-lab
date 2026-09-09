# E9 launcher — implementation report, revision 2

**Prepared for independent review. Not adopted, not frozen, not authorized, not executed.**

Baseline: `a8c3e1e83c28db80642ab0123dd1fbf4d9ff5bc2` on `research/counted-admission`. Zero provider requests, zero credits purchased, no billing setting changed, no amendment adopted, no protocol frozen, no study launched, zero study-objective candidate evaluations. Amendment A1 remains **proposed**; protocol v0.4 remains **operative and unfrozen**.

Revision 1 is preserved unchanged. This revision addresses Codex's nine findings; the finding-by-finding account, with reproductions before and after, is `e9_review_response_rev2.md`.

---

## 1. What changed

`qbridge_e9` is additive: no file at the baseline commit is modified. Two new modules, six rewritten, **150 tests collected** (up from 93): `test_gate.py` 42, `test_fixtures_identity.py` 25, `test_orchestrator.py` 24, `test_spend_limit.py` 18, `test_reopen.py` 13, `test_money.py` 11, `test_deadline.py` 10, `test_terminal_and_resume.py` 7.

| Module | Change |
|---|---|
| `deadline.py` | **New.** Wall-clock enforcement for one dispatch at the transport boundary: arm a budget, run in a daemon worker thread, cancel by closing the inner transport at expiry, reject and record any late result, raise `ReadTimeout`. `CANCEL_GRACE_SECONDS = 0.25`. Subclasses `httpx.MockTransport` when wrapping a mock so `RecordingTransport.inner_is_mock` — and therefore the synthetic/real authority boundary — is untouched. |
| `money.py` | **New.** Conservative arithmetic over every applicable input category. `worst_case_input_rate`, `conservative_generation_reservation`, `conservative_e9_ceiling`. |
| `fixtures.py` | Reviewed digests **pinned as module constants**; the manifest is checked against the pin instead of being trusted. Payloads checked directly against the pin. `repo_root` required. Unreviewed extra payload files rejected. 88 checks without a provider, 96 with. |
| `gate.py` | Real Git worktree detection (`.git` directory **or** file, literal and resolved paths, plus `git rev-parse --show-toplevel`). New `authority.conservative_ceiling` and `authorization.bound_and_timed`. `billing.account_terms` extended. `env` is a **required** argument and `os` is no longer imported. 18 → **20** requirements. |
| `orchestrator.py` | Arms the wall clock before every dispatch. Refuses on a prior terminal stop, a consumed deadline, or an unresolved reservation. Durable per-run consumed-time accounting recorded on every fixture, not only at run end. Conservative headroom required before every generation dispatch. Finished fixtures reconstructed from the journal. |
| `report.py` | Authorization and storage fields **derived** from the gate, journal and filesystem instead of hardcoded. Distinguishes issuing spending authority from consuming one. Per-run timestamped reports written with `open(..., "x")` plus an append-only index. |
| `cli.py` | `--repo-root` required everywhere. Refuses a `--work-dir` inside any Git worktree before creating anything. `RequestRecords` constructed with the verified repo root. No offline path reads the credential variable; `--check-credential` is opt-in. No implicit default subcommand. |
| `acceptance.py`, `mocks.py`, `limits.py` | Unchanged in substance; acceptance reads findings from the durable journal as before. |

The four fixed fixtures, the model profile (`gpt-5.6-sol`, medium effort, 8,192 output cap, L\* = 272,000), the 7,400 s stop limit, the 12+12 attempt caps and the scientific scope are unchanged.

---

## 2. Test evidence

All logs in `e9_test_evidence_rev2.log` were produced from the shipped revision-2 code in **one pass**. (Revision 1's log contained runs from before its last test was added; that is corrected here and acknowledged in the review response.)

| Suite | Result |
|---|---|
| Core repository (`repo/tests`) | **289 passed** |
| Provider candidate, unpatched | **113 passed** |
| Preserved reference suite, unpatched | **152 passed** |
| `qbridge_ext` | **53 passed** |
| Provider candidate with 0001+0002 | **113 passed** |
| Preserved reference with 0001+0002 | **152 passed** |
| E9 launcher, unpatched dependency | **144 passed, 6 skipped** |
| E9 launcher, 0001 only | **145 passed, 5 skipped** |
| E9 launcher, 0001+0002 | **145 passed, 5 skipped** |
| ruff (repository rule set `E4,E7,E9,F`, line length 100) | clean |

The dependency baseline is 289 + 113 + 152 + 53 = **607**, unchanged by either patch. Reproducing 289 requires `pip-audit` installed, because `qbridge.preflight` calls `importlib.metadata.version("pip-audit")`; without it two `test_preflight.py` tests fail with `PackageNotFoundError`. No test was modified to accommodate the environment.

The launcher suite runs against **three** dependency states. The 5–6 skips are two mutually exclusive skip-guarded pairs (spend-limit classification, and reservation arithmetic) plus platform guards: exactly one member of each pair runs, so neither is silently vacuous.

### New test files

| File | Tests | Covers |
|---|---|---|
| `test_deadline.py` | 10 | Cancellation of a stalled real transport; late-result rejection with a recorded digest; in-budget passthrough; daemon workers reaped; unarmed dispatch refused; mock wrapping preserves the synthetic boundary; non-preemptible mock reported as such; Codex's blocking-generation reproduction; orchestrator refuses without a guard; fresh transport per attempt. |
| `test_terminal_and_resume.py` | 7 | Both reopen reproductions; consumed time accumulating across runs; unresolved reservation refusal; rerun preserving acceptance; field-by-field reconstruction; a clean interruption between fixtures resuming with the remaining budget. |
| `test_money.py` | 11 | Worst-case rate identification; conservative reservation equals the worst-case charge; the 31.342080 ceiling; input validation; orchestrator blocking on insufficient headroom; the patched/unpatched pair. |
| `test_fixtures_identity.py` | 25 (was 13) | The self-consistent replacement fixture; the payload pin holding when the manifest pin is defeated; empty and partial source sets; required and wrong `repo_root`; extra unreviewed payload. |
| `test_gate.py` | 42 (was 22) | Real `git init` repositories, linked-worktree marker files, symlinks into repositories, containment under the verified root; six malformed approval instants, future and expired approvals, unbound and mis-bound approvals; the conservative-ceiling requirement. |
| `test_reopen.py` | 13 (was 8) | Bare invocation exits 2 cleanly; a populated credential variable cannot satisfy an offline run and never appears in a report; `--check-credential` affects one requirement only; the CLI refuses a work directory inside a worktree and creates nothing. |

---

## 3. Offline dry run

`python -m qbridge_e9.cli dry-run` is the default mode and the only mode that runs without evidence. Every response is fabricated by `qbridge_e9.mocks` and self-labelled `"_fabricated": true`; the transport is `httpx.MockTransport` throughout.

| | |
|---|---|
| Fixture checks | **96 passed, 0 failed** (88 without a provider) |
| Gate | **9 of 20 passed, 11 failed, `may_dispatch_live: false`** — correct: synthetic authority, no evidence |
| Attempts | 4 count + 4 generation, no retries |
| Ledger | 4.691732 committed against a fabricated 32.000000 ceiling |
| Acceptance | **12 of 12 conditions passed** against fabricated responses |
| Journal | 72 events |
| Wall clock | `attempt_wall_clock_enforced_at_transport: true` |
| Storage | `git_worktree_root: null`, `outside_git: true` (measured, not asserted) |

A second dry run in the same working directory reconstructs all four fixtures from the journal, dispatches nothing further, still reports `e9_accepted: true`, and writes a **new** timestamped report while leaving the first intact — two lines in `e9_reports.jsonl`.

---

## 4. Dependency patches — supplied, not applied

| Patch | Defect | Effect on existing tests |
|---|---|---|
| `0001-spend-limit-not-retryable.diff` | `contract._status_bucket` buckets **every** HTTP 429 as retryable, including the four documented billing rejections and `insufficient_quota`, which the vendor documents as not restorable by retrying. Retrying burns attempt allowance and re-reserves money against a condition only the account owner can clear. | 113/113 provider, 152/152 reference — unchanged |
| `0002-conservative-generation-reservation.diff` | `reservation_for_generation` reserves input at the uncached rate while `charge_from_usage` bills written tokens at the cache-write rate: 1.251840 reserved against 1.523840 charged, a 0.272000 shortfall per attempt at the admission limit. | 113/113 provider, 152/152 reference with **both** applied — unchanged |

Both apply cleanly to a pristine checkout in sequence (`logs/patch_apply.log`: 2 files, 78 insertions, 9 deletions). No preserved reference bytes were modified and no test was weakened. The launcher defends itself independently of both, and behaves identically whether or not they are applied — which is why its suite is run against all three states.

---

## 5. Requirement-to-code traceability

| Requirement | Enforced by |
|---|---|
| Exactly four fixed fixtures, declared order | `fixtures.REVIEWED_FIXTURE_ORDER`, `load_fixture_set` |
| Committed bytes are authoritative; pinned digests | `fixtures.REVIEWED_MANIFEST_SHA256`, `REVIEWED_PAYLOAD_SHA256`, `REVIEWED_SOURCE_SHA256` |
| Developer/user text identical across each count/generation pair | `load_fixture_set` per-fixture text checks |
| Count body is the exact projection of the generation body | `contract.verify_pair` via `load_fixture_set` |
| F3 byte-identical to F2 | `load_fixture_set` F2/F3 comparison |
| One HTTP attempt per provider call | reviewed `SingleAttemptResponsesProvider` |
| Attempt caps counted durably | `orchestrator.attempts_used` over journal reservations |
| 300 s attempt wall clock | `deadline.DeadlineGuard` + `orchestrator._dispatch` |
| 7,400 s monotonic stop limit, durable across reopen | `orchestrator.consumed_seconds/budget_seconds` |
| Predetermined retry rule, server minimum never lowered | `contract.retry_decision` |
| No generation without a valid count and admission | `orchestrator._logical`, `contract.may_dispatch_generation` |
| Conservative solvency before dispatch | `money.conservative_generation_reservation`, `orchestrator` headroom check, gate `authority.conservative_ceiling` |
| Billing rejections are not retryable | `orchestrator.SPEND_LIMIT_ERROR_CODES` (+ patch 0001) |
| Records private and outside Git | `gate.git_worktree_root`, `cli._setup`, `RequestRecords(public_repo=<verified repo root>)` |
| No replay of an unresolved attempt | `orchestrator` refusal on open reservations |
| E9 records separate from study slots | `limits.E9_ARM` asserted not in `STUDY_ARM_LABELS` |
| No study baseline seeded | absence of `seed_identity_baseline`, asserted by test |
| Unresolved requirements recorded as failures | `gate.evaluate_gate`, two statuses only |

---

## 6. Deviations and limits

- **A synchronous in-process mock handler is not preemptible.** The deadline is observed and the late result refused, but the worker thread runs to completion. It is a daemon thread and `workers_alive` reports it. Cancellation is real for a socket; for a mock it is recorded as `mock_transport_not_preemptible` rather than claimed.
- **The 0.25 s cancellation grace window** means a run can exceed its deadline by that bounded amount plus process overhead.
- **`RequestRecords` itself still accepts a Git-contained directory** when handed a fabricated guard path. That is the reviewed component's documented contract; the caller was fixed instead. If the store should detect worktrees itself, that is a third numbered patch, not a fold-in.
- **The count-request charging question is unresolved** and no software change resolves it. The 1.088 USD per count attempt used in the arithmetic is an **assumption**, not a bound: L\* = 272,000 is checked *after* a count returns, so it cannot bound the billable size of a count that is itself rejected as too large.
- **The prepaid-billing help-centre article's contents were never retrieved** — direct fetch is refused with HTTP 403 and a web search returned only its title, URL and date. A first draft of this revision recorded nine specific facts against it that had no source; they are withdrawn and the register carries a correction note. When money leaves the account is recorded as **unanswered**.
- **Account facts remain unknown** and the gate treats "unknown" as a failure. None were invented.
- **Byte length is not a token count.** These fixtures do not prove every legal history fits the context or the admission limit.
- **Count/usage equality at E9 is necessary, not sufficient** for the confirmatory claim.
- **The Responses route exposes no serving fingerprint**, so weight or serving changes that leave the echo unchanged remain undetectable. The identity vector is the weaker instrument and is recorded as such.
- **No cache-window coverage is claimed.** F2/F3 timing is recorded; a zero-cache E9 pass demonstrates no cache lifetime.
- **The launcher enforces limits conditional on the recorded prices and provider compliance. It does not enforce the invoice**, and a hash match is not verification of a charge or of an approval.
- **Environment:** actual versions are recorded in `logs/environment.txt` and section 7 of the financial proposal. Revision 1's claim of an exactly-matching environment is withdrawn; the known difference is a local interpreter of 3.11.15 against this sandbox's 3.11.16, and other packages were not compared.
