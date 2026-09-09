# Response to Codex's E9 review — revision 2, offline only

**Nothing was executed against a provider.** No count or generation request, no credit purchase, no billing change, no amendment adoption, no study-objective evaluation, no freeze, no study launch. Amendment A1 remains proposed; protocol v0.4 remains operative and unfrozen. The original submission is preserved unchanged; this is a new revision with its own manifest.

The four fixed fixtures, the model profile, the scientific scope and the existing attempt caps are unchanged.

## Verification points accepted

| Codex reported | Confirmed |
|---|---|
| Archive SHA-256 `f8f92489…a498`, external manifest `e63433ba…e5e4`, 51 entries verified | Yes. Recomputed from the saved revision-1 artifacts: archive `f8f92489281fab0a6040887057a909db1cc42a2caa49b85322be4b9a1880a498`, manifest `e63433ba7d59bc51a562d579c95945deae2fa01d909c1d5feb155bde4ff9e5e4`. Both match. |
| The embedded manifest differs from the external one on the archive self-hash only | Yes — that was the documented consequence of hashing the archive after writing the manifest into it. Revision 2 removes the ambiguity: the archive now carries `SHA256SUMS.inner.txt`, which contains no self-referential line, and the external `SHA256SUMS_rev2.txt` is the only place the archive digest appears. |
| The unpatched suite reproduces 88 passed / 5 skipped (93 collected) | Yes, that is revision 1's final state. My retained `e9_test_evidence.log` recorded the earlier 87/5 and 88/4 runs from before the last test was added — stale evidence for a package that had moved. All logs in this revision were regenerated from the shipped code in one pass. |
| "Report actual versions, not an exactly matching environment claim" | Revision 1's claim that the environment "matched Codex's recorded environment exactly" is **withdrawn.** Actual versions are recorded in the implementation report and the financial proposal; the known difference (Codex local 3.11.15 against this sandbox's 3.11.16) is named, and no comparison of other packages was made. |

## How each finding was reproduced and corrected

Every finding was **reproduced against the delivered package first**, using Codex's four probe scripts with only the hardcoded repository path changed. The consolidated script is `codex_findings_probe.py`; its output against the delivered package is `codex_findings_before_rev1.json` and against this revision `codex_findings_after_rev2.json`. Both were produced with `httpx.MockTransport` only.

---

### P1 · 1 — the 300 s attempt wall clock was not enforced

**Reproduced.** A 2 s deadline with a 2.25 s blocking generation returned after **2.523 s** and marked F1 `completed`, with `remaining_seconds` at −0.523. The per-phase timeout the SDK saw was 1.758 s on each of connect/read/write/pool — none of which bounds the total. (These are wall-clock measurements and vary by tens of milliseconds between runs; the saved values are in `codex_findings_before_rev1.json`.)

**Cause.** `orchestrator.py` called the provider synchronously and trusted `httpx.Timeout`, which is per-phase by construction.

**Correction.** New module `qbridge_e9/deadline.py` enforces the boundary at the only place bytes leave. The orchestrator arms a budget before every dispatch — `min(300 s, remaining deadline)` — and the wrapped transport runs the inner dispatch in a daemon worker thread. At expiry it (1) **cancels** by closing the inner transport, which aborts an in-flight socket read on a real `httpx.HTTPTransport`; (2) waits a fixed 0.25 s grace window; (3) **rejects any late result**, recording its status, byte length and SHA-256 without ever returning it to the SDK; and (4) raises `httpx.ReadTimeout`, which the reviewed provider classifies as an ordinary attempt timeout — the reservation is retained as unknown-dispatched and the predetermined retry rule applies.

**Journal-lock hazard avoided as instructed.** The worker is a *thread inside the owning process*, not a forked child, and it runs only the transport dispatch. All journalling stays on the single owning thread, so no worker ever inherits or holds the journal's writer lock, and a killed worker cannot tear the hash chain. That was the reason for choosing a thread at the transport boundary over `ProcessExecutor`.

**Honest limit, recorded in the module, the report and the tests:** a *synchronous in-process* handler cannot be preempted — CPython offers no safe way to interrupt arbitrary synchronous code in another thread. For `httpx.MockTransport` only steps 2–4 apply: the deadline is observed exactly and the late result is refused, but the worker thread runs to completion in the background. It is a daemon thread, so it never blocks interpreter exit, and `DeadlineGuard.workers_alive` reports any still running. Cancellation is real for a socket; for a mock it is recorded as `mock_transport_not_preemptible` rather than claimed.

