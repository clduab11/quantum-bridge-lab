# Current E9, budget and readiness audit

Date: 2026-09-08. Author: Codex audit subagent `preflight_budget_gates`.
Scope: read-only offline review of protocol v0.4, current readiness/provider decisions, budget/runner/custody/journal/proposal code and stored verification. No provider research duplicated; no provider or token-count endpoint, objective, secret, install or repository edit was used. The only new file is this temporary report. Current 27 source hashes still match `research/provider/verification.json`; this is a fresh hash check, not a re-run of its 233 tests.

## Authority and practical conclusion

Chris now explicitly says: “Go ahead and perform all three steps in the Claude Science project.” This advances authority beyond the historical offline-only phase. Record that actual instruction and perform the dependent work; do not quote stale historical phase limitations as if they veto the new instruction. The request does not manufacture an observed fingerprint, measured E9, a numerical spending ceiling, a completed manifest, or evidence of independent custody. Under v0.4 §13.1–13.2, freeze and evaluation are distinct recorded decisions referencing the completed immutable manifest; those records can truthfully be authored by the agent exercising actual delegated authority. A fictitious human signature and a fresh generic permission round are unnecessary.

The next executable work is to produce a pinned candidate contract, fixed synthetic E9 package, adapter/accounting implementation with mocks, actual storage/role setup and the complete conditional budget. Paid action still requires the actual token/billing contract and a concrete monetary ceiling/authority record under G-COST. Do not begin a study-objective evaluation merely to estimate runtime before freeze.

## Exact protocol arithmetic

Let `L` be the verified maximum input tokens per attempt; let `p` and `q` be conservative combined USD-per-million input and inclusive-output rates, and let `R` cover any additionally applicable priced costs. All categories and price validity must be resolved by the provider-contract work. Set `c = (L*p + 8192*q)/1,000,000` dollars per fully reserved attempt.

| Quantity | Derivation | Fixed result |
|---|---|---:|
| Stages and blocks | 2 × 20 | 40 blocks |
| Allotted objective slots | 40 × 3 arms × 200 | 24,000 |
| Scheduled study requests | 40 × 19 | 760 |
| Maximum study logical calls | 760 × 2 (initial + correction) | 1,520 |
| Maximum study transport attempts | 1,520 × 3 | 4,560 |
| Output tokens, scheduled ceiling | 760 × 8192 | 6,225,920 |
| Output tokens, logical-call tier | 1,520 × 8192 | 12,451,840 |
| Output tokens, all-attempt ceiling | 4,560 × 8192 | 37,355,520 |
| Per LLM arm/block total tokens | 114 × (L + 8192) | 114L + 933,888 |
| Both stages total tokens | 4,560 × (L + 8192) | 4,560L + 37,355,520 |

Scheduled study cost is `760c`; full correction/retry study reserve is `4560c`. This is a conditional ceiling, not an expected bill. Every dispatched or unresolved reserved attempt consumes an allowance; unknown usage stays unknown and must retain its maximum monetary reservation rather than becoming zero. Timeout/cancellation cannot undo provider work or known/unknown charges.

**E9 has no prescribed numeric call limit in the protocol.** Section 11 requires the number and content to be logged; the separately fixed E9 plan supplies its cap. It is incorrect to infer 4, 12, 24 or any other E9 count directly from v0.4. The plan below proposes 4 logical requests with at most 3 attempts each: 12 E9 attempts. With this explicit plan:

- E9 reserve: `12c`; E9 token ceiling: `12L + 98,304`.
- Scheduled study plus worst-case E9: `772c + R`; input/output ceilings `772L` and `6,324,224`.
- Entire two-stage maximum plus E9: `4572c + R`; input/output ceilings `4572L` and `37,453,824`.
- Round combined money **up** to cents, as `qbridge.budget` already does. Supply `max_e9_attempts=12`; do not multiply that input by retries again.
- If the eventual E9 design instead gives four full proposal batches their own automatic malformed-output correction, its cap becomes 4 × 2 × 3 = 24 attempts. It must not advertise the 12-attempt plan while silently running that larger state machine.

At most 35,150 seconds of HTTP timeout/backoff allowance exists per LLM arm/block: `114*300 + 38*(5+20)`. The independent total arm deadline is 36,000 seconds. Forty LLM arms can consume 400 arm-hours; all 120 sequential arm deadlines sum to 1,200 hours (50 days), before any scheduling/cleanup overruns. These are conservative limits, not latency forecasts. Both stages should use the shortest feasible window, with the frozen price-validity rule enforced. For the proposed four-logical-call E9, transport time/backoff alone is `12*300 + 4*25 = 3700 seconds` (61 minutes 40 seconds), so a claimed universal one-hour E9 wall bound would be false. A separately chosen overall E9 deadline may end it earlier without replacement.

