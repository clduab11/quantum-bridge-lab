# Independent review of E9 launcher revision 2

Reviewed 2026-09-09 by Codex Astra with separate deadline, gate and financial reviewers. **Revision 2 is not ready for live E9.** Several earlier defects are fixed, but independent counterexamples still violate the attempt deadline, overall deadline and approval expiry. A gate-only command also reports readiness without verifying its input paths.

Chris delegated budget approval during this review. Codex approved a **US$32 all-in incremental allocation for one E9** in the [budget decision](../E9_BUDGET_DECISION.md). Billing resolution and live spending release remain pending. There were no experimental count/generation calls, study-objective evaluations, purchases or billing changes. No amendment, launcher or provider patch was adopted.

## Submission and provenance

The source is Claude Science's revision 2 package from **E9 Model-Preflight Launcher Implementation**, based on engineering commit `a8c3e1e83c28db80642ab0123dd1fbf4d9ff5bc2`. Review began with repository head `b04f8b438ec544264245de06709a735adf15f88f`. The [original submission](submission/) is preserved separately from this review; its claims are not automatically accepted.

- Archive SHA-256: `b77b85133dc922706861df07349f1bd8f07ae06ab2660d85562a436deedccdf2`.
- External manifest SHA-256: `40d35f762fe1abb8f559cc7dd2d6e98d5f74fc93cb597fc70c94a80cef364373`.
- Inner manifest SHA-256: `968b700c1564a80595a65093adff91a173154e60cfdceb9eb5d21636e74ae36c`.

All 78 external and 64 inner manifest entries matched after safe extraction. Twelve external entries refer to unchanged repository inputs. The [import receipt](import-verification.json) records every comparison and all 33 selected files retained here. Full third-party articles, AppleDouble metadata and redundant author outputs are omitted. Their original manifest entries remain as provenance; this directory is a selected preservation set, not a complete archive mirror.

## Independent verification

| Configuration | Result | Evidence |
| --- | --- | --- |
| Revision 2 with unchanged provider | 144 passed, 6 skipped; 150 collected; 13.27 seconds | [Log](evidence/independent-unpatched-tests.log) |
| Revision 2 with patches 0001 and 0002 in a temporary provider copy, plus provider tests | 258 passed, 5 skipped; 263 collected; 74.32 seconds | [Log](evidence/independent-patched-tests.log) |
| Independent deadline and gate probes | Remaining defects reproduced with fabricated responses | [Programs and exact evidence](probes/README.md) |
| Independent monetary checks | 48 arithmetic checks passed; direct-orchestrator retry limitation reproduced | [Programs and evidence](financial-probes/README.md) |

The second pytest result contains 145 launcher tests and 113 provider tests. The author CLI subprocess tests construct their own import path pointing to the neighboring unchanged repository, so the result does not show that every subprocess used both patches. Skips distinguish intentionally incompatible patched/unpatched configurations; the logs name each one.

The review runtime was Python 3.11.15, OpenAI SDK 3.9.0, HTTPX 0.28.1, Pydantic 2.13.5, NumPy 2.4.6, SciPy 1.17.1, CMA 4.4.4, pytest 9.1.1 and Ruff 0.16.6 on macOS 26.5.2 arm64. The author used Python 3.11.16 and Pydantic 2.12.0; these environments are not identical. No packages were added to the project lockfile. The historical 607-test integrated result was not rerun or enlarged by adding these overlapping suites.

## Remaining findings

### P1: the response body remains outside the attempt deadline

In [deadline.py](submission/qbridge_e9/deadline.py), the thread guard ends when the inner transport returns a response. The provider subsequently reads the body in its existing `transport.py`, outside that guard. A delayed synthetic response body completed after **2.51449 seconds** with a two-second limit, produced a completed F1 outcome and recorded no wall-clock expiry. The late-response retention path also reads synchronously.

The repair must bound the complete attempt, including body consumption, retention and cleanup, with the existing cancellable process executor. A transport-header timeout alone is insufficient. Local cancellation still cannot undo provider work already accepted remotely.

