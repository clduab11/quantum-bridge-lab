# Amendment A1, revision 2 (PROPOSED, NOT ADOPTED) — counted Responses admission and observable-identity standard

| Field | Value |
|---|---|
| Date drafted | 2026-09-08 (rev 1); revised the same day after Codex technical review (rev 2) |
| Author/agent | Claude Science; Codex review incorporated; both positions retained where they differ (§ "Positions") |
| Old revision | `specification/ai_quantum_control_protocol_v0.4.md`, 52,526 B, SHA-256 `0df9242fd2d0ad5d30b75ea91f498842ac68fe0df9616afd4c9c04518233eda5` (unfrozen, unchanged) |
| Candidate new revision | `ai_quantum_control_protocol_v0.5_CANDIDATE_A1_2026-09-08.md`, 70211 B, SHA-256 `1f1db589681d688bd2ee517386636765bdf87bb266d54bf5caaf605c41af4001` — produced mechanically by applying every old→new block below to the v0.4 bytes (each old block asserted to occur exactly once); unified diff `v0.4_to_v0.5_CANDIDATE_A1.diff`, SHA-256 `9ba14ee1d31057b3b018d8026f4afc311de81c71196c997eba6b8a8d1effcc8d`. **Candidate only; not the operative protocol; not to be placed at `specification/` until recorded in `AMENDMENTS.md`.** |
| Exposure status | **pre-exposure**: zero study-objective evaluations of any optimizer candidate, zero provider generation or count calls, zero real mappings (verification.json, operational-setup.json at commit `3d01292d…`) |
| Reason | v0.4 §6.1 requires a model fingerprint and §7.2/§12 a tokenizer-derived worst-case input ceiling; on the inspected Responses route for `gpt-5.6-sol` neither is available from the documentation retrieved 2026-09-08. This amendment replaces inference with enforcement (provider count + fixed admission limit) and the fingerprint with an observable-identity standard, stating both as reductions of the evidence standard. It does not claim these are the only possible routes. |
| Admission limit | **L\* = 272,000** provider-counted input tokens, selected prospectively by Codex on the documented price-tier-boundary rationale before any count observation. It is an admission choice, not a proof of universal fit and not spending authority. The rev-1 candidate value **200,000** is retained here as the superseded proposal (reason: a round budget-driven cut below the price boundary; superseded because it is anchored to no documented boundary and would increase design-induced admission forfeits). |
| What does NOT change | Claim under test (§0), scope (§1), simulator and noise model (§2), objective (§3), common contract (§4), CMA-ES and random search (§5), prompts (§6.2, §6.5–§6.7), slots/batches/blocks/seeds (§7.1 counts, §8.1–8.2), estimand, interval, margin, decision rules, stage structure, SVF/IVF logic (§9.1–9.5, §7.7), blinding and analysis lock (§10), governance (§13). No prompt tuning, no extra arm, no replay, no re-analysis. |
| Sequence on adoption | Codex technical review → record in `AMENDMENTS.md` with this file's hash → candidate file becomes the operative revision → separate **E9 gate** (monetary authority for both request classes; G-COST billing evidence) → E9 → closure of **all** §12 gates → freeze. Equality of count and usage at E9 is necessary, not sufficient. |

## Disposition of Codex's rev-1 review points (all incorporated unless marked)