**Now.** Same probe: **2.276 s**, outcome `generation_failed`, `e9_attempt_wall_clock` journalled with `late_results_rejected` and every entry `accepted: false`. The armed budget is `min(300 s, remaining deadline)`, so after the count attempt it is strictly less than the 2 s deadline — the tests assert that relation rather than a fixed number.

**Tests** (`test_deadline.py`, 10): stalled real transport cancelled and closed exactly once; late response rejected and recorded with a digest; in-budget response returned normally; workers are daemon threads and are reaped; dispatch without an armed budget raises `DeadlineNotArmed`; wrapping a mock preserves `RecordingTransport.inner_is_mock` so the synthetic/real boundary is untouched; a mock handler reports non-preemptibility; Codex's blocking-generation reproduction; the orchestrator refuses to run at all without a guard; and a fresh transport per attempt, so closing one is safe.

---

### P1 · 2 — reopening reset the deadline and forgot terminal stops

**Reproduced, both halves.** After a first run stopped with `deadline_exhausted`, a second orchestrator over the same journal reported `remaining_seconds: 7400.0` and dispatched F2–F4, taking attempts from (1,1) to (4,4). After a `project_spend_limit_exceeded` stop, a reopen dispatched three more pairs, taking attempts from (1,0) to (4,3).

**Correction — both mechanisms, not one.**

1. **Terminal state is persisted and honoured.** `terminal_records()` reads every `e9_stopped` and `provider_halted` event. A journal holding either refuses to continue: `e9_run_refused` is written, nothing is dispatched, and the unfinished fixtures report `refused`. The refusal quotes the launcher's own `e9_stopped` reason in preference to a provider halt, so the string does not depend on whether patch 0001 is applied.
2. **The governing deadline is durable.** Consumed time is recorded on every `e9_logical_finished` as well as on `e9_stopped`/`e9_run_finished`, tagged with a per-run index. `consumed_seconds()` takes the largest recorded value per run and sums across runs; `budget_seconds()` is the deadline minus that. A run whose budget is already spent is refused with `governing_deadline_already_consumed`. Recording consumption per fixture, not only per run, means a run **killed between fixtures** still contributes the time it used instead of handing a resumed run the whole budget again.
3. An unresolved prior reservation still refuses continuation, since such an attempt may already have been billed.

**Now.** Deadline probe: attempts stay at (1,1), stop reason `prior_terminal_stop:deadline_exhausted`, `second_remaining_seconds` 0.0. Billing probe: attempts stay at (1,0), stop reason `prior_terminal_stop:spend_limit_halt:project_spend_limit_exceeded`. Before the fix both probes reached (4,4) and (4,3) with the second run reporting the full 7,400 s.

**Tests** (`test_terminal_and_resume.py`, 7): both of Codex's reproductions; consumed time accumulating across runs; an unresolved reservation refusing; and a clean interruption between fixtures resuming correctly — reconstructing F1/F2 from the journal, sending only F3/F4, and subtracting the 1,000 s the killed run had already used.

---

### P1 · 3 — Git detection and the fabricated `public_repo` path

**Reproduced, both halves.** `git init` a directory, place the records store inside it: the gate reported `inside_git_worktree=False` and `may_dispatch_live: true`. And `RequestRecords(records, public_repo=<work>/public_repo_guard)` — the fabricated sibling path `cli.py` was passing — accepted a directory inside a real repository.

**Cause.** The check was `any(p.name == ".git" for p in path.parents)`, which looks for a parent *named* `.git` and therefore never matches a real repository. And the `public_repo` argument was a path that does not exist, making the store's own containment check vacuous.

**Correction.** `gate.git_worktree_root(path)` walks both the literal and the resolved path for a `.git` **directory or file** — linked worktrees and submodules use a file — and then asks `git rev-parse --show-toplevel`, which catches configurations the marker walk cannot see. The `records.private` requirement now fails if any worktree root is found *or* if the path resolves under the verified repository root. `cli.py` constructs `RequestRecords` with the **resolved `--repo-root`**, and `--repo-root` is now required on every subcommand. Additionally, `_setup` refuses **before creating anything** if `--work-dir` lies inside a worktree, in every mode, with no override flag.