## Smallest useful fixed E9 package

Preselect exactly one candidate provider/model/endpoint and one complete request configuration before examining its outputs. E9 is transport/schema/identity evidence, never a miniature optimization study or performance-driven model/prompt selection.

1. **F1:** legal fabricated 10-row history, `batch=1`, unique indexes 1–10, valid disk coordinates and scores in [0,1], remaining-after 180; unchanged literal prompts.
2. **F2:** legal fabricated long-spelling 190-row history, `batch=19`, unique indexes 1–190, scores in [0,1] and disk-valid coordinates; remaining-after 0. The existing negative minimum-normal coordinate fixture is legal. Fabricated scores are not outputs from any physical objective.
3. **F3:** exact byte-repeat of F2 as a separate stateless request, to inspect response identity/usage stability. Equal metadata across two responses is limited evidence, not a stationarity proof.
4. **F4:** F2 plus exactly the frozen correction suffix, e.g. `\nPREVIOUS RESPONSE REJECTED: invalid_envelope. Respond again following the output rules exactly.` This is an explicitly declared synthetic correction-interface fixture, not a claim that a real F2/F3 response actually failed. No response body is included in the correction reason.

These are **four independently specified logical interface fixtures**, not four whole `ArmRunner.run_llm` batches. Use transport retries only for connection failure, timeout, 429 or 5xx, at most three attempts with 5/20-second backoffs. A 2xx malformed response is parsed, recorded and finishes that fixture; it does not introduce an unbudgeted correction beyond the fixed F4. An invalid request/unsupported configuration or materially missing identity contract should stop remaining preflight work for diagnosis, preserving evidence and consumed attempts. Do not adapt settings to obtain a favorable E9 result. Any necessary prospective config change needs a new explicit version/allowance rather than an unlogged free retry.

The request fixture manifest should hold complete serialized payloads/hashes, exact system/user prompt hashes, fabricated-input provenance, correction code, request fields, expected API/usage categories, metadata checks, cap calculation and stopping conditions. A fresh E9 namespace in the durable journal must reserve before every dispatch. Preserve HTTP/request IDs, raw body/headers after credential filtering, finish/refusal state, actual identity/decoding metadata, usage categories and missingness, parser results, attempt times and errors. Never pass a returned vector into the study objective. Do not reuse `ArmRunner` initialization for E9 because it invokes the supplied objective; use a dedicated objective-free interface path or extracted bounded transport helper.

The current renderer accepts at most 190 rows. The protocol's 200-row worst-case boundary can be supported by the separate grammar/tokenizer derivation or an explicitly marked boundary-only rendering utility, without changing scheduled batch numbering or claiming `render_user(..., 20)` is valid. The long legal example is not itself proof of the universal token maximum.

## Can a context cap replace tokenizer proof?

Not under the present evidence and literal v0.4. A model context size `C` may support an extremely loose **conditional monetary reservation** for successfully accepted requests if the provider contract establishes how all billable input/context/output tokens are bounded. Even `L=C` does not prove that the longest permissible prompt plus 8192 output fits; `L=C-8192-margin` is an admission threshold, not proof that a given request is below it. Failed over-context request billing and hidden/server wrapper behavior cannot simply be assumed absent.

Section 7.2 specifically requires a verified tokenizer-derived input ceiling and requires an over-ceiling request to be rejected **before dispatch**. The runner implements that contract through `count_input_tokens` and `input_token_limit`. A constant function that returns the advertised context maximum would fabricate counting, even if used as an accounting reserve. Setting the cap high also does not satisfy G-MODEL's worst-case 200-row fit-with-margin requirement.

There are legitimate routes: a correct endpoint/model tokenizer plus proved wrapper bound; a documented exact count of that same request format available before dispatch, with bounded count-call resources if applicable; or an explicit prospectively reviewed amendment to an equivalent enforceable admission/accounting contract. The existing 108,835 text-byte bound can combine with a proven byte-tokenizer property and wrapper bound, but bytes alone and four measured fixtures cannot do so. Responses counts cannot be silently rebranded Chat counts. Do not introduce truncation of history or a smaller input-admission cap that forfeits otherwise permissible histories as an invisible design change.

## Gate-by-gate remaining work