| # | Codex point | Disposition in rev 2 |
|---|---|---|
| L\* | Select 272,000 prospectively; retain 200,000 as superseded; "nil scientific cost" too absolute; no monotonicity claim; remove "not large", condition 2q³ on iid | Adopted. §7.2 text now says the limit changes the admitted method and resource allocation and that over-limit depends on rendered text, not row count alone; review rev 2 removes the absolute wording |
| 1 | `Retry-After` is a minimum: never cap downward; retry only if wait ≤ 300 s and fits remaining deadline with dispatch margin; parse delta-seconds and HTTP-date against `Date`; define malformed/negative; `retry-after-ms` only with evidence; 70,300 and 7,400 are nominal fixed-backoff figures | Adopted (§7.2 bullet 4, §7.3, §11; reference `parse_retry_after`, `retry_decision` with tests) |
| 2 | Count object has no `model`; do not demand model from count responses; count identity = requested model + body hash + receipt | Adopted (§6.1 bullet 1, §7.1 count receipt) |
| 3 | Validate expected profile before accepting a baseline; required vs optional echo fields; absence/null semantics; check all 2xx objects (completed/incomplete/failed) for usage/metadata before retry or parse; record charges unclipped before halting; unknown mandatory usage cannot pass E9 or silently continue; no generation without count evidence/body validation | Adopted (§6.1 bullets 4, §7.3, §7.4 new rows `accounting_halt` distinct from IVF, §11; reference `validate_expected_profile`, `compare_identity`, `settle_response`, `may_dispatch_generation`) |
| 4 | Billing circularity; separate scenarios from dispatch authority; assumed count fee gives only a conditional total; before live dispatch require account/provider contract evidence covering failed count charges or an explicitly adopted bounded exception (not proposed); daily Costs data cannot prove a fee maximum; software enforces reservation limits conditional on pricing, not the invoice; account limits are operational context, not a block on writing the amendment | Adopted (§12 G-COST). Rev-1 wording "measured from E9" as the evidence route is withdrawn as circular; E9 cost reconciliation remains a *post hoc check*, not the evidence that licenses E9 |
| 5 | `store:false` ≠ zero server-side storage; remove exhaustiveness claims ("only", "unsatisfiable across all endpoints") | Adopted (§6.1 last bullet; §6.1 limitation wording restricted to the inspected route) |
| 6 | Exact verbatim old→new text; §7.2 replaced three bullets not two; no placeholders; adoption precedes E9 with a separate E9 gate; freeze follows all gates | Adopted: old blocks are extracted from the v0.4 bytes by script; §7.2 is replaced as a whole section (all six bullets reproduced); the applied candidate file and diff are supplied |
| 7 | Reference code: validate full canonical profile values, strict types, no aliasing, mutation tests, reject boolean admission limit, safe classification of None/unknown/malformed, duplicate-key rejection | Adopted (reference rev 2–4: 152 offline tests on fabricated values, Ruff clean) |
| R2 | Second Codex check: monetary arithmetic must be independent of ambient Decimal precision/traps (observed `Decimal('1.3')` at precision 2), Infinity rate accepted, `retry_decision` retried on NaN remaining time; validate rates/reservations/policy at every entry; reject non-finite remaining times and bool attempt numbers; reject present `background:true`, non-empty `tools`, `object != "response"` even on the first baseline; presence-tagged canonical values instead of the string `ABSENT`; compare whole frozen `reasoning`/`text`/`prompt_cache_options` objects; charge and preserve all received usage before classifying retry outcomes | Adopted (reference rev 3/4: exact `Fraction` money with bounded finite rate grammar and fresh-context rendering, `handle_generation_response` settles before classification, presence-tagged identity vector over whole frozen objects; 130 offline tests incl. ambient-precision-2 and NaN/Infinity cases). Amendment §6.1 (iv), §7.2 bullet 4, §7.3 and §12 G-COST wording updated |
| R3 | Codex review of the full candidate diff: history is at most 10·b valid rows; fix the retry dispatch margin to exactly 1 s and remove the duplicated 36,000 s sentence; reconcile anomaly/halt behaviour — malformed count/body/wire evidence ⇒ compatibility halt of all future LLM dispatch (not automatically IVF), ordinary count exhaustion/terminal HTTP ⇒ forfeit that batch only; `accounting_halt` on a received response parses/evaluates the received text, suppresses corrections/new calls, forfeits remaining slots, keeps unknowns reserved; IVF/identity/profile/credential/anomaly halts discard the current proposal from evaluation, retaining raw text for audit | Adopted verbatim as pre-exposure method selection (§7.2 bullets 4 and 6, §7.2a, §7.3, §7.4 rows, §9.6, §11); reference rev 4 adds `compatibility_halt` and `attempt_consequence` |
| R4 | Provider spending-controller source checks `total_tokens == input_tokens + output_tokens`; require a strict non-negative total, validate the equality, classify missing/inconsistent totals as `accounting_halt` with no zero substitution, preserve computable category charges and the raw report, do not present inconsistent usage as reconciled; reasoning tokens informational, never double counted | Adopted (§7.4 accounting row; contract Table C; reference rev 4 `usage_checks`/`settle_response.reconciled`, 152 tests) |
| + | Integration finding (`arm_started` vs `started`; `arm_closed` vs `arm_finished`); components are not a launcher; durable pre-dispatch retention of sent bytes; headers without authorization secrets | Recorded in §7.5 and in the contract; no integration is claimed |

## Positions retained (not merged into consensus)

- Codex: a higher L\* is not scientifically free — it changes the admitted method, resource allocation and potential deadline exposure while reducing size rejections. Claude Science (rev 1) had called the scientific cost "nil"; rev 2 withdraws that word and adopts Codex's formulation.
- Codex: over-limit occurrence is not proven to be late-batch-only or monotone in valid-row count; Claude Science's rev-1 statement is withdrawn.
- Claude Science: the price-tier boundary is the only documented input-token boundary below the rate-limit figures, which is why 272,000 is preferred over 200,000; Codex selected 272,000 on that rationale while stating it is a choice, not a proof.
- Both: count-class failures are LLM-arm-specific; enforcement is conditional on provider compliance; unknown fees cannot be bounded by an assumed reserve; retrieved documentation does not exhaust alternatives; no independent evaluator blinding exists or is claimed.

## Old → new blocks (mechanically applied; `L*` rendered as 272,000)

## A1.1 — Title

**old (verbatim from v0.4)**

```
# AI-Guided vs Conventional Parameter Discovery on a Simulated Single-Qubit Robust-Gate Objective — Protocol Draft v0.4
```

**new (complete replacement text)**

```
# AI-Guided vs Conventional Parameter Discovery on a Simulated Single-Qubit Robust-Gate Objective — Protocol Draft v0.5 (CANDIDATE — amendment A1 applied for review; NOT ADOPTED)
```

## A1.2 — Revision line

**old (verbatim from v0.4)**

```
Revision: protocol-v0.4 draft, 2026-09-08. Codex clarification revision of reviewed protocol-v0.3; all earlier artifacts remain unchanged. This revision incorporates independent statistical and operational review; it is not a run-manifest freeze. Supersedes the operative content of v0.1, Round 1, v0.2 and v0.3, all preserved unchanged as historical evidence. Evidence IDs refer to `research_evidence_brief_v2.md` (evidence-brief-v2). Governance terms refer to `protocol_governance_v2.md` (governance-v2).
```

**new (complete replacement text)**