**Now.** Gate probe: `may_dispatch_live: false`, `records.private` fails naming the worktree root. CLI probe: refused with "refusing to write E9 records inside a Git worktree rooted at …", and nothing is created.

**One thing deliberately not changed.** `RequestRecords` is a reviewed repository component. With a caller-supplied fabricated guard it still accepts a Git-contained directory — that is its documented contract, and the fix belongs in the caller. Probe case `F3c` shows that with the verified repository root it refuses (`request records must be outside the public repository`), and `F3d` shows the CLI refuses first. If you would rather the store itself detect worktrees, that is a change to a reviewed component and I would supply it as a third numbered patch rather than fold it in here.

**Tests** (in `test_gate.py`): a real `git init` repository; a linked-worktree `.git` **file**; a symlink pointing into a repository; containment under the verified repo root without Git; a genuinely-outside private directory passing; and a real-subprocess test that the CLI refuses a work directory inside a worktree and creates nothing.

---

### P1 · 4 — fixtures trusted the caller-supplied manifest

**Reproduced, both halves.** Changing the committed F1 prompt and updating its declared digests passed **all 76 checks** with the mutated text loaded. An empty `source_sha256` mapping was accepted with zero failures.

**Correction.** The reviewed digests are now **pinned as module constants** in `qbridge_e9/fixtures.py`, taken from the pinned commit: `REVIEWED_MANIFEST_SHA256`, `REVIEWED_BUILDER_SHA256`, the eight `REVIEWED_PAYLOAD_SHA256` entries with byte lengths, and the five `REVIEWED_SOURCE_SHA256` paths. The manifest is checked against the pin, so it can only confirm what was reviewed. The payloads are checked **directly against the pin**, not via the manifest, so defeating one check does not defeat the other. The declared source set must equal the pinned set exactly — empty and partial both fail. `repo_root` is a **required** argument: there is no executable path that skips source verification, and `verify-fixtures` requires it too. An unreviewed extra payload file in the directory also fails.

**Now.** Both probes refuse with `FixtureError: pinned reviewed manifest digest: manifest.json sha256=3e987b73… equals the pinned f6c1cafc…` (the mutated digest is reported alongside the pin, so the refusal names what differed). Checks on the genuine fixtures rose from 76 to **96** with a provider bound (88 without), across 19 named requirement families.

**Tests** (`test_fixtures_identity.py`, 25): Codex's self-consistent replacement; the payload pin holding even when the manifest pin is defeated (by re-pinning the constant in a monkeypatch, which isolates the second line of defence instead of letting the first mask it); empty and partial source sets; a required and a wrong `repo_root`; an extra unreviewed payload; single-byte whitespace edits; and the profile/prospective-state checks retained behind the pin.

---

### P1 · 5 — under-reservation before dispatch

**Reproduced.** `reservation_for_generation(272000, rates)` = **1.251840 USD**; `charge_from_usage` for the same request with cache writes = **1.523840 USD**; shortfall **0.272000 USD** per attempt.

**Correction, in two independent places.**

1. **The launcher, patch-independently.** New `qbridge_e9/money.py` computes the conservative figure — input at the highest rate any input token can attract (`max(input, cached_input, cache_write)` = the cache-write rate) plus the full output cap. The gate gained requirement `authority.conservative_ceiling`: the authority's ceiling must cover that figure for **every** attempt the caps allow (12 × 1.523840 + 12 × 1.088000 = **31.342080**). The orchestrator requires conservative headroom **before every generation dispatch** and refuses with `insufficient_conservative_headroom`, recording the required and available amounts, rather than discovering the overrun at settlement.
2. **The dependency, as a separate numbered patch.** `patches/0002-conservative-generation-reservation.diff` makes `reservation_for_generation` reserve at the worst applicable category. It is supplied and **not applied**; it stacks cleanly on 0001; and the reviewed suites are unchanged by it — **113/113 provider and 152/152 reference with 0001+0002 applied**. No preserved reference bytes were modified and no test was weakened.