| Gate | Can be completed without live experimental calls? | Exact work remaining |
|---|---|---|
| G-ENV | Yes, except newly added provider dependencies must then be pinned/checked | Capture the actual study Python/executable/platform and complete `pip freeze`/lock metadata. Match relevant documentation or installed-release source/signatures for NumPy/SciPy/pycma behavior. Existing release capture is partial evidence; do not use mutable main docs as exact-release proof. |
| G-CMA | Yes | Bind the demonstrated pycma 4.4.4 options and ask/tell-after-stop test evidence to the final manifest. Record deterministic seed manifests for all blocks 0–39, not only the existing block-0 options fixture; seeds can be generated without evaluating candidates. |
| G-MODEL | Documentation/serialization/token proof partly offline; actual response identity requires E9 | Resolve one complete supported profile, exact role mapping/settings, stable metadata/fingerprint and output limit; prove input accounting/fit. E9 must actually capture accepted request and identity metadata. Optional/missing fingerprint remains an actual evidence issue, not a fixed impossibility proof. |
| G-TRANSPORT | Adapter/mocks/admission/accounting offline; real acceptance/usage E9 | Build explicit provider adapter with hidden SDK retries disabled and fixed transport rules. Flatten/capture nested usage without omitting categories or double-counting inclusive reasoning. Validate real timeout, rejection, error and usage behavior with available bounded E9 evidence, supplemented by mocks. Shared study journal must preserve identity tracking across all arms/blocks. |
| G-CUSTODY | Yes under current delegated operational authority | Actually name Codex/operator, the locked analyst process, and the real owner/operator of automated custody. Implement selected option (b) and record its limitation. Create mapping via the protected process without printing or consulting mapping contents. No independent custodian or new human-role approval is required by option (b). |
| G-LOCK | Yes | Finalize/hash all analysis dependencies and exact invocation in the complete manifest, retain E8 evidence. Implement coordinator export of endpoints/curves that drops prohibited identity-bearing fields. Commit sealed output hash before calling pair selection. |
| G-EXPOSURE | Yes before E9, then append actual E9 and later events | Reconcile exposure events across Codex, Claude Science and all participating workflows, including any currently running Claude work, rather than trusting this repository alone. Record synthetic check inputs and every pre-freeze model call. Preserve zero pre-freeze study-objective evaluations if true. |
| G-STORAGE | Yes | Establish actual owner-only 0700 directories and 0600 files outside public Git for mapping/seed, journals, raw transcripts and local configuration. Public record names storage classes/commitments without leaking private absolute paths. Verify owner/permission/symlink constraints and process access; these do not create agent independence. |
| G-RUNTIME | Yes for deadline engineering; E9 supplies limited latency evidence | Implement/test full scheduled coordinator, enforceable process deadlines and nonselective crash recovery. Actual study-objective runtime need not be measured before readiness: §12 expressly leaves it unmeasured until authorized evaluation. Do not invent a requirement to benchmark the objective before freeze. |
| G-COST | Arithmetic/control implementation offline; actual billing evidence and spending decision still needed | Establish `L`, inclusive 8192, every applicable billing category/rate/region/window and separately capped E9 plus both-stage maximum. Record the actual monetary ceiling and authority. Reserve full per-attempt money before dispatch; unknown usage retains its reservation; missing provider usage is not zero. A calculator output alone neither enforces a live ceiling nor proves an invoice contract. |

## Missing execution engineering, beyond documenting gates

The repository has numerical components, parser/rendering, per-arm runner, durable journal, seed helpers and locked analysis/custody. It still lacks the full 25-node study objective assembly, provider adapter, endpoint token admission implementation, monetary reservation enforcement, full two-stage launcher/coordinator, masked export/full-run manifest builder, and recorded freeze/evaluation decisions. Do not mistake 233 component tests for a runnable frozen study.

The study objective assembly may be implemented and reviewed offline, with aggregation/composition exercised through stubs/component identities. Do not call the full study objective on zero/random/known-good vectors as a pre-freeze sanity check. The coordinator can be fully exercised with injected fabricated objectives/transports: blocks 0–39, fixed RS → CMA → AI order, both stages always scheduled, shared initialization evaluated separately by each arm, no replay/replacements, and no outcome-dependent continuation. After recovery, failed arms remain failed and later scheduled arms may proceed under the fixed contract. Freeze checks must fail closed on unresolved fields or source/hash changes.

Recommended immediate split: provider agent resolves current direct API/token/rate contract; implementation agent prepares objective-free E9 payload/adapter/accounting mocks; root/Claude records current authority, actual custody/storage and final manifest inputs. Once these tangible prerequisites exist, the remaining dollar decision (if not covered by an existing numeric authorization) can be presented concretely. No generic new approval should be requested instead of completing this authorized preparation.