```
Revision: protocol-v0.5 CANDIDATE, 2026-09-08. Applies proposed pre-exposure amendment A1 (counted Responses admission and observable-identity standard) to reviewed protocol-v0.4; all earlier artifacts remain unchanged. This candidate is under Codex review; it is neither adopted nor a run-manifest freeze. Supersedes nothing until recorded in `AMENDMENTS.md`. Evidence IDs refer to `research_evidence_brief_v2.md` (evidence-brief-v2). Governance terms refer to `protocol_governance_v2.md` (governance-v2).
```

## A1.3 — §6.1

**old (verbatim from v0.4)**

```
### 6.1 Model and decoding
- Exactly one model. Its identifier is **recorded from API response metadata at freeze and at every call**; no identifier is asserted in this document.
- Decoding parameters: before freeze select one supported explicit configuration and record the exact request parameters, provider/API version and model fingerprint. A documented fixed default may be used only when its versioned semantics are recorded. If effective decoding settings or stable model identity cannot be established, G-MODEL remains open; no confirmatory run is licensed by substituting an unknown value. No numeric provider default is invented here.
- `max_tokens` (output): declared design value **8192** (a cap, not a guarantee that every permissible output fits; tokenizer/provider-limit compatibility is checked with synthetic boundary fixtures at readiness).
- No tools, no system-side code execution, no multi-turn memory, no retrieval augmentation.
```

**new (complete replacement text)**

```
### 6.1 Model and decoding
- Exactly one model, addressed by one exact model string (never a routing alias). For generation, the model identifier is **recorded from the `model` field of every generation response**; no identifier is asserted in this document. The count endpoint returns only `object` and `input_tokens`, so a count receipt carries the *requested* model string and the count-body hash, not a served-model identity.
- Endpoints: `POST /v1/responses` for generation, preceded for every distinct logical-call body by `POST /v1/responses/input_tokens` (§7.2a). Chat Completions is not used under this revision.
- Request profile (frozen; its SHA-256 enters the manifest). Explicitly sent: `reasoning.effort` (one documented Sol value, design candidate `medium`), `text.verbosity: "medium"` (documented default, sent explicitly), `truncation: "disabled"` (documented default; marked deprecated in the reference — a later rejection is a contract failure, not a field to drop), `max_output_tokens: 8192`, `store: false`, `stream: false`, `service_tier: "default"`, `prompt_cache_options: {"mode": "explicit"}` with no breakpoints (documented as not using prompt caching). Never sent: `temperature`, `top_p`, `tools`, `tool_choice`, `parallel_tool_calls`, `instructions`, `personality`, `previous_response_id`, `conversation`, `context_management`, `include`, `metadata`, `user`, `safety_identifier`, `prompt_cache_key`, `prompt_cache_retention`, `background`, `reasoning.mode`, `reasoning.context`, `reasoning.summary`. Developer and user texts are plain-string `input` items (roles `developer`, `user`).
- **Observable-identity standard (replaces the fingerprint requirement for this revision).** The evaluated method is defined as the archived exact request profile plus the observable generation-response metadata. (i) *Required echo fields* must be present and equal the frozen profile with strict types on every received response: `object == "response"`, `model`, `service_tier`, `truncation`, `max_output_tokens` (integer), `store` (boolean), `reasoning.effort`, `text.verbosity`, `prompt_cache_options.mode`. (ii) *Optional fields with a safe set*: `background` must be absent or `false`; `tools` must be absent or `[]`; any other value fails the profile even on the first response — optional does not mean that a conflicting value is acceptable. (iii) *Optional free fields* `temperature` and `top_p` are recorded verbatim. (iv) The identity vector records every field as a presence-tagged canonical value (absent, or present with its canonical JSON), and records the **whole** `reasoning`, `text` and `prompt_cache_options` objects canonically, so that a nested field appearing, changing or disappearing cannot escape the drift check. A missing, unequal or unsafe required value before the baseline exists is an unverified-compatibility failure (E9 fails; no baseline is recorded); the baseline is the identity vector of the first profile-valid `completed` E9 generation response and enters the manifest; on every later response any difference in any identity key is IVF (§7.4). **Limitations stated as part of any confirmatory claim:** the inspected Responses reference exposes no serving fingerprint and the model page lists a single undated snapshot, so weight or serving changes that leave the echo unchanged are undetectable; effective sampling values are unobserved when echoed as `null`; reproducibility is transcript-level (exact bytes sent and received are archived), not re-executable. Other endpoints or providers are not characterised by this statement.
- `max_output_tokens` 8192 is a cap inclusive of reasoning tokens (documented), not a guarantee that every permissible output fits; a response with `status: "incomplete"` is a received response (§7.4).
- No tools, no system-side code execution, no multi-turn memory, no retrieval augmentation, no conversation linkage. `store: false` is sent; this is not a claim of zero server-side storage or retention (provider data-control terms govern; disclosed limitation).
```

## A1.4 — §7.1 additions

**old (verbatim from v0.4)**

```
- **Transport attempt:** one HTTP request made in service of a logical call.
```

**new (complete replacement text)**

```
- **Transport attempt:** one HTTP request made in service of a logical call.
- **Count request:** one HTTP request to `POST /v1/responses/input_tokens` carrying the exact projection (§7.2a) of a logical-call body. A count request is a transport attempt of the **count class**; a generation request is a transport attempt of the **generation class**. Attempt caps, backoff, timeout, reservation and logging apply to each class separately.
- **Count receipt:** the provider's `input_tokens` integer for one count body, bound to that body's SHA-256, the requested model string, the response headers and the receipt time. Valid only for byte-identical generation attempts of the same logical call; never reused across logical calls, corrections, batches or blocks.
- **Admission:** the predetermined decision `counted input_tokens ≤ L*`. Rejection forfeits the batch (§7.4) and dispatches no generation request. Admission never truncates or edits the prompt.
```

