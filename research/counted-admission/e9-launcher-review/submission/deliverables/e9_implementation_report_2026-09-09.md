# E9 launcher — implementation report

**Prepared for independent review. Not adopted, not frozen, not authorized, not executed.**

Baseline: `a8c3e1e83c28db80642ab0123dd1fbf4d9ff5bc2` on `research/counted-admission` (verified: the commit exists on exactly that one remote branch, authored 2026-09-08 20:14:07 −0500, subject "Complete counted provider review and explain quantum-control study").

Zero provider requests were made. Zero credits were purchased. No billing setting was changed. Amendment A1 remains **proposed**; protocol v0.4 remains **operative and unfrozen**.

---

## 1. What was built

A new package, `qbridge_e9`, that supplies the E9 entry point listed as remaining work in `research/counted-admission/STATUS.md`. It is additive: no file at the baseline commit was modified. Eight modules, 93 tests.

| Module | Responsibility |
|---|---|
| `limits.py` | The fixed stopping rules. Rejects any drift from the reviewed profile, and asserts the arithmetic identity behind the 7,400 s monotonic stop limit (24 × 300 s attempt timeouts + 8 × 25 s backoffs). Uses record label `E9`, which is asserted **not** to be one of the study arm labels. |
| `fixtures.py` | Loads the four committed fixtures in declared order and records every verification as a named requirement. 76 checks, all of which raise rather than warn. |
| `gate.py` | Evaluates 18 independent live-dispatch requirements. Absence is failure. Never reads or logs credential material. |
| `orchestrator.py` | Owns the fixture sequence, both attempt caps, the attempt timeout, the retry rule, the monotonic stop limit, admission and the count receipt. |
| `acceptance.py` | Encodes the A1.11 pass conditions, each naming the requirement and the code that enforces it, evaluated from the durable journal. |
| `mocks.py` | Fabricated offline responses. Every body carries `"_fabricated": true`. |
| `report.py` | The durable JSON report, including an explicit limitations list. |
| `cli.py` | Four subcommands. The offline dry run is the default. |

### Division of responsibility

The reviewed provider owns **exactly one HTTP attempt**: bound bytes, pre-send verification, durable retention before dispatch, monetary reservation, usage settlement, profile and identity checks, halt persistence. The orchestrator owns everything across attempts. This is the split the work order specifies, and it is why the launcher never calls `httpx` itself.

**Deliberate difference from `CountedArmRunner`:** the study runner forks a worker per attempt via `ProcessExecutor`. The E9 orchestrator runs attempts inline in one process. E9 has no parallelism to gain and inline execution avoids inheriting the journal's locked file descriptor across a fork. The fork-safety property that motivated the study design is preserved anyway: **halt state and both attempt counts are re-read from the durable journal before every dispatch**, never cached in memory. Real-process behaviour is covered by four subprocess tests, including a hard-killed child.

---

## 2. Requirement-to-code traceability

### Fixed fixtures (76 recorded checks, `verify-fixtures`)

- 8 payload SHA-256 hashes and 8 byte lengths bound to the committed manifest.
- Both bodies of every fixture re-serialized and confirmed byte-identical to canonical JSON.
- Developer text and user text confirmed **identical between each count body and its generation body**.
- The count body confirmed to be the exact five-key projection of the generation body (`contract.verify_pair`).
- F2 and F3 confirmed **byte-identical** in both classes.
- The manifest's frozen profile fields confirmed equal to the reviewed contract constants; the manifest's prospective-state claims (`execution_authorized`, `protocol_adopted`, `count_fee_verified`, zero call counts) confirmed still false/zero.
- The builder hash and all five manifest source hashes verified against the checked-out repository.
- With a provider supplied, the provider's own pure `prepare` step confirmed to **reproduce all eight committed byte strings exactly**.

A single whitespace edit that still parses as JSON is rejected (`test_single_byte_edit_fails_the_hash_binding`).

### Separate allowances

