# Independent integration review follow-up

This record covers offline review after commit `1129a6037a20e1935a34cc210e61431eb3b5f99b`. It does not adopt amendment A1, run E9 or freeze a study. Chris requested that the remaining updates, including the plain-language README, be consolidated into one final commit and push. Earlier published commits remain unchanged.

## Counted runner: confirmed and corrected

A received accounting-halt result is allowed to preserve its current proposals while stopping further model requests. The implementation applied that exception before resolving all durable worker halts. Two fabricated real-worker regressions demonstrated that a returned accounting-only result could cause the runner to accept text even after a stricter compatibility or inferential failure was saved.

The corrected runner selects an inferential failure first, then another non-accounting halt, then an accounting halt. It preserves newly discovered stricter failures for later blocks. The current-text exception is allowed only when the selected durable halt itself is accounting-only. Three regression cases were added: two worker cases and propagation into the next block. The counted-runner suite passes 18 tests.

The [broader verification](post-review-verification.json) passes 488 tests (283 core, 53 earlier Chat-candidate, 152 counted-reference). It predates integration of the new single-attempt Responses provider; that package needs its own verification. The original 485-test record remains a historical milestone.

## Process executor: confirmed local cleanup defect

The provider's strict abrupt-exit test failed in both Claude Science and the independent local environment: cleanup signalled an unreaped worker group, and macOS returned EPERM, masking WorkerCrashed as provider_client_error. This was not a Claude-only permission limitation. The first independent provider run passed 112 tests and failed this one test; its financial and transport reservations remained preserved.

The core now reaps an already-exited worker before group cleanup. A new descendant regression also established that a forked descendant can hold both completion pipes open after the worker exits. A direct local diagnostic observed worker exitcode 1 while its sentinel was still unready and the descendant remained in the worker's group. The executor therefore checks the actual worker exit status in bounded waits and still signals the process group to cancel descendants. Eight focused crash/cancellation checks and the unchanged five provider fork/crash tests passed after this correction. Three additional regressions require non-finite worker timeouts to be rejected before a process starts. Final combined results and the exact published core hashes are recorded in [integrated verification](integrated-verification.json).

## Fixed prospective E9 inputs

The [input bundle](e9-inputs/README.md) contains four fabricated fixtures and eight canonical count/generation bodies. It uses the preserved earlier fixture generator and reviewed counted reference. The count and generation requests preserve identical input strings; F2 and F3 are byte-identical in each request class. All eight hashes were read back. A formatting-only builder change left all payload bytes unchanged.

The fixture bundle makes the inputs reviewable before model observations. It is not an execution entry point, an observed token count, a context-fit guarantee or a spending authority.

## Provider review in Claude Science

The new project conversation is [Single-attempt Responses Provider Implementation](http://localhost:8765/projects/proj_993c3d0d7ed9/frames/bbd403c9-9e28-4efd-8513-54cf83e57833). Its source starting point is the immutable commit above. The work order specifies one request per attempt, durable outgoing and response records, separate monetary reservations, complete authority checks, strict usage/identity handling and fabricated-only verification.

Codex's early review identified the following issues for correction and independent retesting in the candidate package:

- An unreconciled usage total must not make the recorded commitment smaller than a computable category-based charge above the original reservation.
- Authority time checks must reject non-finite or premature instants and expire both price and count-fee evidence. Count evidence needs a hash, validity and explicit failed/rejected-attempt coverage. The dispatch boundary must recheck authority and durable halt/ledger state.
- Identity tags represented as tuples become lists after JSON storage. A direct fabricated round-trip reproduced 13 false identity-change findings. Comparisons need a validated JSON-stable representation, tested across workers and reopen.
- Monetary rendering must be independent of the ambient Decimal exponent and trap settings. A fabricated `$123` rendering raised Overflow under a restricted ambient context; Decimal coefficient length also bypassed the intended rational bound. Both cases were sent for correction and regression tests.
- A count receipt must match the specific reserved and completed count attempt, its body, logical context and recorded count. A standalone receipt plus an unrelated successful count event is insufficient.
- E9 provisional observations must remain distinct from an accepted baseline; study requests must require the accepted, validated E9 baseline.

The [final provider package](provider-candidate/) includes corrections and regression tests for these findings. The [import receipt](provider-import-verification.json) verifies 23 declared files plus the manifest, and all 14 source-input hashes against immutable commit `1129a6037a20e1935a34cc210e61431eb3b5f99b`. Original author bytes and historical failure logs are preserved. Two Python files differ from the independent review snapshot only in explanatory docstrings; their logic and assertions are unchanged. The [integrated verification](integrated-verification.json) records results on the imported package with the corrected core.

The original 152 reference tests are preserved and pass against their original module. When redirected to the operational contract, two old assertions expect tuple identity tags; the new JSON-stable list representation intentionally fails those assertions (150 pass, 2 fail). The operational provider tests cover the replacement representation. Those two compatibility differences are disclosed separately and are not counted as passing tests or added to the combined total.

All records retain zero experimental count calls, zero experimental generation calls and zero study-objective candidate evaluations. The package validates the structure of authority evidence; it cannot establish the truth of external billing attestations. The bounded E9 entry point, accepted E9 identity baseline, complete study launcher and freeze remain outstanding.

## Public explanation

The README now explains the classical software / simulated-qubit feedback loop, the fixed comparison and success criterion, and who can use this repository. Its commercial framing is conditional: a positive result would motivate harder tasks and later hardware research. Hardware savings, scaling and commercial value require separate evidence.