## A1.5 — §7.2 + new §7.2a

**old (verbatim from v0.4)**

```
### 7.2 Per-block caps (LLM arm)
- Logical calls ≤ 2 per batch (1 proposal + ≤ 1 correction) → **≤ 38 per block**.
- Transport attempts ≤ 3 per logical call → **≤ 114 per block**.
- Per-attempt timeout: declared design value **300 s** (verified at readiness).
- Backoff between attempts of the same logical call: 5 s, then 20 s (fixed).
- Output tokens ≤ 8192 per attempt (§6.1). Input length is bounded by construction (≤200 mapped-history rows plus fixed template and bounded correction reason). Freeze a verified tokenizer-derived input-token ceiling L_in and a total-token ceiling 114×(L_in+8192), with context/reserved-reasoning-token requirements included. A request exceeding its ceiling is not sent and follows the failed-call forfeit path. Record provider-reported token categories separately; unavailable billing quantities remain unknown. G-MODEL blocks freeze until these ceilings are concrete.
- HTTP timeout/backoff allowance alone is at most 114×300 + 38×25 = 35,150 s; it is not a bound on total runtime. Enforce an independent monotonic **36,000 s (10 h) deadline per arm per block**, including initialization, local computation, waits and calls. At expiry stop new work, cancel in-flight work, keep completed valid evaluations, and forfeit remaining slots without replacement. A timed-out objective invocation is simulator-invalid/SVF because a valid result was not obtained. Apply the same deadline to CMA-ES and random search. Record actual elapsed time and scheduling/cleanup overruns. Process execution must support enforceable timeouts before readiness can close.
```

**new (complete replacement text)**

```
### 7.2 Per-block caps (LLM arm)
- Logical calls ≤ 2 per batch (1 proposal + ≤ 1 correction) → **≤ 38 per block**.
- Count-class attempts ≤ 3 per logical call → **≤ 114 per block**; generation-class attempts ≤ 3 per admitted logical call → **≤ 114 per block**. Study maxima over 40 blocks: ≤ 4,560 count and ≤ 4,560 generation attempts. These are caps, not expected counts; completion of all of them within the arm deadline is not promised.
- Per-attempt timeout (either class): declared design value **300 s** (verified at readiness).
- Backoff between attempts of the same logical call and class: nominal 5 s after attempt 1, 20 s after attempt 2. If the provider returns `Retry-After` (a documented minimum wait), the wait is max(nominal backoff, server minimum) and is **never shortened**; the retry is made only if that wait is ≤ 300 s and wait plus a fixed dispatch margin of exactly 1 s fits the remaining arm deadline, otherwise the logical call ends without retry and the batch is forfeited with reason recorded. `Retry-After` delta-seconds are parsed as non-negative integers; HTTP-dates are measured against the response `Date` header when present, else against receipt time; a malformed value means no retry; a date in the past means the minimum is already satisfied; `retry-after-ms` is recorded but not interpreted (no documentation evidence); a retry is never made when the remaining deadline is unknown or non-finite.
- Output tokens ≤ 8192 per generation attempt (§6.1). **Input admission is enforced, not inferred:** every distinct logical-call body is counted by the provider before generation and a generation request is dispatched only if `input_tokens ≤ L*`, with **L\* = 272,000 provider-counted input tokens** (prospective admission choice anchored to the documented price-tier boundary "prompts with >272K input tokens", read conservatively as 272,000; it is not a proof that every legal history fits and not spending authority; the earlier candidate value 200,000 is recorded as superseded in the amendment file). The visible history is at most 10·b valid rows at batch b ≤ 19 under §6.3 (forfeits and invalid evaluations reduce it; never more than 190 rows because batch 19's results are not fed back), but no row count, byte count or tokenizer estimate is used for any bound; whether and when a body exceeds L\* depends on the rendered text, not only on row count, and no monotonicity in batch index is claimed. An over-limit body is a forfeited batch under §7.4. The per-attempt token ceiling is L\* + 8,192; the a priori study ceiling is 4,560 × (L\* + 8,192) generation tokens plus ≤ 4,560 count requests whose billing is unknown until account evidence exists. Provider-reported token categories are recorded separately; unavailable billing quantities remain unknown, never zero.
- Nominal fixed-backoff HTTP allowance (no server-imposed waits): 2 × (114×300 + 38×25) = 70,300 s per block, which already exceeds the arm deadline; with `Retry-After` waits it is not an upper bound at all, and it is not a bound on total runtime. The independent monotonic **36,000 s (10 h) deadline per arm per block** is the binding bound and is unchanged; enforce it, including initialization, local computation, waits and calls. At expiry stop new work, cancel in-flight work, keep completed valid evaluations, and forfeit remaining slots without replacement. A timed-out objective invocation is simulator-invalid/SVF because a valid result was not obtained. Apply the same deadline to CMA-ES and random search. Record actual elapsed time and scheduling/cleanup overruns. Process execution must support enforceable timeouts before readiness can close.

### 7.2a Count-to-send identity
Let `G` be the generation body. The count body `C` is the exact projection `C = {k: G[k] for k in G if k ∈ COUNT_SCHEMA}`, where `COUNT_SCHEMA` is the parameter set of `POST /v1/responses/input_tokens` in the pinned SDK (openai-python 3.9.0: `conversation, input, instructions, model, parallel_tool_calls, personality, previous_response_id, reasoning, text, tool_choice, tools, truncation`). Before projection the full profile of `G` is validated value by value (exact model string, exactly two plain-string `input` items with roles `developer` then `user`, `reasoning` exactly `{"effort": <fixed>}`, `text` exactly `{"verbosity": "medium"}`, `truncation` `"disabled"`, `max_output_tokens` the integer 8192, `store` and `stream` the boolean `false`, `service_tier` `"default"`, `prompt_cache_options` exactly `{"mode": "explicit"}`, no other key). `C` must then be exactly `{model, input, reasoning, text, truncation}` and `G \ C` exactly `{max_output_tokens, store, stream, service_tier, prompt_cache_options}`. The canonical bytes of `C` and `G` are bound (copied, not aliased) before any dispatch and durably journaled together with their SHA-256; the bytes actually leaving the process and the URL are verified against the bound bytes in a pre-send hook for both endpoints, and any difference aborts before dispatch and raises a `compatibility_halt` (§7.3). Provider JSON is parsed rejecting duplicate keys; a count response is valid only if `object == "response.input_tokens"` and `input_tokens` is a non-negative integer. Generation retries within a logical call reuse the identical `G` and the same count receipt; a correction call is a new logical call with its own count. No generation request is dispatched without a valid count receipt, an admitted count, bound bytes and a validated profile.
```

