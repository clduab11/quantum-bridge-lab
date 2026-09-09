# E9 launcher review: corrections required

Reviewed 2026-09-08 America/Chicago / 2026-09-09 UTC. This is an offline engineering review of Claude Opus 5's first E9 launcher submission. **The submission is not ready for a paid preflight.** Its passing tests miss defects in deadline enforcement, reopening, storage protection, fixture identity and monetary reservations.

The original implementation is retained under [submission](submission/) for review. It is not installed in the operational provider, adopted into the protocol or an approved launch path. Claude Science has received an offline correction request covering the findings below. A revised package will need independent review.

Protocol v0.4 remains unchanged and unfrozen. A1 and candidate v0.5 remain proposed. No live count or generation request, study-objective evaluation, credit purchase or billing-setting change occurred in this review. Neither $25 nor $32 is approved spending authority.

## What was checked

Source conversation: **E9 Model-Preflight Launcher Implementation**, Claude Science project `proj_993c3d0d7ed9`, frame `3028e4de-1ac6-4a2a-98cd-a7bea009f3ad`, model shown as Opus 5. The implementation uses engineering baseline `a8c3e1e83c28db80642ab0123dd1fbf4d9ff5bc2`; its work order came from documentation commit `1db79978cbeaa0fb40728f6cc986d1d106621995`.

Codex checked the completed conversation through Edge browser automation, inspected the files, verified their hashes, ran the supplied tests independently and added separate offline counterexamples. Three delegated reviews covered orchestration, gates/storage and billing. Their findings were reconciled with the source and retained reproductions.

The archive's 110 members were checked for absolute paths, traversal, links and unexpected member types before extraction. All **51 external manifest entries matched**: 38 content entries found in the extracted package, the archive itself, and 12 unmodified repository dependencies checked separately. The dependencies are not included in the archive.

| Item | SHA-256 |
| --- | --- |
| Original archive | `f8f92489281fab0a6040887057a909db1cc42a2caa49b85322be4b9a1880a498` |
| External manifest | `e63433ba7d59bc51a562d579c95945deae2fa01d909c1d5feb155bde4ff9e5e4` |
| Reviewed fixture manifest | `f6c1cafce927cde8617b72dd2b404b698a891b2f907b20520d58ff72def9bf63` |

The embedded manifest has a stale archive self-hash; that one line differs from the external manifest. It is not evidence of changed source bytes. Both manifests are retained. Selected author source, tests, patch and documents are preserved byte-for-byte; AppleDouble metadata, full third-party billing pages and unrelated artifacts are omitted. The [import verification](import-verification.json) identifies the retained files and every checked entry. Hash agreement establishes integrity, not correctness or billing authority.

## Independent test results

| Configuration | Result |
| --- | --- |
| Original launcher and unchanged provider | **88 passed, 5 skipped**, 93 collected, 8.69 s |
| Launcher plus supplied billing-429 patch, and existing provider suite | **202 passed, 4 skipped**, 206 collected, 27.36 s |

The second result comprises 89 passing launcher cases and 113 passing provider cases. The patch was applied only to a temporary copy. The skips select mutually exclusive patched/unpatched cases; they are not unexplained omissions. Child CLI tests still locate the unchanged baseline provider through the supplied test layout, so this is not a claim that every subprocess path used the patch.

See the [unpatched log](evidence/independent-unpatched-tests.log), [patched log](evidence/independent-patched-tests.log) and [actual environment](evidence/environment.json). The independent runtime used Python 3.11.15 and Pydantic 2.13.5; Claude recorded Python 3.11.16 and Pydantic 2.12.0. Both used OpenAI SDK 3.9.0 and HTTPX 0.28.1. No dependencies were installed or changed for this review.

Claude's final claim of 93 launcher cases is reproduced. Its retained `e9_test_evidence.log` instead records earlier 92-case runs (87/5 and 88/4); that evidence is stale and must be refreshed in the revision. The prior [607-test integration result](../VERIFICATION.md) remains historical evidence, not a newly rerun total. Do not add overlapping provider runs to it as unique tests.

Passing the supplied suite does not resolve the findings below. The [separate probes](probes/) exercise cases absent from that suite. Their successful execution demonstrates counterexamples to the claimed protections, not passing protections. All request traffic in these probes uses fabricated responses and MockTransport.

## Required corrections

### R1 — Enforce cancellation and reject late results (P1)