**Tests** (`test_money.py`, 11): the worst-case rate is the cache-write rate; the conservative reservation equals the worst-case charge exactly (1.523840); the conservative E9 ceiling is 31.342080 and exceeds 25; non-token inputs rejected; the orchestrator blocking a dispatch when headroom is one micro-dollar short — which holds whether or not 0002 is applied; and a mutually exclusive skip-guarded pair asserting the unpatched (1.251840, under-reserved) and patched (1.523840, exact) behaviour, so exactly one runs and neither is vacuous.

---

### P2 · 6 — the approval time was only truthiness-checked

**Reproduced.** `approved_at_utc: "invalid UTC, not an instant"` left `may_dispatch_live: true` with `authorization.explicit_e9` passing.

**Correction.** New requirement `authorization.bound_and_timed`. `approved_at_utc` must parse as a UTC instant and must not be in the future; `expires_at_utc`, when present, must be later than the dispatch instant; and the record must carry `authority_sha256` equal to the digest of the authority record being used — so an approval is **bound to one authority**, not reusable against a different ceiling or profile. Adoption records get the same treatment for `adopted_at_utc`. The requirement's own detail states that a parsed digest and timestamp are not evidence that a person approved a charge.

**Now.** `may_dispatch_live: false`, `failed_keys: ["authorization.bound_and_timed"]`. The gate is now **20 requirements**; with no evidence at all, 19 fail and only `environment.sdk_versions` passes, and the offline dry run fails 11 of 20.

**Tests** (in `test_gate.py`): six malformed instants; a future approval; an expired approval; an approval bound to a different authority digest; an unbound approval; and a future adoption date.

---

### P2 · 7 — a rerun flipped acceptance and overwrote the report

**Reproduced.** A rerun of a completed journal dispatched nothing yet reported `e9_accepted: false`, failing `fixtures.all_four_completed` and not-demonstrating `a1.timing.f2_f3_recorded`, and wrote over `e9_report.json`. Also confirmed: `report.py` hardcoded `amendment_a1_adopted: false`, `live_spending_authority_issued: false` and `storage.outside_git: true`.

**Correction.**

- **Reconstruction.** A fixture already finished in the journal has its outcome rebuilt from the durable events — count receipt, admission, parse result, usage, identity vector, attempt counts, and the dispatch instant now recorded on the reservation so the F2→F3 gap survives. The rebuilt outcomes are marked `reconstructed: true`.
- **Reports are per-run.** `write_report` writes `e9_report_<UTC>[_NNN].json` with `open(..., "x")` so it can never overwrite, and appends a line to `e9_reports.jsonl`.
- **Authorization fields are derived, not asserted.** `amendment_a1_adoption_evidence` comes from the gate's `adoption.record` status; `spending_authority_issued_by_this_run` is `false` as a structural invariant (the launcher consumes an authority and never creates one) and is now named that way instead of conflating issuing with consuming; `spending_authority_consumed` is derived from mode and gate; call counts come from the journal's transport reservations, with the transport class recorded and `experimental_generation_calls` zero only because the transport is a mock. `storage.outside_git` is now **measured** by `git_worktree_root`, and the worktree root is reported.

**Now.** Rerun probe: `second_accepted: true`, no failed keys, no not-demonstrated keys, identical F2→F3 gap, and a new report filename.

**Tests:** rerun preserving acceptance; reconstruction recovering counts, admission and parse results field by field; a real-subprocess rerun producing a second report with both files intact and two index lines; and the derived report fields asserted individually.

---

### P2 · 8 — the dry run read `OPENAI_API_KEY`; `main([])` crashed

**Reproduced.** One `os.environ.get("OPENAI_API_KEY")` during a dry run, and `cli.main([])` raising `AttributeError: 'Namespace' object has no attribute 'work_dir'`.

**Correction.** `evaluate_gate` now takes `env` as a **required explicit** argument and raises if it is missing, so no gate call can silently reach the process environment; `os` is no longer imported by `gate.py` at all. The dry-run path passes `{}`. The `gate` subcommand reads credential *presence* only under an explicit `--check-credential` flag, off by default. A bare invocation prints usage and returns **2** with "a subcommand is required (verify-fixtures | gate | dry-run | live). There is no implicit default" — the implicit dry-run default is gone, since falling through into an execution mode with unset arguments was the defect.