## A1.6 — §7.3

**old (verbatim from v0.4)**

```
### 7.3 Ordering of transport retry and malformed-output correction
For each batch: **logical call 1** → up to 3 transport attempts (retry the identical request only on connection failure, timeout, HTTP 429 or HTTP 5xx; only HTTP 2xx is a received model response for parsing. Other HTTP errors terminate the logical call immediately and forfeit the batch without correction. Every dispatched request consumes an attempt, regardless of whether it was billed or returned text). If no response is received after 3 attempts → all 10 slots of the batch **forfeited**; **no correction call**; proceed to the next batch (statelessness makes this well-defined). If a response is received → apply §6.7. If it yields ≥ 1 valid vector → evaluate them, forfeit the remainder, proceed. If it yields 0 valid vectors → **logical call 2 (correction)**: same system prompt; the user message is the original message with the appended line `PREVIOUS RESPONSE REJECTED: {reason}. Respond again following the output rules exactly.` → up to 3 transport attempts → apply §6.7 → evaluate valid, forfeit the rest. No further calls for that batch.
```

**new (complete replacement text)**

```
### 7.3 Ordering of transport retry and malformed-output correction
For each batch: **logical call 1** → **count step**: up to 3 count-class attempts with the identical count body (retry the identical request only on connection failure, timeout, HTTP 429 or HTTP 5xx, subject to the `Retry-After` and deadline rule of §7.2; a retry is never made when the remaining deadline is unknown or non-finite). A valid count is an HTTP 2xx body with `object == "response.input_tokens"` and a non-negative integer `input_tokens`. HTTP 401, 402 or 403 on either class halts further LLM dispatch for the run (credential/billing failure is not per-request): remaining LLM slots of the current and all later blocks are forfeited without replay, RS and CMA-ES continue under the frozen schedule, and the halt is journaled. Any other HTTP 4xx or exhaustion of 3 count attempts → batch **forfeited** (10 slots), **no correction call**, no generation request (ordinary failure: only this batch is affected). A malformed count body (2xx without a valid `object`/`input_tokens`), a failed profile/body validation, or a pre-send bytes/URL mismatch → **compatibility halt** (`compatibility_halt`): malformed provider or wire evidence means the contract cannot be trusted for any later request, so all future LLM dispatch for the run stops, the current batch and all remaining LLM slots are forfeited without replay, and RS/CMA-ES continue; this is not automatically IVF. If `input_tokens > L*` → **admission rejected**: batch forfeited, no correction call, the counted value recorded. Otherwise → **generation step**: up to 3 generation-class attempts with the identical generation body (same retry conditions and rule; 401/402/403 as above). Every HTTP 2xx `Response` object — whether `status` is `completed`, `incomplete` or `failed` — has its metadata and `usage` recorded and settled (§7.4 accounting rows) **before** any retry decision or parsing. A received model response is a 2xx object with `status ∈ {completed, incomplete}`; a 2xx object with `status: "failed"` and `error.code ∈ {server_error, rate_limit_exceeded}` counts as a failed attempt eligible for retry; `failed` with any other or missing code terminates the logical call and forfeits the batch without correction (ordinary failure); any other status (`in_progress`, `queued`, `cancelled`, missing), an unparseable or duplicate-key 2xx body, or a pre-send bytes/URL mismatch is malformed evidence → `compatibility_halt` as above. **Halt consequences for the text of the current attempt (pre-exposure method selection, fixed here):** on an `accounting_halt` raised by a received `completed`/`incomplete` object, the already-received text is parsed and its valid vectors evaluated, any correction call or other new provider call is suppressed, and all remaining future LLM slots are forfeited, with every mandatory billing unknown kept reserved; on an IVF, identity/profile, credential or compatibility halt, the current proposal is **not** evaluated (its slots are forfeited) and the raw text is retained for audit only. Only HTTP 2xx objects are parsed. Every dispatched request of either class consumes one attempt of its class, regardless of whether it was billed or returned text. If no model response is received after 3 generation attempts → all 10 slots of the batch **forfeited**; **no correction call**; proceed to the next batch (statelessness makes this well-defined). If a response is received → apply §6.7 to the concatenated `output_text` parts of `message` items in `output` (reasoning items are never parsed; a `refusal` part or empty output yields 0 valid vectors). If it yields ≥ 1 valid vector → evaluate them, forfeit the remainder, proceed. If it yields 0 valid vectors → **logical call 2 (correction)**: same system prompt; the user message is the original message with the appended line `PREVIOUS RESPONSE REJECTED: {reason}. Respond again following the output rules exactly.` → its own count step (new body, new receipt, same admission rule) → if admitted, up to 3 generation attempts → apply §6.7 → evaluate valid, forfeit the rest. No further calls for that batch.
```

