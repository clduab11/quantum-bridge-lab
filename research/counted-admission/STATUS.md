# Counted-admission implementation and protocol review

Status: offline engineering and prospective amendment review. Protocol v0.4 remains operative and unfrozen. Zero experimental generation calls, zero provider token-count calls, zero study-objective candidate evaluations and zero real comparison mappings have been created. No spending is authorized by this record.

The next design counts the exact Responses input before generation. Codex selected a prospective limit of 272,000 tokens before any count observation, following Claude Science's documented price-boundary rationale. This reduces size rejection relative to the initial 200,000 proposal, but changes the admitted method and its resource allowance; neither limit proves every legal history fits. The proposal replaces the unavailable serving fingerprint with validated observable response metadata and explicitly retains undetectable drift as a limitation.

## Completed and independently checked

- [Separate budget arithmetic](BUDGET.md): 13 new tests plus 59 existing budget tests passed. Up to 4,560 count and 4,560 generation attempts across both stages, plus 12 of each for E9. Unknown counting fees leave the combined total null; supplied fees are conditional assumptions, not verified billing or authority.
- [Durable request records](../../src/qbridge/request_records.py): 19 tests passed, including short writes, file/directory sync failures and a writer killed after successful retention. Files are created exclusively with private permissions outside Git and are never overwritten after failure. A future adapter must call this before dispatch; the component alone does not establish that integration.
- [Counted runner](../../src/qbridge/counted_runner.py): 15 tests passed. Count and generation retries have distinct reservations and limits inside one arm deadline. Admission rejection or count failure sends no generation. Only received zero-valid text can open one correction, with a new count receipt. Server minimum waits are never shortened. A real sequential worker test verifies that a persisted halt overrides apparent success before parsing. Interrupted arms cannot replay.
- [Claude Science reference and amendment](claude-science/): 152 reference tests passed independently. All 13 hashes and byte sizes in the source manifest were verified. The three amendment-build outputs reconstructed byte-identically; the physical task, estimand, classical methods, custody design and governance sections are unchanged. The complete third-party Cookbook article is not republished; its URL and checksum are retained.

The combined suite passes **485 tests**: 280 core tests including the three additions, 53 earlier Chat-candidate tests and 152 counted-reference tests. See [combined verification](combined-verification.json) and its [test log](combined-tests.log). The sole warning is that optional CMA plotting is unavailable; plotting is not required. Earlier receipts retain their historical test counts and scope.

## Decisions reconciled with Claude Science

The [proposed amendment](claude-science/amendment_A1_counted_responses_admission_PROPOSED_2026-09-08.md) and [applied candidate v0.5](claude-science/ai_quantum_control_protocol_v0.5_CANDIDATE_A1_2026-09-08.md) are review artifacts, not adoption or freeze records. The [review](claude-science/counted_responses_amendment_review_2026-09-08.md) retains disagreements and withdrawn claims. Important corrections include:

- Count receipts identify the requested payload, not an independently observed served model. Required response settings must match the expected profile before a baseline is accepted; whole-object metadata and presence changes are retained.
- The two retry classes can exceed the arm deadline in nominal maximum-duration arithmetic. The 36,000-second arm and 7,400-second E9 limits are stopping rules; overhead and longer server waits consume them. Retry dispatch requires the full server minimum wait and a fixed one-second margin.
- Compatibility, credential and identity/IVF halts forfeit the current proposal and prevent later provider calls. An accounting halt on already-received completed/incomplete text preserves its valid proposals while suppressing corrections and later calls. Raw evidence is retained in either case.
- Mandatory usage includes consistent input, output and total counts, plus cached and cache-write categories. Inconsistent or missing accounting cannot become zero; known category-based amounts and overruns remain visible. Counting fees cannot be established by four observations or delayed daily aggregate costs.

## Remaining work and gates

1. Finish the single-attempt Responses provider and integrate durable raw records, separate monetary reservations, price validity, observed identity and the counted runner. The imported reference functions do not constitute that adapter. The earlier Chat coordinator also remains a component: its event names do not directly compose with ArmRunner's lifecycle.
2. Review and record the prospective amendment before E9. Complete the four fixed synthetic Responses fixtures and their bounded execution entry point. No prompt, effort or admission-limit choice may be tuned from E9 observations.
3. Obtain configured API access and account/provider evidence covering counting and failed requests, plus applicable model prices. Record an actual numeric E9 authority before any live request. A separate financial-risk exception has not been proposed or adopted. Account limits are operational context, not a substitute for client controls.
4. After live E9 and all remaining readiness checks, record a complete immutable manifest and actual freeze decision. Both study stages and locked analysis follow only then.

Protected owner-only storage and automated custody roles already exist, as recorded in [operational setup](../execution-preparation/operational-setup.json). No independent evaluator blinding is claimed. Project Context was not rewritten during this review.

The project remains worth a bounded research effort. There is still no evidence that the language-model arm outperforms CMA-ES, saves hardware trials or supports a commercial claim. A funding decision depends on the value of this narrow question and verified total costs, not on agreement between assistants.