**Now.** `api_key_get_calls: 0`; bare invocation returns 2 cleanly.

**Tests:** a bare invocation exits 2 with no `AttributeError` and no stdout; a dry run with a populated `OPENAI_API_KEY` in the child environment still fails `credential.present` and the value appears nowhere in the report; and `--check-credential` changes only that one requirement, with the value never printed.

---

### 9 — billing corrections

All nine points are carried into `e9_financial_proposal_rev2_2026-09-09.md` and `e9_billing_source_register_rev2_2026-09-09.json`:

- **Retracted by name:** "$32 covers every case", "the smallest round ceiling that cannot be reached", and "the evidence supports $32". The evidence supports four scenarios and no selection among them.
- **The count figure is an assumption, not a bound.** There is no established maximum for a count attempt. Recorded explicitly: **L\* = 272,000 is checked *after* a count returns, so it cannot bound the billable size of a count request that is itself rejected as too large.**
- **A successful count+generation would establish the charges for those two calls only** — not a fee schedule, not the treatment of failed or rejected calls, not the study's arithmetic.
- **$25 and $32 are both retained as UNAPPROVED scenario figures.** No probe is proposed or authorized, and the proposal recommends no figure, because selecting one requires resolving the count-charging question.
- **Cent ceilings corrected as directed:** conditional D = 31.342080 → **31.35**. Study: **5708.40 / 6948.72 / 10669.68 / 11910.00**.
- **Project hard limits are monthly and cover all traffic in the project.** The gate now requires `existing_month_to_date_spend_usd` and `concurrent_project_traffic` to be recorded before a live run.
- **The prepaid article could not be read, and this is the one instruction I did not satisfy.** A web search confirmed the article exists at the URL the work order names, with the title "Setting up and managing prepaid API billing" and a page age of 30 July 2026 — but the search returned result metadata only, no page text, and direct fetch is still refused with HTTP 403 (refusal page retained). Per the instruction's second branch, the precise reason it remains unavailable is recorded: **automated fetch is blocked by the host, and no tool available to me returned its contents.**
- **A self-correction, recorded because it matters more than the finding it fixes.** This revision's first draft recorded nine specific prepaid-billing facts against that article — credit expiry after one year, non-refundability, free credits consumed first, a non-instantaneous stop leaving a negative balance carried to the next purchase, an auto-recharge feature with an inconsistent documented default. **None of those statements came from a retrieved source; they came from my own recollection and were written as if sourced.** An independent verification pass caught it. All nine were removed from the register, the proposal and this document before any of them was saved. The register carries a `correction_note` describing the error, and prepaid mechanics are now listed as unresolved.
- **The question "when does money leave my account" is therefore recorded as unanswered**, not answered. What survives is what the hashed sources say: prepaid credits exist for an organization, `credit_balance_exhausted` means that balance is depleted, and hard spend-limit enforcement is not instantaneous. Whether an amount of credit functions as a cap is unknown, because the depletion and replenishment behaviour is unknown.
- **Provenance is graded, and the grading is now enforced by having no ungraded claims.** Eight sources are hashed local copies a future reader can verify. The ninth is `search_result_metadata_only`: it establishes that a page exists and nothing whatsoever about its contents.
- **No account fact or fee term is asserted.** All remain listed as unresolved, and the one place where facts had been invented is retracted above.

---

## Residual limits, stated rather than closed

1. A synchronous in-process mock handler is not preemptible; only its result is refused (finding 1).
2. `CANCEL_GRACE_SECONDS = 0.25`, so a run can exceed its deadline by that bounded amount plus process overhead before stopping. In the saved probe the overshoot was 0.276 s against a 2 s deadline.
3. `RequestRecords` itself still accepts a Git-contained directory when handed a fabricated guard; the caller was fixed instead (finding 3).
4. Patches 0001 and 0002 are supplied and **not applied**. The launcher behaves identically either way by design, and the suite is run against all three dependency states.
5. The count-charging question is unresolved and no software change can resolve it.
6. A hash match shows a retained file is the recorded one. It is not verification of an account's charges, and not verification that a person approved anything.
7. The prepaid-billing article's contents were never retrieved. Nothing in this package rests on them, and the nine facts a first draft attributed to them are withdrawn (finding 9).