## A1.7 — §7.4 rows

**old (verbatim from v0.4)**

```
| Provider model/fingerprint or effective decoding change; evidence of shared state or nonstationarity | Inferential validity failure (IVF), preserve metadata and outcomes (§8.3) | Neither confirmatory support nor exclusion is permitted |
```

**new (complete replacement text)**

```
| Provider model string or any required/baselined identity field (§6.1) changes after the baseline; `usage.input_tokens ≠ count receipt`; non-zero `cached_tokens` or `cache_write_tokens` under explicit mode with no breakpoints; other evidence of shared state or nonstationarity | Inferential validity failure (IVF): evidence of contract breach or drift. Applicable-rate charge recorded unclipped first; the current proposal is not evaluated (raw text retained for audit); LLM dispatch halted for both stages; remaining LLM slots forfeited without replay; RS/CMA-ES continue descriptively (§8.3) | Neither confirmatory support nor exclusion is permitted |
| LLM count-class exhaustion or terminal HTTP 4xx on the count | Batch forfeited (10 slots); no correction; cause `count_failure` (ordinary failure, this batch only) | Incumbent unchanged |
| Malformed count body, malformed or duplicate-key 2xx generation body, unexpected `status`, failed profile/body validation, or pre-send bytes/URL mismatch | `compatibility_halt`: all future LLM dispatch stops; current proposal not evaluated (raw bytes retained for audit); current and remaining LLM slots forfeited without replay; RS/CMA-ES continue. Not automatically IVF | Blocks remain in analysis; forfeits reported |
| LLM admission rejected (`input_tokens > L*`) | Batch forfeited (10 slots); no correction; cause `admission_rejected`; counted value recorded | Incumbent unchanged |
| HTTP 401/402/403 on either class | LLM dispatch halted for the run (`credential_halt`); current proposal not evaluated; remaining LLM slots forfeited without replay; RS/CMA-ES continue | Blocks remain in analysis; forfeits reported |
| Received 2xx object whose usage is not fully reconciled — mandatory `input_tokens`, `output_tokens`, `total_tokens`, `input_tokens_details.cached_tokens`, `.cache_write_tokens` missing or not non-negative integers, or `total_tokens ≠ input_tokens + output_tokens` — or a known applicable-rate charge above its reservation (any computable category-based charge and the raw inconsistent report are preserved; nothing is substituted by zero; `output_tokens_details.reasoning_tokens` is informational, included in `output_tokens`, never charged again) | `accounting_halt` (unverified accounting, distinct from IVF): a received `completed`/`incomplete` text is still parsed and its valid vectors evaluated; correction and all further provider calls suppressed; remaining LLM slots forfeited without replay; the full reservation is retained (unknown) or the overrun recorded unclipped. Under E9 policy this is a failed preflight. | Blocks remain in analysis; forfeits reported; confirmatory status unaffected unless an IVF row also applies |
```

## A1.8 — §7.5 addition

**old (verbatim from v0.4)**

```
Durably reserve the allotted slot or transport-attempt number before starting external work; append the completed response/result afterward. Never reuse a reserved number. If an arm is interrupted or the process crashes, do not resume its optimizer, partially completed batch or API request. Keep its durably completed valid evaluations and forfeit the remaining unreserved slots; retain reserved-but-unresolved attempts as uncertain resource usage. An objective reservation without a durable result is consumed/SVF with execution status unknown; it may represent a crash before invocation or during execution, so it is not counted as a confirmed call. An unresolved API reservation consumes one attempt allowance and is logged as dispatch/execution status unknown, and any missing billing/usage remains explicitly unknown rather than zero. Later arms and blocks may proceed under the frozen schedule after recovery, without rerunning the failed arm. If interruption occurs before any valid initialization value for an arm, its endpoint is undefined and SVF applies. This deliberately simple failure policy trades potential performance for auditable nonselective accounting; it removes checkpoint/serialization-dependent continuation from this experiment.
```

**new (complete replacement text)**