[`orchestrator.py:449`](submission/qbridge_e9/orchestrator.py#L449) invokes the synchronous provider directly. An HTTPX phase timeout does not enforce an overall wall-clock attempt limit. The retained probe with a two-second run deadline and a generation handler sleeping 2.25 seconds returned after 2.49 seconds and marked F1 completed. The submitted real-process tests do not exercise a stalled transport.

Use an enforceable worker deadline and cleanup, preserving durable retention and journal ownership. Reject results arriving after the governing deadline. Retain the 300-second attempt and 7,400-second overall limits. Local cancellation cannot reverse a request already accepted remotely; unknown charges must retain their reservations.

### R2 — Preserve terminal stops and the deadline across reopen (P1)

[`orchestrator.py:209`](submission/qbridge_e9/orchestrator.py#L209) starts a new timer and does not restore `e9_stopped`. After F1 exhausted the 7,400-second limit, reopening the same journal dispatched F2–F4 and reported 7,400 seconds remaining. With the delivered unpatched provider, a billing 429 stopped at one count and zero generations; reopening then dispatched three additional pairs.

Persist the governing run state or refuse continuation after interruption or a terminal stop. Reopening must not grant more time or bypass a billing halt. Keep cumulative attempt and monetary reservations intact.

### R3 — Reject records inside actual Git worktrees (P1)

[`gate.py:424`](submission/qbridge_e9/gate.py#L424) looks for an ancestor named `.git`, missing ordinary worktree directories. [`cli.py:176`](submission/qbridge_e9/cli.py#L176) supplies a fabricated `public_repo_guard` path to `RequestRecords`. A newly initialized temporary Git repository containing `out/raw` with mode 0700 passed the gate and record-writer construction.

Check resolved worktree ancestors, including `.git` files and symlinked paths, and pass the verified repository root to the record writer. Private file permissions do not prevent accidental Git publication.

### R4 — Anchor fixtures to the reviewed manifest (P1)

[`fixtures.py:173`](submission/qbridge_e9/fixtures.py#L173) trusts the supplied manifest's own declarations. A modified F1 prompt with updated payload/text hashes passed all 76 checks, including the real provider's `prepare` and unchanged builder/source hashes. Removing all `source_sha256` entries also passed.

Independently pin the reviewed manifest digest and require the complete source set and source verification on executable paths. A self-consistent replacement manifest must fail before dispatch. Do not regenerate fixtures or change scientific inputs to repair this check.

### R5 — Reserve for every applicable charged category (P1)

The provider's reservation is $1.251840 for 272,000 ordinary input tokens and 8,192 output tokens. At the documented cache-write rate, the same token totals can cost $1.523840. The submission acknowledges the difference but does not fix admission.

Reserve using the highest applicable category rate before dispatch, with a separate versioned provider patch and regression evidence. Cache activity must still fail E9. A later halt or a larger aggregate budget does not repair an inadequate reservation for a charge already incurred.

### R6 — Validate approval timestamps and binding (P2)

[`gate.py:369`](submission/qbridge_e9/gate.py#L369) accepts any truthy approval timestamp. The string `invalid UTC, not an instant` passed a fabricated otherwise-complete gate. Strictly parse UTC times, check their relationship to dispatch and validity windows, and bind approval evidence to the reviewed authority/run. The positive gate fixture is fabricated; it does not verify an account, provider terms or user approval.

### R7 — Preserve reports and describe authority accurately (P2)

Reopening a completed run dispatches nothing, but [`acceptance.py:140`](submission/qbridge_e9/acceptance.py#L140) evaluates `skipped` outcomes without reconstructing completed outcomes and timing. Acceptance changes from true to false, and [`report.py:159`](submission/qbridge_e9/report.py#L159) overwrites the previous report. Preserve the result or reconstruct it faithfully.

[`report.py:88`](submission/qbridge_e9/report.py#L88) also hardcodes amendment adoption and issued live authority as false, including a future live run whose gate requires them. Distinguish consuming existing authority from issuing it, and derive status from retained evidence.

### R8 — Make offline invocation match its claims (P2)

The dry-run calls the gate without `env={}`, causing a read of `OPENAI_API_KEY`. An environment spy containing only a fabricated value reproduced one read; no real secret was exposed. Supply an empty environment for offline gate checks.

`main([])` chooses dry-run but lacks its argument fields and raises `AttributeError` for `work_dir`. Provide a usable offline default or a clean documented usage error.

### R9 — Correct the financial conclusion and evidence (P1)

The proposed $32 is a conditional illustration, not a verified bound. Its $1.088 per-count assumption has no established maximum covering success, failure, rejection and timeout. The 272,000-token admission limit is applied after counting, so it cannot by itself bound charges for a rejected count request. One successful count and generation can reveal charges for those observed calls, subject to billing detail and delay; they cannot establish general failed-request terms.

Under the stated assumptions, conditional scenario D is **$31.34208**, rounded upward to **$31.35**. The four study scenario ceilings, rounded upward to cents, are **$5,708.40 / $6,948.72 / $10,669.68 / $11,910.00**. They remain conditional maxima, not expected bills. Existing and concurrent usage also matters: the provider project limit is monthly and covers all project traffic, whereas the proposed launcher authority is per run.

Current primary documentation supports the $4 ordinary-input, $0.40 cached-input, $5 cache-write and $20 output prices per million tokens at short context, and distinguishes billing/quota 429s from throughput limits. The supplied billing-429 patch addresses a real classification issue, but remains unadopted alongside the submission. Sources: [Sol model pricing](https://developers.openai.com/api/docs/models/gpt-5.6-sol), [spend limits](https://developers.openai.com/api/docs/guides/spend-limits), [error codes](https://developers.openai.com/api/docs/guides/error-codes), checked 2026-09-09 UTC.

The [prepaid billing article](https://help.openai.com/en/articles/8264644-how-can-i-set-up-prepaid-billing) is now accessible through web tooling; Claude's retained 403 is a retrieval failure, not billing evidence. It describes a $5 minimum purchase, automatic reload enabled by default at setup, one-year credit expiry, nonrefundable purchases and possible cutoff delay. No actual account configuration was inspected. The [cost brief](../COST_BRIEF.md) separates credit purchases, usage charges and development expenses.

## Next decision

Claude Science was asked to return a separate corrected package, fresh logs, regression results, explicit provider patches, accurate financial wording and a response to each finding. It was instructed to stop after offline work and keep live gates closed. Project Context was not changed.

After the corrected code passes independent review, missing billing terms and a numeric E9-only authority can be considered. Scientific adoption, live E9, full-manifest freeze and study execution remain separate decisions. This review supports continuing a bounded engineering effort; it supplies no evidence of an advantage over CMA-ES or of commercial performance.