Both caps are counted from `reserved` events in the durable journal, so they survive a reopen and cannot be reset by restarting. `test_twelve_count_attempts_are_the_total_allowance` drives 4 fixtures × 3 attempts and asserts the total stops at exactly 12 with zero generation attempts. E9 records carry `arm="E9"`, `block=0`; `test_run_never_labels_records_with_a_study_arm` asserts no study arm label ever appears, and no study slot is consumed.

### Deadlines and retries

The retry rule is delegated to the reviewed `contract.retry_decision` and every decision is journalled with its reason. Covered: a 97 s server minimum honoured **in full** where the fixed backoff was 5 s; a malformed `Retry-After` producing no retry; a 301 s directive exceeding the attempt cap; deadline exhaustion; and refusal when wait + 1 s margin does not fit the remaining deadline.

### Count failure and admission

A count failure forfeits only that fixture and **no generation is dispatched for it** — asserted directly against the journal's generation reservations. An over-limit count is recorded as a finding with no generation dispatch, and `L*` is asserted unchanged: the launcher records the finding, it does not retune the limit to fit an observation. A count of exactly 272,000 is admitted, and its reservation is asserted to be exactly `1.251840000000`.

### Acceptance

Each A1.11 pass condition is a named condition carrying the requirement text and the enforcing code. HTTP 200 is explicitly insufficient: the run must reach a profile-valid **completed** response on all four fixtures with usage equal to the count, all mandatory usage categories known, zero cache activity, identity recorded and F2/F3 identical, count(F3) = count(F2), and a logged §6.7 parse result. Conditions are evaluated from the **durable journal**, not from in-memory state — see defect 2.

### Live dispatch gate

18 requirements. With no evidence, 17 fail and only the installed-SDK check passes. Proposal-marked documents, synthetic authorities, expired price validity, a forged authorization amount, a mismatched evidence hash and unknown account terms each fail specifically. `test_a_complete_consistent_non_synthetic_evidence_set_passes` constructs a complete evidence set inside `tmp_path` and asserts the gate **can** pass, so the gate is demonstrably not vacuous; a companion test removes each element in turn and asserts the gate closes again.

The shipped `e9_unapproved_authority_template.json` is asserted to be inert: it cannot even be constructed into an `AuthorityRecord`.

---

## 3. Defects found and fixed

Three defects in my own code were found **by the tests, not by inspection**:

1. **Outcome labels were never overwritten.** The initial sentinel `"not_started"` is truthy, so `outcome.outcome = outcome.outcome or "count_failed"` silently kept the sentinel and every failure path reported the wrong outcome. Fixed by assigning unconditionally.
2. **Acceptance read findings from memory.** Findings were collected from in-memory outcomes, which are empty **precisely when an attempt halts** — so a cache-activity or profile-mismatch failure produced an acceptance record that did not name the failed condition. Rewritten to read findings and identity vectors from the journal, joining `completed` events back to their `reserved` events for the fixture name.
3. **The fabricated correction fixture was not faithful.** F4 exists to exercise a response with no valid vectors; the mock returned ten. Made body-aware.

---

## 4. Defect in a dependency, and the minimal patch

`contract._status_bucket` maps **every** HTTP 429 to `"retryable"`. Against documentation retrieved 2026-09-09 this is wrong for four documented codes — `organization_spend_limit_exceeded`, `project_spend_limit_exceeded`, `organization_usage_limit_exceeded`, `credit_balance_exhausted` — and for `error.type = insufficient_quota`. The error-codes guide states that retrying these will not restore access. On the baseline, such a rejection would be retried up to the attempt cap, each retry re-reserving money against a condition only the account owner can clear.

**Reproducing evidence:** `e9tests/test_spend_limit.py::test_defect_unpatched_contract_calls_a_billing_429_retryable` asserts the defective classification on the unpatched baseline for all four codes, across both request classes, including that `attempt_consequence` reports `retry_allowed: True`.

**The patch** (`patches/0001-spend-limit-not-retryable.diff`, 107 lines, applies cleanly via `git apply`) adds `SPEND_LIMIT_ERROR_CODES`, `SPEND_LIMIT_ERROR_TYPES` and `billing_rejection_code()`, gives `_status_bucket` an optional `payload` argument, and passes the parsed error body through from both classifiers. It buckets these rejections with the existing credential statuses — where 402 Payment Required already sits. Both provider methods parse the retained error body only when the status is 429; retention is unchanged.