```
Durably reserve the allotted slot or transport-attempt number before starting external work; append the completed response/result afterward. Never reuse a reserved number. If an arm is interrupted or the process crashes, do not resume its optimizer, partially completed batch or API request. Keep its durably completed valid evaluations and forfeit the remaining unreserved slots; retain reserved-but-unresolved attempts as uncertain resource usage. An objective reservation without a durable result is consumed/SVF with execution status unknown; it may represent a crash before invocation or during execution, so it is not counted as a confirmed call. An unresolved API reservation consumes one attempt allowance and is logged as dispatch/execution status unknown, and any missing billing/usage remains explicitly unknown rather than zero. Later arms and blocks may proceed under the frozen schedule after recovery, without rerunning the failed arm. If interruption occurs before any valid initialization value for an arm, its endpoint is undefined and SVF applies. This deliberately simple failure policy trades potential performance for auditable nonselective accounting; it removes checkpoint/serialization-dependent continuation from this experiment. Count-class attempt numbers are durably reserved before dispatch exactly as generation attempts are, and the bound canonical request bytes are journaled before dispatch so that a process kill after dispatch leaves an auditable record; an unresolved count or generation reservation is logged as dispatch/execution status unknown with unknown billing, never zero. Retained headers exclude request authorization material.
```

## A1.9 — §8.3

**old (verbatim from v0.4)**

```
- **Stationarity assumption:** the model behind the recorded identifier is unchanged across all calls of both stages. Mitigation: record the response metadata identifier per call; execute both stages within the shortest feasible window; report any change. A known model, fingerprint or decoding change breaches the frozen stationarity model and sets IVF; any continued computation is descriptive only. Absence of a reported change is not proof that the service is stationary.
```

**new (complete replacement text)**

```
- **Stationarity assumption:** the model, tokenizer and serving configuration behind the recorded identifier are unchanged across all calls of both stages. Mitigation: record the identity vector and count receipt per call; require `usage.input_tokens == count receipt` on every generation response; execute both stages within the shortest feasible window; report any change. A change in the model string or any baselined identity field, or a count/usage mismatch, breaches the frozen stationarity model and sets IVF; any continued computation is descriptive only. Absence of a reported change is not proof that the service is stationary; under a single undated snapshot without a fingerprint, undetectable drift is possible and is disclosed with every confirmatory statement.
```

## A1.10 — §9.6

**old (verbatim from v0.4)**

```
Per stage: all 20 D values; the interval; decision category; sample median; number of floored endpoints; number of exact ties; per-block forfeits, objective calls, valid evaluations, duplicates for each arm; SVF and IVF events; best-so-far curves per arm (descriptive figure; label-revealing, see §10.4). Random-search endpoints alongside (descriptive).
```

**new (complete replacement text)**

```
Per stage: all 20 D values; the interval; decision category; sample median; number of floored endpoints; number of exact ties; per-block forfeits **by cause (invalid vector, zero-valid after correction, count failure or anomaly, admission rejected, generation transport exhaustion, terminal error, deadline, credential halt, compatibility halt, accounting halt, IVF halt)**, objective calls, valid evaluations, duplicates for each arm; **per dispatched LLM request: class, attempt numbers, counted input tokens, `usage` categories or explicit unknowns, applicable-rate charge or unknown**; SVF and IVF events; best-so-far curves per arm (descriptive figure; label-revealing, see §10.4). Random-search endpoints alongside (descriptive). Forfeit-cause tabulation is descriptive; it licenses no re-analysis, re-run or exclusion.
```

## A1.11 — §11 E9

**old (verbatim from v0.4)**

```
- **E9 LLM interface:** format-compliance smoke test with a **synthetic** history (fabricated numbers). Its purpose is to confirm transport and parsing, not performance; the number of such calls and their content are logged. This is the only permitted pre-freeze model call and it is an implementation-readiness activity, not authorized by this document.
```

**new (complete replacement text)**

```
- **E9 LLM interface:** format-, count- and identity-compliance smoke test with **synthetic** histories (fabricated numbers). Exactly four fixed fixtures — F1 (batch 1, 10 rows), F2 (batch 19, 190 rows, renderer maximum), F3 (byte-identical repeat of F2), F4 (F2 with the fixed correction suffix) — each run as one logical call: count step then, if admitted, generation step; ≤ 12 count and ≤ 12 generation attempts in total; monotonic stop limit 7,400 s (the nominal fixed-backoff HTTP allowance 24×300 + 8×25; server-imposed waits and overhead consume it, so not every maximum attempt is promised to fit). Pass conditions on every fixture: valid count; required echo fields equal the frozen profile (§6.1); `usage.input_tokens == count` with all mandatory usage categories present; `cached_tokens == cache_write_tokens == 0`; identity vector recorded and (F2 vs F3) identical; `count(F3) == count(F2)`; §6.7 parse result logged. Unknown mandatory usage, any profile mismatch, any count/usage inequality or any cache activity fails E9; no baseline is recorded from a failed E9. Over-limit rejection, count-only, count-failure, `Retry-After`, `status: failed/incomplete`, credential-halt, compatibility-halt, accounting-halt and IVF paths are exercised offline with mocked responses, not live. Every count and generation request, its bound and sent bytes, full response headers (without authorization material) and body are logged. E9 may not be used to choose L\*, the effort, or any prompt text; if a fixture count exceeds L\*, that is a recorded finding for a revised amendment. E9 is the only permitted pre-freeze provider call; it follows adoption of this amendment, requires its own recorded E9 gate (monetary authority covering both request classes and the billing evidence of §12 G-COST), and is not authorized by this document. Freeze follows closure of all §12 gates, not E9 alone.
```

## A1.12 — §12 G-MODEL

**old (verbatim from v0.4)**

```
| G-MODEL | Model identifier from response metadata; supported explicit decoding configuration or versioned documented defaults recorded; stable model identity established; `max_tokens` 8192 accepted; worst-case input (200 history rows, shortest-repr) fits the context limit with margin | Metadata capture + E9 log |
```

