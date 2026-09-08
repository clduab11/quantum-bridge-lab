# Provider Feasibility Review — 2026-09-08

**Reviewer:** Claude Science (bounded adversarial review, delegated by Chris)
**Scope:** documentation review and arithmetic only. No provider calls, token-counting calls, credentials, installs, study-objective evaluations, protocol edits, freeze, or Project Context / GitHub / Linear edits were made. This document is advisory; it opens no gate.

**Inputs verified by hash (read from the project artifact store):**
- `ai_quantum_control_protocol_v0.4.md` — SHA-256 `0df9242fd2d0ad5d30b75ea91f498842ac68fe0df9616afd4c9c04518233eda5` (matches the operative draft cited in the challenge). Unchanged.
- `pursuit_decision_reconciled_2026-09-08.md` — SHA-256 prefix `b7c4b22d9de90d3a…` (matches the offline-milestone receipt). Unchanged.
- Challenge brief `pasted-text-2026-09-08T20-49-31.txt` (Codex's candidate evidence items 1–5).

**Evidence labels used below.** `[SOURCE]` = a statement I read today in a search-engine rendering of an official provider page (I did not fetch the pages directly; snippets, not full pages). `[3RD]` = third-party measurement or report, not a provider guarantee. `[CODEX]` = Codex's evidence, accepted or challenged as stated, not re-verified by me. `[INFER]` = my inference. `[UNCHECKED]` = I could not verify in this session. Nothing here is API validation; no call was made.

---

## 0. One-paragraph verdict

Codex's arithmetic is correct and its billing model (OpenAI inclusive input categories; Anthropic disjoint categories; reasoning/thinking inside output) is consistent with what I could check. Three material corrections: (1) the Sol \$4/\$20 rates are **promotional, guaranteed only through at least 2026-11-21**; the non-promotional list is \$5/\$30 (cache read \$0.50, cache write \$6.25), so any cap that may be spent after that date must be computed at \$5/\$30 (scheduled cap at L=50,000 rises from 276.52 to 376.78 USD; transport cap from 1,659.11 to 2,260.67 USD). (2) The illustrative L=50,000 is roughly half the **provable offline byte ceiling** (~109,099 bytes for 200 max-length rows plus template plus correction suffix); at that ceiling the caps roughly double on the input term. (3) Third-party latency measurements for Claude Fable 5.1 at its default effort (`high`) put mean time-to-first-token near 26 s and output speed near 56 tokens/s, so a maximal 8,192-token response alone consumes ~146 s of the 300 s per-attempt timeout; at `max` effort the mean TTFT (~267–291 s) makes the 300 s timeout infeasible. Neither provider exposes a serving fingerprint in the surfaces inspected (Codex; consistent with my knowledge; not verified by me for the Responses schema), so **v0.4 §6.1/§12 G-MODEL as written ("model fingerprint … stable model identity established") cannot be satisfied literally by either provider**. A prospective, pre-exposure amendment that names what stationarity evidence *is* observable — and states plainly what is not — is needed before E9 results can serve as G-MODEL evidence. I do not recommend a provider, and I do not recommend opening E9 now.

---

## A. Factual / API / billing challenges to the candidate evidence

### A1. OpenAI `gpt-5.6-sol`

| Claim in brief | Status | Note |
|---|---|---|
| 1,050,000 context; 128,000 max output; ID listed under snapshots | `[SOURCE]` consistent | Model page states snapshots "lock in a specific version"; the `gpt-5.6` alias routes to Sol. Snapshot ≠ serving fingerprint (see B). |
| Efforts none/low/medium/high/xhigh/max; medium default | `[SOURCE]` confirmed | Official GPT-5.6 guide: omitting `reasoning.effort` defaults to `medium`. `none` is API-only. |
| Rates 4 / 0.40 / 5 / 20 (≤272k) and 8 / 0.80 / 10 / 30 (>272k) | **`[SOURCE]` CORRECTION** | The model page states \$4/\$20 as a **promotional price available at least through November 21, 2026** (announced 2026-08-21 as a >20 % cut for three months). Launch/list price is \$5 input / \$30 output; with the documented 0.1× cache-read and 1.25× cache-write multipliers that is \$0.50 / \$6.25. The >272k rule (2× input, 1.5× output for the whole request) and the 1.25× cache-write rule are confirmed. **Any spending ceiling must be computed at the non-promotional rate unless the entire paid window is proven to end before the promotion does.** |
| Regional / service-tier / taxes not assumed away | `[SOURCE]` add specifics | OpenAI pricing page: data-residency (regional) endpoints carry a **10 % uplift** for models released on/after 2026-03-05 (Sol qualifies). `service_tier` unset means `auto` (project setting); setting `default` explicitly is correct; the response echoes the tier actually used — log it. |
| `max_output_tokens` 8192 includes hidden reasoning | `[CODEX]` consistent with my knowledge | Not re-verified today. Implication (INFER): reasoning can consume the whole cap and return an empty/incomplete visible answer → parse failure → correction path. This is a format-compliance property E9 must exercise on the maximal fixture. |
| No `system_fingerprint` in Responses reference | `[CODEX]`, `[UNCHECKED]` by me | I found `system_fingerprint` documented only for Chat/Completions ("represents the backend configuration"). I could not confirm its absence from the Responses object from search results; Codex's reading is consistent with my prior knowledge. Treat as: **no fingerprint available on the Responses path until shown otherwise.** |
| `input_tokens` endpoint counts exactly | `[SOURCE]` confirmed | Docs: returns the exact count, includes request-structure formatting tokens. Caveat (INFER): the prompt-caching guide mentions "OpenAI-provided hidden system content"; whether any such tokens appear in billed `input_tokens` is not stated in what I read — record as unknown, not zero. |
| Explicit-mode caching with no breakpoints ⇒ no read/write | `[SOURCE]` (Azure OpenAI doc states it explicitly); OpenAI direct `[INFER]` | The OpenAI guide describes explicit-only mode as avoiding unnecessary cache writes; the Azure page states "no prompt caching or cache-write charges" for that configuration. For api.openai.com this is a reasonable reading, **verified only when E9 usage shows `cached_tokens = 0` and cache-write tokens = 0.** |
| Not in brief | `[3RD]` new | **GPT-6 Astra (`gpt-6-astra`) launched 2026-09-03**; Sol is now the prior-generation flagship. Third-party sources state no retirement date has been announced for any GPT-5.6 model. Deprecation exposure during a multi-week study window is a stationarity risk to record, not a blocker. |
| Not in brief | `[3RD]` | Codex CLI users reported the *product* context window for Sol being silently cut (353k→258k) in July 2026; this concerns Codex, not the raw API, but it is evidence that provider-side serving configuration changes without notice — relevant to §8.3. |
| Not in brief | `[UNCHECKED]` | Responses API `store` defaults to true (my knowledge). The contract should set `store: false` explicitly; §5 forbids server-side memory reuse, and stored responses are unnecessary retention. Verify at E9. |

### A2. Anthropic `claude-fable-5-1`

| Claim in brief | Status | Note |
|---|---|---|
| Dateless IDs from 4.6 on are pinned snapshots; routing/classifiers/sampling infra can still change | `[SOURCE]` confirmed | Official versioning page: dateless ID "maps to a single, fixed model snapshot"; Anthropic "does not update the weights or configuration of an existing model ID"; updated versions ship under a new ID. The residual caveat (infrastructure/classifier changes) is Codex's reading and matches third-party quotations of the same page. |
| 1M context / 128k max output; adaptive thinking always on; default effort high; display omitted possible | `[SOURCE]` confirmed | Fable 5 overview page and Fable 5.1 migration guide. `thinking: {type: "disabled"}` → 400; **`thinking.type.enabled` with `budget_tokens` is also rejected on Fable 5.1** (troubleshooting page) — there is no fixed-budget mode; `effort` is the only depth control. |
| Non-default temperature/top_p/top_k rejected | `[SOURCE]` refine wording | Bedrock model card for Fable 5.1: temperature must be **1.0 or unset**; top_p must be **0.99 or unset**; temperature and top_p cannot both be specified; top_k not supported. So "explicit configuration" is expressible (temperature 1.0 explicit, top_p omitted). What "unset top_p" resolves to is not stated — record as unknown. Confirm on the first-party page; I read the Bedrock card. |
| `max_tokens` 8192 includes hidden thinking | `[SOURCE]` confirmed (Bedrock adaptive-thinking page: hard limit on thinking plus response). Same truncation implication as A1. |
| Rates 10 / 0.25 / 12.50 (5m) / 20 (1h) / 50 | `[SOURCE]` confirmed | Official pricing page: Fable 5.1 cache hit = 2.5 % of input = \$0.25/MTok (all other models 10 %); \$10/\$50 unchanged from Fable 5; cache writes 1.25×/2× (\$12.50/\$20). |
| Region/tier | `[SOURCE]` add specifics | `inference_geo` US-only inference = **1.1× on all token categories** (pricing page). Fable 5.1 is **not on Priority Tier** (migration guide). Not available under ZDR unless expressly authorized. |
| `count_tokens` is an estimate | `[SOURCE]` confirmed | Official page: "The token count is an estimate… may differ by a small amount"; system-added tokens are not billed. Claude 4.7+ tokenizer yields ~30 % more tokens than earlier models for the same text — so OpenAI-style token intuitions do not transfer. |
| No serving fingerprint in Message schema | `[CODEX]`, consistent with my knowledge | Response carries `model`, `id`, `stop_reason`, `usage`; no backend fingerprint. |
| Not in brief | `[SOURCE]` new | Fable 5.1 runs safety classifiers; a declined request returns HTTP 200 with `stop_reason: "refusal"` and `stop_details.category`, and **can fall back to another model via the `fallbacks` parameter**. The contract must **not** set `fallbacks`, must log `stop_reason`/`stop_details`, and must compare the response `model` field to the requested ID on every call (mismatch ⇒ IVF). Under §7.3 a refusal is a received 2xx with zero valid vectors → correction path, not a transport retry. |
| Not in brief | `[3RD]` latency | Artificial Analysis (first-party API, short prompts): TTFT ≈ 5.6 s (low), 18.7 s (medium), **25.7 s (high, the default)**, 109.5 s (xhigh), 266.8–291 s (max); output ≈ 56–69 tokens/s. A full 8,192-token response at 56 t/s ≈ 146 s. **INFER:** at default effort the 300 s per-attempt timeout is exposed to tail risk on maximal responses; at `max` effort it is infeasible on average. Sol: I found no comparable measurement today — unknown. §7.6's 300 s is a declared design value "verified at readiness"; E9 must measure it. |
| Not in brief | `[SOURCE]` | Bedrock: prompt-stage refusals not billed; mid-stream refusals billed for generated tokens. First-party behavior not stated in what I read → unknown, not zero. |

### A3. SDK / transport (both)

- `[SOURCE]` (secondary quotations of SDK constants): both Python SDKs default to **`max_retries = 2`** and a **600 s** per-attempt timeout. The runner must construct both clients with `max_retries=0` and `timeout=300` explicitly, else the SDK silently issues up to 3 HTTP requests per logical attempt and breaks the §7.3 attempt accounting. Codex's item 4 is correct on this point.
- `[INFER]` The OpenAI SDK attaches an idempotency-key header and a retry-count header per request; with `max_retries=0` these are inert but should be logged as part of the recorded request envelope.
- `[CODEX]` accepted: missing usage on failed/unknown attempts is never zero; reservation retained; local cancellation ≠ refund.

### A4. Arithmetic check (independent, `Decimal`)

Formula as stated: cost = n × (L×R + 8192×O) / 10⁶, n ∈ {760 scheduled logical calls, 1520 logical ceiling incl. corrections, 4560 transport ceiling}, both stages. Structural counts re-derived from v0.4: 19 batches × 40 blocks = 760; ×2 with corrections = 1,520; ×3 attempts = 4,560; 200 slots × 3 arms × 40 blocks = 24,000 objective slots. All of Codex's figures reproduce exactly (276.5184 / 1659.1104; 691.296 / 4147.776; 314.5184 / 1887.1104). The brief omits the 1,520 tier; added below.

| L (input tokens) | Rate scenario (R / O, USD per MTok) | 760 calls | 1,520 calls | 4,560 attempts |
|---|---|---|---|---|
| 50,000 | Sol promotional 4 / 20 | 276.5184 | 553.0368 | 1,659.1104 |
| 50,000 | Sol promotional, input reserved at cache-write 5 / 20 | 314.5184 | 629.0368 | 1,887.1104 |
| 50,000 | **Sol list 5 / 30** | **376.7776** | **753.5552** | **2,260.6656** |
| 50,000 | Sol list, input at cache-write 6.25 / 30 | 424.2776 | 848.5552 | 2,545.6656 |
| 50,000 | Fable 5.1 10 / 50 | 691.2960 | 1,382.5920 | 4,147.7760 |
| 50,000 | Fable 5.1 US-only 1.1× (11 / 55) | 760.4256 | 1,520.8512 | 4,562.5536 |
| 109,099 (byte bound, §C) | Sol promotional 4 / 20 | 456.1794 | 912.3587 | 2,737.0762 |
| 109,099 | **Sol list 5 / 30** | **601.3538** | **1,202.7076** | **3,608.1228** |
| 109,099 | Sol list, input at cache-write 6.25 / 30 | 704.9978 | 1,409.9957 | 4,229.9871 |
| 109,099 | Fable 5.1 10 / 50 | 1,140.4484 | 2,280.8968 | 6,842.6904 |
| 109,099 | Fable 5.1 US-only 1.1× | 1,254.4932 | 2,508.9865 | 7,526.9594 |

These are conditional cap-consumption scenarios (every attempt billed at full input and full 8,192 output), not expected bills and not an authorized ceiling. The >272k OpenAI surcharge is unreachable under the byte bound. E9, count-token calls, taxes, account minimums and any regional uplift are separate. A real ceiling also needs a stated rate-validity date because of the promotional expiry.

---

## B. Can either provider meet v0.4 *as written* for identity / fingerprint / effective defaults?

**What v0.4 requires (verbatim anchors).** §6.1: "record the exact request parameters, provider/API version and **model fingerprint** … If effective decoding settings or stable model identity cannot be established, G-MODEL remains open." §8.3: "record the response metadata identifier per call … A known model, **fingerprint** or decoding change … sets IVF … Absence of a reported change is not proof that the service is stationary." §12 G-MODEL: "Model identifier from response metadata; supported explicit decoding configuration or versioned documented defaults recorded; stable model identity established."

**Assessment.**
1. *Fingerprint.* Neither inspected response schema exposes a serving/backend fingerprint (`[CODEX]`, consistent with my knowledge; Responses absence `[UNCHECKED]` by me). The literal "model fingerprint" requirement is therefore **unsatisfiable by either provider on current documentation**. A model ID is not a fingerprint: Anthropic's own page says the pinned ID fixes weights and configuration but third-party quotations of the same documentation note that infrastructure updates can still produce minor behavioral differences; OpenAI's Chat-Completions fingerprint exists precisely because backend changes occur under a fixed snapshot ID.
2. *Stable model identity (ID level).* Both providers document ID-level pinning (Anthropic explicitly; OpenAI via "snapshots lock in a specific version"). Both return the served `model` in the response. This is the strongest observable evidence available and it should be recorded per call — but it is evidence of *identifier* stationarity, not *serving* stationarity.
3. *Effective decoding defaults.* Anthropic: temperature is documented as fixed at 1.0 (explicitly settable), top_k unsupported, top_p omitted-or-0.99; thinking depth is adaptive by design — **nondeterministic token consumption at a fixed effort is the documented behavior**, so "effective decoding" can be recorded as (effort, temperature=1.0, top_p omitted, thinking omitted, display omitted) with the caveat that the adaptive policy itself is unobservable. OpenAI: `reasoning.effort` has a documented default (`medium`) and can be set explicitly; sampling fields for reasoning models are not model-specifically documented in what I read (`[CODEX]` agrees) — record effort explicitly and record that temperature/top_p were omitted. Neither provider documents an effective *sampling* configuration to the level "versioned semantics" as §6.1 uses the phrase; the honest record is "explicit fields sent + documented defaults for omitted fields + list of fields whose effective value is undocumented".

**Conclusion for B.** As written, G-MODEL cannot close for either provider, and no run is licensed (§6.1 forbids "substituting an unknown value"). The choice is binary and must be recorded, not implied:
- (i) **Keep the gate literal → stop**: no paid run with either provider.
- (ii) **Prospective pre-exposure amendment** (AMENDMENTS.md, dated, `pre-exposure`) that replaces "model fingerprint" with the observable stationarity record — requested model ID; response `model`; provider API version header (`anthropic-version`; OpenAI request/response IDs and any version metadata); full request parameter envelope; `service_tier`/`stop_reason`/`stop_details`/`usage` per call; execution window timestamps — and adds an explicit sentence that **serving-level stationarity is not observable from either API, is assumed, and undetected changes remain an unverifiable residual**. The amendment must keep IVF for any *detected* change, must forbid `fallbacks`/alias IDs/`store`, and must not weaken §8.3's "absence of a reported change is not proof". This is a clarification of evidence standard, not a relaxation of the failure rule — but it *is* a relaxation of the literal G-MODEL text and must be labelled as such.

Timing: E9's log is the named evidence for G-MODEL. If E9 is run before the amendment defines what metadata counts, the E9 log may need to be repeated. **Recommend the amendment decision precede E9**, and that it be a top-level decision by Chris (it changes gate text), not a routine correction.

---

## C. What an offline byte/token bound can prove; how to accommodate estimated counts

**Computed today from the v0.4 normative text (no provider involved).**
- System prompt (§6.5): 1,257 bytes. User template (§6.6) before substitution: 1,703 bytes.
- Maximum `repr(float)` length is 24 characters (verified by sampling 200,000 random IEEE-754 doubles and the known extremes, e.g. `-2.2250738585072014e-308`). Index ≤ 3 digits.
- Worst-case history row: 3 + 1 + 24 + 20×(1+24) + newline = **529 bytes**. 200 rows (protocol ceiling; the scheduled maximum at batch 19 is 190 rows = 100,510 bytes) = **105,800 bytes**.
- Correction suffix with a bounded reason (allowance 200 bytes) ≈ 280 bytes; substituted scalars ≈ 60 bytes.
- **B_max ≈ 109,099 bytes** of rendered content per request.

**What this proves.** For any tokenizer in which every token covers at least one byte of the content (true for byte-level BPE, which OpenAI's tokenizers are; assumed, because unpublished, for Anthropic's), `L_content ≤ B_max` tokens. Provider-added structural/system tokens (δ) are outside this bound: OpenAI's counting includes request-structure tokens; Anthropic states system-added tokens are not billed. So the provable statement is **L_in ≤ 109,099 + δ**, with δ unknown offline and small relative to B_max. The 1,050,000 / 1,000,000 context limits are satisfied with two orders of margin regardless of tokenizer; the 8,192 output cap plus L_in fits trivially; the OpenAI 272k pricing threshold is unreachable.

**What it cannot prove.** The actual token count (tokenizer-dependent: a heuristic of ~9 tokens per 24-character number gives ≈ 42,000 tokens for 200 rows — an estimate that motivates L=50,000 for OpenAI-style tokenizers but is *not* a bound, and Anthropic's newer tokenizer is documented to be ~30 % denser on ordinary text, so 50,000 may be exceeded there); provider formatting overhead; whether a maximal response fits in 8,192 tokens once hidden reasoning is included; latency. **Fabricated worst-case-looking fixtures prove exactly what they are constructed to prove**: byte-stability of rendering (E6), parser behavior (duplicate keys, bare fences), and the byte ceiling — provided the fixture is *maximal by construction* (200 rows, every number 24 characters, 3-digit indices). A fixture that merely "looks large" proves nothing about the ceiling.

**Accommodating estimated counts (proposal, for the amendment/readiness record).**
1. Freeze **L_in := B_max + δ_allowance** (e.g., δ_allowance = 1,024 tokens) as the *cost and admission ceiling*. It is provable offline, conservative by ~2× on the input term, and makes the cost bound independent of tokenizer disputes. The total-token ceiling in §7.6 becomes 114 × (L_in + 8,192) per block with this L_in.
2. Keep §7.6's admission rule ("a request exceeding its ceiling is not sent") but make it byte-based for the pre-send check (deterministic, no provider call), and record the provider's post-hoc `usage.input_tokens` for every call as the *measured* quantity.
3. If a pre-send provider count is used at all: OpenAI's is documented exact for the request; Anthropic's is documented as an estimate — treat it as `count + margin`, never as truth, and reconcile against `usage.input_tokens`. Any post-hoc exceedance of L_in is logged as an accounting deviation (cost cap breach), never absorbed silently. Count calls are transport events: define their logging class in the amendment (pre-freeze they carry only synthetic content; in-study they carry real history but no outcome to any evaluator).
4. E9 must include the maximal-by-construction fixture so that one real `usage.input_tokens` value per provider exists to compare against B_max; the ratio (tokens/byte) becomes a recorded engineering measurement, not an assumption.

---

## D. Smallest defensible next step; retained disagreements; unknowns

**Recommendation (bounded).**
1. **Do not select a provider now**, and do not select on presumed optimization performance. Cost, latency feasibility against the 300 s timeout, and the fingerprint amendment are the discriminating facts, and two of the three are unmeasured.
2. **Record the B(ii) amendment question as a top-level pre-freeze decision** for Chris. Until it is decided, G-MODEL cannot close for any provider and the paid decision stays closed, consistent with the reconciled pursuit decision's requirement for "a named stable model/decoding contract".
3. **Codex's provider-neutral Decimal CLI** is an appropriate next artifact if it: takes rates and a *rate-validity date* as inputs (promotional vs list is a user input, never a default); accepts L as either an illustrative value or the byte-bound; prints all three tiers (760 / 1,520 / 4,560); prints the 1.1× / 10 % regional variants only when asked; and labels every output "conditional cap-consumption, not a ceiling". No default prices.
4. **Lower-cost candidate contracts exist but are a design decision, not a review finding.** Any smaller tier at either provider reduces the caps proportionally to its rates; choosing one is a change to "the one AI approach" and must be recorded as such before freeze, without reference to expected performance. I make no recommendation between tiers.
5. **Stop condition:** if the team holds G-MODEL to its literal fingerprint text, neither provider can satisfy it on current documentation, and the correct outcome is "no paid run" — a legitimate, reportable result of the readiness process, not a failure of the project.

**Retained disagreements / points Codex should confirm or contest.**
- Codex's brief presents Sol's \$4/\$20 without the promotional qualifier; I regard the list price as the binding planning rate.
- Codex's brief does not raise the latency-versus-300 s issue; I regard it as amendment-relevant for the Anthropic candidate at ≥ `xhigh` and as tail-risk at `high`, and unmeasured for Sol.
- I could not independently confirm the absence of `system_fingerprint` from the Responses schema; I accept Codex's reading provisionally.
- The prior disagreements recorded in the offline receipt (no unconditional "likely inconclusive" prediction; exact-configuration novelty; unmeasured objective runtime) are untouched by this review.

**Unknowns that block readiness regardless of provider (never to be fabricated):** δ (provider structural tokens); tokens/byte for the actual numeric content on each tokenizer; whether an 8,192-token cap yields a visible 10×20 JSON at the chosen effort on the maximal fixture; per-attempt latency distribution on 50k–110k-token inputs; the first-party (non-Bedrock) billing treatment of refusals and timed-out requests; OpenAI hidden-system-content billing; effective `top_p` when omitted (Anthropic); whether promotional pricing is extended past 2026-11-21; the exact anthropic-version / OpenAI API version strings the pinned SDKs send; GPT-5.6 Sol's deprecation schedule.

---

## E. A fixed, finite, format-only E9 plan (proposal — gate NOT opened)

**Purpose (per v0.4 §11 E9):** confirm transport and parsing with a synthetic history of fabricated numbers; not performance. Every call is logged in `EXPOSURE_LOG.jsonl`. No prompt tuning follows except format-only corrections already permitted by §6.2.

**Fixtures (committed with SHA-256 before any call):** F-min = 10 fabricated rows; F-max = 200 fabricated rows, every number exactly 24 characters, 3-digit indices, best_I/index/remaining substituted (maximal by construction, B ≈ 109 kB); F-corr = F-max plus the §7.3 rejection suffix with a fixed 200-byte reason.

**Calls per candidate provider (hard cap 4 generation calls; SDK `max_retries=0`; runner retries disabled for E9 so the count is exact):**
1. F-min → parse under §6.7 rules; record full response metadata.
2. F-max → record `usage` (all categories), `model`, `stop_reason`/`incomplete` status, `service_tier`, wall-clock, whether visible output is complete within 8,192, and cache read/write counters (expected 0).
3. F-max again, identical bytes → compare metadata to call 2 (identifier stationarity, cache counters still 0, latency second sample).
4. F-corr → confirm the correction path renders, is accepted, and parses.
Optional (0 or 2 calls, decided in advance): the provider's token-count endpoint on F-max, to obtain a pre-send count for comparison with `usage.input_tokens`; classify these calls explicitly in the log.

**E9 cost ceiling (conditional; full 8,192 output charged on every call; L = 109,099):** per call Sol list 0.7913 USD → 4 calls 3.17 USD (8 calls incl. a second configuration 6.33); Sol promotional 0.6002 → 2.40 / 4.80; Fable 5.1 1.5006 → 6.00 / 12.00; US-only 1.1× 1.6506 → 6.60 / 13.20. Count-endpoint calls are documented free (Anthropic; OpenAI not checked for price today). Real spend will be lower; the ceiling is what must be authorized.

**Prerequisites before any E9 call (all currently open):** a recorded permitted-implementation decision (v0.4 §13 step 2 — still absent per the offline receipt); a recorded E9 monetary ceiling and rate-validity date (G-COST partial); credential custody named (G-CUSTODY roles exist; credential handling must be added); frozen prompt files with hashes; committed fixture hashes; the B(ii) amendment decision so the metadata captured is the metadata that counts; a per-call log schema listing every field above; and the SDK pin (openai / anthropic versions) added to the uv.lock record so the request envelope is reproducible.

---

## F. Correction requests (to Codex; routine document corrections, no gate implied)

1. Provider-feasibility notes and the Decimal CLI: label Sol \$4/\$20 as promotional through ≥ 2026-11-21 and carry the \$5/\$30 list rate as the planning rate.
2. Add the 1,520-call tier to every cost table.
3. Add the offline byte bound (529 B/row; 105,800 B for 200 rows; ≈109,099 B total) and state that L=50,000 is an unproven estimate below the provable ceiling.
4. Add the regional multipliers (OpenAI 10 % data-residency uplift; Anthropic 1.1× US-only) as optional inputs.
5. Record the Fable 5.1 sampling rule precisely (temperature 1.0 or unset; top_p 0.99 or unset; not both; top_k unsupported) and that `thinking.enabled`/`budget_tokens` are rejected.
6. Add `fallbacks`, `store`, alias IDs and `prompt_cache_key` to the list of fields the contract must *not* send, and `stop_reason`/`stop_details`/`service_tier` to the fields it must log.
7. Add the latency measurements (third-party, labelled as such) to the G-TRANSPORT/G-RUNTIME open-items list.
8. Raise the G-MODEL fingerprint question to Chris as a top-level amendment decision.

---

## G. Sources actually checked (search-engine renderings of the pages, 2026-09-08; no page fetched in full)

Official (OpenAI): model page `gpt-5.6-sol` (promotional pricing, >272k rule, 1.25× cache write, snapshots); pricing page (regional 10 % uplift; Daybreak aliases); prompt-caching guide (1,024-token minimum; explicit-only mode; 1.25× writes); token-counting guide and `responses.input_tokens.count` reference (exact count; formatting tokens); GPT-5.6 latest-model guide (`reasoning.effort` levels; `medium` default; alias routing); Chat Completions reference (`system_fingerprint`; `service_tier` semantics); OpenAI launch post (\$5/\$30 list; 2026-08-21 promotional note).
Official (Anthropic): pricing page (Fable 5.1 2.5 % cache read; `inference_geo` 1.1×); Fable 5 overview (1M/128K; adaptive always on; default high; legacy status); Fable 5.1 what's-new and migration guide (thinking disabled → 400; forced tool choice → 400; refusal `stop_reason`; `fallbacks`; not on Priority Tier; ZDR restriction); thinking troubleshooting page (`enabled`/`budget_tokens` rejected on Fable 5.1); token-counting page (estimate; system-added tokens unbilled; 4.7+ tokenizer ~30 % denser); model IDs and versioning page (dateless pinned IDs).
Official (AWS Bedrock model cards, used as a proxy for sampling rules): Fable 5 and Fable 5.1 cards; adaptive-thinking page (max_tokens includes thinking).
Official (Microsoft Azure OpenAI): prompt-caching page (explicit mode with no breakpoints ⇒ no caching / no write charges).
Third-party: Artificial Analysis model pages (Fable 5.1 TTFT and t/s by effort); OpenAI SDK/Anthropic SDK default constants as quoted in secondary sources (max_retries 2, timeout 600 s); GPT-6 Astra launch coverage; Codex CLI GitHub issues on context-window changes; VentureBeat/others on Fable 5.1 cache-write rates.
Not checked: `_base_client.py` sources directly; the Responses `create` reference page directly; the Fable 5.1 first-party overview page directly; OpenAI deprecations page.

*End of review. No gate opened; no protocol, receipt, Project Context, GitHub or Linear content altered.*