### P1: a partial resume excludes time spent stopped

[orchestrator.py](submission/qbridge_e9/orchestrator.py) reconstructs consumed active duration and grants the remaining duration from a new clock start. An intact prefix through F2 consumed 100 seconds. Resuming at monotonic time 10,000, beyond the original 7,400-second deadline, granted another 7,300 seconds, sent two count/generation pairs and accepted E9. The F2/F3 gap was 9,950 seconds.

Persist and enforce the original deadline with valid clock-continuity evidence, or refuse an unfinished continuation when continuity cannot be established. The repaired explicit terminal-stop and completed-run replay cases do not cover this partial-prefix case.

### P1: approval expiry is checked only at startup

[gate.py](submission/qbridge_e9/gate.py) validates initial approval expiry, but [cli.py](submission/qbridge_e9/cli.py) does not carry that expiry into later dispatch checks. In a fabricated live-path test, the approval expired one second after startup and the clock advanced two seconds after the first count. Seven subsequent fabricated dispatches proceeded and E9 was accepted.

Approval expiry must be checked before every count, generation and retry, including after waits or reopen. Price validity is a different check and cannot substitute for it. The probe replaced the HTTP transport factory and blocked external socket access; it made no provider request.

### P2: gate-only mode certifies nonexistent inputs

The `gate` command returned exit 0, 20/20 checks and `may_dispatch_live: true` with nonexistent fixture and repository paths, given otherwise complete fabricated evidence. The actual live branch separately verifies fixtures, so this is a false readiness certificate rather than a demonstrated live fixture bypass. Gate-only mode must perform the same input and source verification before reporting readiness.

### Required reservation correction and financial wording

The new `money.py` and provider patch 0002 correctly reserve the maximum applicable input-category rate. However, the launcher's independent headroom check runs once before the generation retry loop. Patch 0002 therefore cannot remain optional unless an equivalent conservative check occurs before every attempt.

A direct synthetic orchestrator probe, deliberately bypassing the CLI's full-allowance gate, committed $2.775680 against a $2.603680 ceiling with the unchanged provider. With patch 0002 it dispatched one generation and retained $1.523840. **The full CLI rejects that artificial low allowance before dispatch**; this is not evidence that the fully patched launcher overspends that ceiling.

The author's $31.342080 example rounds upward to **$31.35**, not $32. It still assumes an unverified count fee. Also, the new full-allowance gate rejects an insufficient $25 scenario before dispatch; it does not knowingly start and stop partway through that scenario. These wording corrections are requested in revision 3.

## Corrections confirmed

Independent probes confirm normal Git/worktree/symlink containment refusal, independently pinned fixture and source hashes, parsed and bound initial approval evidence, zero credential reads in dry-run mode, clean exit 2 without a subcommand, restored terminal stops, completed-result reconstruction and exclusive report creation without overwrite. The fixture verifier performs 88 checks without a provider. Author metadata now distinguishes fabricated authority from actual authority.

The author retracted previously unsourced prepaid-billing claims rather than treating an inaccessible page as evidence. This review subsequently read the official prepaid page; the [budget decision](../E9_BUDGET_DECISION.md) cites the public terms while keeping account facts unverified.

## Follow-up

Codex sent a focused offline revision 3 request in the same Claude Science conversation on 2026-09-09. Claude reproduced the remaining counterexamples and began repairs. Earlier packages, fixed fixtures and scientific decisions are to remain preserved. Revision 3 requires its own independent review before any claim of readiness.

The $32 allocation is approved under the user's delegation. Account billing, the maximum count-attempt fee and mandatory charges remain unresolved. The OpenAI API tab is signed out; account access has been requested. Existing Claude Science compute can support engineering, but no evidence establishes that it pays for the selected OpenAI API route.

Protocol v0.4 remains unchanged and unfrozen. Its SHA-256 is `0df9242fd2d0ad5d30b75ea91f498842ac68fe0df9616afd4c9c04518233eda5`. A1, candidate v0.5 and all launcher/provider changes remain unadopted. The full study has no spending authority or complete launch command.