**new (complete replacement text)**

```
| G-MODEL | Model string from generation response metadata equals the frozen profile's; explicit request profile (§6.1) accepted live; required echo fields validated against the profile and the identity baseline captured at E9 and entered in the manifest; `max_output_tokens` 8192 accepted; admission limit L\* fixed before E9 and enforced; `usage.input_tokens == count` with complete usage on every E9 fixture; the observable-identity limitations of §6.1 recorded in the manifest | Metadata capture + E9 log |
```

## A1.13 — §12 G-TRANSPORT

**old (verbatim from v0.4)**

```
| G-TRANSPORT | Enforced attempt limits, 300 s timeout, backoffs, 36,000 s per-arm deadline, context/input-token ceiling and provider usage accounting validated with mocks and E9 | Engineering and E9 log |
```

**new (complete replacement text)**

```
| G-TRANSPORT | Enforced per-class attempt limits, 300 s timeout, nominal backoff and the `Retry-After`/deadline rule, 36,000 s per-arm deadline, count-to-send identity (profile validation, bound bytes, pre-send verification on both endpoints), status/error classification for 2xx objects, header retention, durable pre-dispatch journaling and provider usage accounting validated with mocks and E9 | Engineering and E9 log |
```

## A1.14 — §12 G-COST

**old (verbatim from v0.4)**

```
| G-COST | Concrete input/total token ceilings, provider billing categories, monetary spending ceiling and authorization for both stages recorded; no unknown billing quantity silently treated as zero | Budget and authority record before any paid preflight or evaluation |
```

**new (complete replacement text)**

```
| G-COST | Admission-limit-derived token ceilings for both request classes; conditional monetary scenarios at the hashed current price page (exact rational arithmetic independent of ambient numeric context, bounded finite positive rate grammar; exact subtotals; a combined total is null while any class's price is unknown — an assumed count fee yields only a conditional mathematical total, never billing completeness); **before any live dispatch, account/provider contract evidence covering count-request charges (including failed and rejected counts) and the applicable model rates, or an explicitly adopted and bounded financial-risk exception (none is proposed or adopted here)**; price page hash and validity date checked at every dispatch; monetary spending ceiling and authorization for E9 and both stages recorded; the software enforces attempt and reservation limits conditional on the recorded prices and provider compliance — it does not enforce the invoice; overruns and unknowns remain possible and are recorded unclipped; account usage tier, monthly limit and model rate limits recorded as operational context | Budget and authority record before any paid preflight or evaluation |
```

## A1.15 — §14.4

**old (verbatim from v0.4)**

```
*For a null or inconclusive result:* the prompt format, not the approach, limits the proposer; attention degradation over long exact-decimal histories; forfeits under the failure contract dominate the endpoint; the instance is easy enough that both arms saturate; resource-limited n = 20 may yield a wide interval, so moderate benefits can remain inconclusive.
```

**new (complete replacement text)**

```
*For a null or inconclusive result:* the prompt format, not the approach, limits the proposer; attention degradation over long exact-decimal histories; forfeits under the failure contract dominate the endpoint, including count-class failures, admission rejections and halts that exist only for the LLM arm; the instance is easy enough that both arms saturate; resource-limited n = 20 may yield a wide interval, so moderate benefits can remain inconclusive.
```

## Entry to append to `AMENDMENTS.md` on adoption (not appended by this draft)

> [adoption date] — Codex and Claude Science — protocol-v0.4 (`0df9242f…3eda5`) → protocol-v0.5 (`<hash of the file actually placed at specification/>`) — Reason: fingerprint and tokenizer-derived worst-case input ceiling not available on the inspected Responses route for `gpt-5.6-sol`; replaced by provider-counted admission with fixed L\* = 272,000 and an observable-identity standard, both stated as reductions of the evidence standard; count class budgeted separately; `Retry-After`, 2xx-status, accounting-halt and credential-halt rules made explicit — **pre-exposure** (0 objective evaluations, 0 provider calls at drafting; E9 not run). Retained disagreements: `counted_responses_amendment_review_2026-09-08.md` (rev 2) and this file. Superseded candidate value L\* = 200,000 recorded.

## Unresolved limitations retained (not resolved by this amendment)

- No serving fingerprint and a single undated snapshot: undetectable drift is possible; confirmatory statements carry this disclosure.
- Effective sampling values unobserved when echoed `null`; `temperature`/`top_p` are not sent and their effective values are undocumented for Sol.
- Count-class failures, admission rejections and halts exist only for the LLM arm.
- Count-endpoint billing undocumented; no provider-side per-request hard stop; project limits may lag; alerts do not stop requests (Cookbook `856bc6ae…`, used for the control pattern only, with fictitious example rates).
- `store: false` is not a retention guarantee.
- Live acceptance of the exact wire profile (`text.verbosity`, deprecated `truncation`, `prompt_cache_options.mode`, explicit effort, `store:false`) is unverified until E9.
- The existing candidate components (`qbridge_ext`) are components, not a launcher; Codex's integration finding (`arm_started` without `started`; `arm_closed` vs `arm_finished`) is open.
- Other providers or contract routes may exist that the retrieved documentation does not show.

## Not part of this amendment

No monetary figure is authorized; no provider is finally selected until E9 evidence exists; no custody, storage or blinding change; no E9, count or objective call is licensed; the candidate file is not the operative protocol.