**Effect on existing tests: none.** With the patch applied, the 113-test provider-candidate suite and the 152-test preserved reference suite both still pass at their full counts. Nothing was weakened, skipped or relaxed. A 429 with no billing code, or with no parseable body, remains retryable exactly as before.

**The launcher does not depend on the patch.** It classifies billing rejections itself, before consulting the provider's category, so the recorded stop reason and the `e9_spend_limit_rejection` event are identical whether or not the patch is applied. The launcher's suite passes against both the unpatched dependency (88 passed, 5 skipped) and the patched one (89 passed, 4 skipped) — the skips are the two mutually exclusive documentation tests, and the total is 93 either way.

Whether to adopt the patch is the reviewers' decision; it is supplied separately and is **not** applied to the repository.

---

## 5. Test evidence

Dependency baselines re-run at the pinned commit in the locked environment:

| Suite | Result |
|---|---|
| Core repository (`tests/`) | 289 passed |
| Provider candidate | 113 passed |
| Preserved reference | 152 passed |
| `qbridge_ext` | 53 passed |
| **Total** | **607 passed** — reproducing Codex's recorded figure exactly |

**An honest note on how that number was reached.** The core suite first produced **287 passed, 2 failed**. Both failures were in `tests/test_preflight.py`, and both were caused by `pip-audit` — a dev dependency pinned in `uv.lock` — being absent from my freshly created environment, so the preflight module's `importlib.metadata.version("pip-audit")` lookup raised. No test was modified. Installing the locked `pip-audit==2.10.1` (and aligning `pydantic` to the 2.12.0 recorded in the baseline's own environment log) produced 289/289. Every other pin already matched `uv.lock` exactly.

New launcher suite: **93 tests**, passing against both the unpatched and patched dependency. `ruff` clean under the repository's rule set.

Offline dry run (`e9_dry_run_report.json`): 76/76 fixture checks passed; gate correctly refused with 10 failures; 4 count and 4 generation attempts, no retries; ledger committed a **fabricated** $4.691732 of a fabricated $25 ceiling; 12/12 acceptance conditions passed; 72 journal events.

**That dry run is not evidence about the model, the provider, prices or cache behaviour.** It demonstrates only that the orchestration, accounting, gate and acceptance logic execute end to end. Every response in it was invented by `qbridge_e9.mocks`.

---

## 6. Deviations, limits and what is still missing

- **No live evidence of anything.** Wire-profile acceptance, the real token count, the real identity vector and cache behaviour are all unverified until E9 runs.
- **The count fee is unresolved**, so the gate cannot pass. This is the single largest blocker and it is not a software problem.
- **Account facts are unknown** — billing mode, tier, balance, configured limits, tax treatment. The gate treats "unknown" as a failure; none were invented.
- **The help-centre prepaid-billing article named in the work order was not retrievable** (403). Its contents are not asserted.
- **Byte length is not a token count.** These fixtures do not prove that every legal history fits the context or the admission limit.
- **Equality of count and usage at E9 is necessary, not sufficient** for the confirmatory claim.
- **The Responses route exposes no serving fingerprint**, so weight or serving changes that leave the echo unchanged remain undetectable. The identity vector is a weaker instrument than a fingerprint and is recorded as such.
- **No cache-window coverage is claimed.** F2/F3 timing is recorded; a zero-cache E9 pass demonstrates no cache lifetime.
- **The reservation under-reserves cache writes.** `reservation_for_generation` reserves input at the uncached rate; `charge_from_usage` bills written tokens at 1.25×. A cache write therefore produces a recorded overrun. E9 policy already fails on any cache activity, but the money is spent before the failure is detected — which is why the proposed ceiling is sized on the charge worst case, not the reservation worst case.
- **The launcher enforces limits conditional on the recorded prices and provider compliance. It does not enforce the invoice.**
