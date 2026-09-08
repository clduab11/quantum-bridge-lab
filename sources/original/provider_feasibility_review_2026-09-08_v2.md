# Provider Feasibility Review — 2026-09-08 — v2 (corrected)

**Reviewer:** Claude Science. **Supersedes:** v1 (`provider_feasibility_review_2026-09-08.md`, SHA-256 `2e609e82d9bed032ff36a28760d2b386148147cab0969764e03a8be12eb8519e`), which is preserved unchanged as historical evidence.
**Scope of this revision:** bounded reconciliation against Codex's correction list and two immutable source files. No new general search, no provider generation or token-counting call, no credential use, no install, no protocol / receipt / Project Context / GitHub / Linear edit. Advisory only; no gate opened.

**Inputs actually opened (hash-verified):**
- `ai_quantum_control_protocol_v0.4.md` — SHA-256 `0df9242fd2d0ad5d30b75ea91f498842ac68fe0df9616afd4c9c04518233eda5` (unchanged).
- `pursuit_decision_reconciled_2026-09-08.md` — SHA-256 prefix `b7c4b22d9de90d3a…` (unchanged).
- Codex `research/PROVIDER_FEASIBILITY.md` at commit `65769c8f5c61c215330ec660960fc261118b8f2f` — SHA-256 `1ccca0912035e03fa885a944f25a3d58cd2425903fd78ee8079f2f6888b3cce0`.
- Codex `research/PROMPT_BYTE_BOUND.md` at the same commit — SHA-256 `83b17ca17166151069f2f7c67bfb6c0f8b97e08fe5ea9ddfdcd9e75ac32be8ed`.
- Codex `docs/plans/2026-09-08-offline-preflight.md` at the same commit — SHA-256 `f8de9b4471b6897e3e8d29eb7c2469f8d8ecc0df71f5401a0da573d697a32094` (read only for the "Authority and limits" record).
- Correction brief `pasted-text-2026-09-08T21-01-34.txt`.
Not opened in this revision: the repository's prompt files, renderer source, tests, PR #3 budget planner, `research_evidence_brief_v2.md`, `protocol_governance_v2.md`. Claims about them below are Codex's, labelled `[CODEX]`.

Evidence labels: `[SOURCE]` = read in a search rendering of an official page in v1 (no page fetched in full, then or now); `[3RD]` = third-party measurement; `[CODEX]` = Codex's evidence, not re-verified by me; `[INFER]` = my inference; `[UNKNOWN]` = not established by anyone.

---

## 0. Verdict (revised)

Codex's cost arithmetic reproduces exactly and its billing-category model is consistent with what I checked. The v1 finding that the abbreviated challenge brief omitted the promotional character of Sol's \$4/\$20 stands only against that brief: Codex's full `PROVIDER_FEASIBILITY.md` already dates the promotion ("at least through November 21, 2026") and requires re-verification at budget authorization. The historical \$5/\$30 rate is a **stress-rate scenario**, not a known post-expiry price: "at least through" a date does not establish what the price becomes afterwards `[INFER]`. On identity, **neither inspected route** (Responses for Sol; Messages for Fable 5.1) exposes a serving fingerprint; this does not generalize to every endpoint of either provider — Sol is also served on Chat Completions, whose schema historically carries `system_fingerprint`, and Codex is checking whether that yields usable returned metadata `[CODEX]`. Schema presence would not by itself prove Sol returns a populated value. **G-MODEL stays open.** A prospective pre-exposure amendment to the gate's evidence standard remains one of the two honest options (the other is stop), and my preference that the amendment be a top-level decision by Chris is a **recommendation**, not a protocol permission rule: scientific-amendment authority is delegated to Codex/Claude Science by the user; freeze and spending authority are separate and not delegated. No provider is recommended; E9 is not opened.

---

## 1. Revision log (v1 → v2)

| # | v1 statement | v2 disposition |
|---|---|---|
| R1 | "Provable offline byte ceiling … tokens ≤ bytes for byte-level BPE … L_in ≤ 109,099 + δ" presented as a token bound; "δ … small relative to B_max"; "context limits satisfied with two orders of margin"; "272k threshold unreachable". | **Withdrawn.** A prompt byte maximum is not a provider-token theorem. Bytes and tokens are different units and cannot be compared as if identical; provider overhead (role delimiters, hidden instructions, configuration text) is `[UNKNOWN]` and cannot be declared small; the Anthropic tokenizer's per-token byte coverage is unverified. Context-fit and the 272k-threshold status are therefore `[UNKNOWN]` until a provider count exists. The byte figure is retained only as an offline size guard and fixture-construction aid, as Codex's `PROMPT_BYTE_BOUND.md` states. |
| R2 | "L=50,000 is roughly half the provable ceiling … a plausible estimate, not a bound". | **Corrected.** Codex's L=50,000 was explicitly hypothetical ("if a later verified ceiling were 50,000"), never proposed as verified. I retain it and one other hypothetical L as arbitrary inputs to the conditional formula; neither is derived from bytes or from any tokenizer. |
| R3 | Byte derivation: system 1,257 B; user 1,703 B; row 529 B incl. newline; 200 rows 105,800 B; "correction suffix … reason allowance 200 bytes ≈ 280 B"; total ≈ 109,099 B. | **Replaced by Codex's exact derivation** (`[CODEX]`, independently reviewed by Codex; I did not open the prompt files): system 1,258 and user 1,704 B including trailing LF; fixed text after removing four placeholders 2,910 B; scalar allowance 30 B; row ≤ 528 B with n−1 joining LFs. Theoretical 200-row grammar boundary: **108,739 B initial / 108,835 B with correction**. Actual renderer (batch 1..19, ≤190 rows): **103,449 / 103,545 B**. Correction reason is one of exactly `invalid_json` / `invalid_envelope` / `no_valid_vectors` (≤16 B); full suffix 96 B — not an arbitrary 200-byte reason. My v1 figures were within ~0.3 % but used a wrong suffix model and counted LF differently. |
| R4 | "max repr(float) is 24 characters (verified by sampling 200,000 random doubles and known extremes)". | **Corrected.** Finite sampling supports but does not prove the 24-byte maximum; Codex's analytic argument from the tagged CPython 3.11.15 short-repr source (17 significant digits + sign + point + `e` + exponent sign + 3 exponent digits) is the supporting derivation, conditional on the standard implementation. |
| R5 | Proposed E9 fixture "200 rows, every number 24 characters, 3-digit indices". | **Withdrawn as stated; replaced.** Indices 1..200 cannot all be 3 digits; I ≥ 0 has a shorter repr maximum than a signed coordinate; the renderer accepts batch 1..19 and at most 190 rows. Fixtures must be legal for the actual renderer (Codex's 190-row fixture with the 24-byte negative minimum-normal coordinate in every position rendered to 103,146 B `[CODEX]`); the 200-row figure is a theoretical grammar boundary, not a renderable request; the correction fixture uses exactly one normative reason code. |
| R6 | "Neither provider exposes a serving fingerprint" (generalized). | **Narrowed** to the two inspected routes; Chat Completions route for Sol under Codex review; schema presence ≠ returned populated metadata. |
| R7 | "Recommend the amendment … be a top-level decision by Chris … not a routine correction." | **Reframed** as a recommendation. Scientific-amendment authority is delegated to Codex/Claude Science; freeze and spending are separate, non-delegated gates. |
| R8 | E9 prerequisite: "a recorded permitted-implementation decision … still absent". | **Corrected.** The permitted-implementation decision for *offline code and analytic/synthetic preflight* is recorded in `docs/plans/2026-09-08-offline-preflight.md` ("Authority and limits": Chris's 2026-09-08 request interpreted with prior expert delegation; explicitly excludes paid model preflight, monetary ceilings, frozen execution). What is absent for E9 is **monetary authority and an E9-specific spending record**, which is a different gap. |
| R9 | "G-CUSTODY roles exist; credential handling must be added." | **Corrected.** Custody roles are **not established**; only synthetic custody fixtures exist (`[CODEX]`, offline plan Task 2: "do not establish a real study mapping"). |
| R10 | E9 plan "per candidate provider … 8 calls incl. a second configuration". | **Replaced.** Exactly **one** selected candidate and configuration is chosen and recorded before E9; fixed attempt cap; legal fixtures; no second configuration and no provider search implied. |
| R11 | "Real spend will be lower; the ceiling is what must be authorized." | **Replaced** with conditional-cap language: the figures are cap-consumption scenarios under stated assumptions; realized charges are `[UNKNOWN]` until usage is reconciled. |
| R12 | Latency: "at default effort the 300 s timeout is exposed to tail risk …; at max effort it is infeasible on average." | **Downgraded** to an unvalidated risk. Third-party TTFT/output-speed figures on short prompts do not measure this workload, do not expose high/max reasoning tail probabilities, and no reported figure is adopted as study latency. |
| R13 | Anthropic sampling rule stated from the Bedrock model card; Bedrock refusal-billing note. | **Marked `[UNKNOWN]` for the first-party Claude API.** Bedrock fields do not establish the first-party contract; pending direct documentation. |
| R14 | "`store: false` … §5 forbids server-side memory reuse." | **Reworded.** `store: false` may be preferred as a privacy/stateless construction; storage alone is not automatic memory reuse and does not by itself breach §5. |
| R15 | Correction requests asking the Decimal CLI to add promotional/list toggles, rate-validity date, regional multipliers. | **Withdrawn.** Rate validity and region belong in the eventual verified rate profile; the CLI already takes explicit conservative effective rates with none hard-coded. Retained only as an optional suggestion: a descriptive 1,520-logical-call line, noting that the 4,560 transport ceiling already covers it. |
| R16 | Regional uplift figures (OpenAI 10 %; Anthropic 1.1×). | Retained as `[SOURCE]`; Codex's file already states "can add 10 %". No correction needed. |

---

## 2. Findings, corrected

### A. Factual / billing
- **Prices** `[SOURCE]`/`[CODEX]` agree: Sol ≤272k input 4 / 0.40 / 5 / 20; >272k 8 / 0.80 / 10 / 30; Fable 5.1 10 / 0.25 / 12.50 (5 m) / 20 (1 h) / 50. Sol's promotion is dated in Codex's file. **Post-2026-11-21 price: `[UNKNOWN]`.** Freeze requires rate re-verification on the authorization date and an explicit expiry policy (what happens if the run window crosses a price change).
- **Billing categories** `[CODEX]`, consistent with `[SOURCE]`: OpenAI `input_tokens` inclusive, cached/cache-write subsets; Anthropic three disjoint input categories; reasoning/thinking inside inclusive output. Unreported category ≠ zero.
- **Counting endpoints** `[SOURCE]`: OpenAI documents exact rendered-request counting; Anthropic documents an estimate with possible small deviation and unbilled system-added tokens. Neither has been called.
- **Caching-off construction** `[CODEX]`; Azure documentation states the OpenAI explicit-mode/no-breakpoint configuration incurs no cache read/write `[SOURCE]`; for api.openai.com this is verified only when returned usage shows zero in both subsets.
- **SDK defaults** `[SOURCE]` (secondary quotations): `max_retries=2`, 600 s timeout in both Python SDKs; runner must set `max_retries=0` and its own 300 s boundary; Codex's file already says the scalar SDK timeout is not a substitute for the outer wall-clock boundary — agreed.
- **Fable 5.1 refusal path** `[SOURCE]`: 200 with `stop_reason: "refusal"`; optional `fallbacks` parameter exists — must not be sent (Codex's file: "Do not add model fallback"). Under §7.3 a refusal is a received response with zero valid vectors → correction path.
- **Sampling / thinking** `[SOURCE]` (first-party pages, v1): adaptive thinking always on for Fable 5.1; `thinking.disabled` → 400; `enabled`/`budget_tokens` rejected; effort default `high`. Sol `reasoning.effort` default `medium`. Exact first-party temperature/top_p/top_k acceptance rules for Fable 5.1: `[UNKNOWN]` (Bedrock card not adopted).
- **Environment facts** `[3RD]`: GPT-6 Astra launched 2026-09-03; no Sol retirement date reported. Stationarity/deprecation exposure to record, not a blocker.

### B. Identity / fingerprint / effective defaults vs v0.4 as written
- v0.4 §6.1 requires recording a "model fingerprint" and establishing "stable model identity"; §8.3 sets IVF on a known model/fingerprint/decoding change and states absence of a reported change is not proof of stationarity.
- Inspected routes: Responses (Sol) and Messages (Fable 5.1) — no serving fingerprint field found `[CODEX]`, consistent with my knowledge; not generalized to other endpoints. Chat Completions for Sol: schema historically has `system_fingerprint`; whether Sol returns a populated, meaningful value is `[UNKNOWN]` (Codex checking).
- ID-level pinning documented by Anthropic `[SOURCE]` and via OpenAI's snapshot language `[SOURCE]`; a constant ID is weaker than proven stationarity (Codex's file says the same).
- Effective defaults: recordable as "explicit fields sent + documented defaults for omitted fields + explicit list of fields whose effective value is undocumented". Adaptive thinking depth is nondeterministic by design.
- **Gate status: open for both candidates.** Options: (i) keep the literal text → no paid run; (ii) prospective pre-exposure amendment defining the observable stationarity record (requested ID, returned `model`, request/message IDs, API-version header, full request envelope, returned tier / stop reason / usage, execution window) and stating that serving-level stationarity is assumed, not verified, with IVF retained for any detected change. Recommendation (not a rule): decide (i)/(ii) before E9 so the E9 log captures the metadata that will count; my preference for Chris to make that call is a recommendation given delegated amendment authority.

### C. Offline byte bound — what it proves
- Proves (conditional on the standard CPython short-repr implementation and the literal prompt files): deterministic byte maxima for the rendered plain text — 103,449 / 103,545 B (actual renderer, 190 rows) and 108,739 / 108,835 B (200-row grammar boundary) `[CODEX]`; renderer byte-stability (E6); parser behavior on legal fixtures.
- Does **not** prove: any token count on any provider; provider overhead; context fit; which pricing tier applies; whether an 8,192-token output allowance leaves room for a visible 10×20 JSON after hidden reasoning; latency. Fabricated fixtures prove only what they are constructed to prove, and only when they are legal for the actual renderer.
- Accommodating estimated counts (proposal): keep the byte maximum as a pre-send **offline size guard**; obtain the provider's count on the legal maximal fixture at E9 (OpenAI exact; Anthropic estimate + explicit margin policy) and reconcile against returned `usage.input_tokens`; freeze L_in only from a provider count with a stated margin, never from bytes; log any post-hoc exceedance as an accounting deviation. Count calls are transport events whose logging class the amendment should define.

### D. Smallest defensible next step; retained disagreements; unknowns
1. Do not select a provider on presumed optimization performance. Select **one** candidate and one explicit configuration for E9 on non-performance grounds (documented identity semantics, explicit-configuration availability, cost scenario), record the choice and its rationale before any call.
2. Resolve the G-MODEL evidence-standard question (B) before E9 (recommendation).
3. Codex's provider-neutral Decimal CLI: adequate as is (explicit conservative effective rates, no defaults). Optional: a descriptive 1,520-logical-call line; not required for ceiling coverage.
4. Stop condition: if the literal fingerprint standard is retained and no route returns a usable serving identifier, the outcome is "no paid run" — a legitimate readiness result.

**Retained disagreements (Codex ↔ Claude Science):**
- I continue to treat \$5/\$30 as the stress rate that a spending ceiling should be computed at unless the run window is proven to end before any promotional expiry; Codex frames it as one scenario among several and requires re-verification at authorization — compatible, but the planning default differs.
- Latency versus the 300 s attempt boundary: I retain it as an unvalidated risk worth an explicit E9 measurement on the legal maximal fixture; Codex's file lists it under G-TRANSPORT implementation rather than as a feasibility risk.
- Prior disagreements in the offline receipt (no unconditional "likely inconclusive" prediction; exact-configuration novelty; unmeasured objective runtime) are untouched.

**Unknowns (explicit; never to be fabricated):** post-expiry Sol price; provider structural/hidden token overhead; tokens per byte for numeric content on each tokenizer; whether a populated fingerprint-like field is returned on any route for either model; first-party Fable 5.1 sampling acceptance rules and refusal/timeout billing; OpenAI hidden-system-content billing; effective `top_p` when omitted; whether a maximal legal request fits either context limit or crosses the 272k tier; visible-output survival under the 8,192 cap with hidden reasoning; per-attempt latency distribution on this workload; exact API-version/SDK version strings to be pinned; Sol deprecation schedule; the user's account-specific charges (taxes, minimums, regional uplift applicability).

### E. Fixed, finite, format-only E9 plan (proposal; gate not opened)
- **Preconditions:** one recorded candidate + configuration (B/D above); E9-specific monetary authority and cap recorded (G-COST partial) — distinct from the already-recorded offline permitted-implementation decision; credential handling defined (custody roles are not established; only synthetic fixtures exist — this must be stated, not assumed away); frozen prompt hashes (Codex: system `5165cfc3…`, template `80aa634b…` `[CODEX]`); committed fixture hashes; per-call log schema; SDK/transport versions pinned.
- **Fixtures (legal for the actual renderer; fabricated numbers; committed before any call):** F-min = batch 1, 10 rows; F-max = batch 19, 190 rows, 24-byte negative minimum-normal coordinate in every coordinate position, legal nonnegative objective (Codex's rendered size 103,146 B); F-corr = F-max plus the exact normative correction suffix with one reason code (96 B).
- **Calls (hard cap 4 generation calls; SDK retries 0; runner retries disabled for E9):** (1) F-min; (2) F-max — record all usage categories, returned `model`, IDs, stop/incomplete status, tier, wall-clock, whether visible output completes within 8,192, cache subsets (expected 0); (3) F-max repeated byte-identical — compare metadata; (4) F-corr. Optional, decided in advance: 0 or 2 count-endpoint calls on F-max, logged as their own class.
- **Conditional E9 cap (every call charged full hypothetical input L and full 8,192 output; USD):** at hypothetical L=108,835 (a number chosen to equal the byte boundary — an arbitrary token hypothesis, not a derivation): Sol 4/20 → 2.3967; Sol 5/20 (input at cache-write) → 2.8321; Sol stress 5/30 → 3.1597; Fable 5.1 10/50 → 5.9918. At hypothetical L=50,000: 1.4554 / 1.6554 / 1.9830 / 3.6384. Realized charges are unknown until usage is reconciled; the authorized figure is the cap, not a forecast.

### F. Conditional study cap-consumption table (both stages; unchanged formula)
n × (L×R + 8192×O)/10⁶, n ∈ {760, 1,520, 4,560}. Both L values are hypothetical inputs; neither is verified or derived.

| L (hypothetical) | Rate scenario | 760 | 1,520 | 4,560 |
|---|---|---|---|---|
| 50,000 | Sol promotional 4 / 20 | 276.5184 | 553.0368 | 1,659.1104 |
| 50,000 | Sol promotional, input at cache-write 5 / 20 | 314.5184 | 629.0368 | 1,887.1104 |
| 50,000 | Sol stress 5 / 30 | 376.7776 | 753.5552 | 2,260.6656 |
| 50,000 | Fable 5.1 10 / 50 | 691.2960 | 1,382.5920 | 4,147.7760 |
| 108,835 | Sol promotional 4 / 20 | 455.3768 | 910.7536 | 2,732.2608 |
| 108,835 | Sol promotional, input at cache-write 5 / 20 | 538.0914 | 1,076.1828 | 3,228.5484 |
| 108,835 | Sol stress 5 / 30 | 600.3506 | 1,200.7012 | 3,602.1036 |
| 108,835 | Fable 5.1 10 / 50 | 1,138.4420 | 2,276.8840 | 6,830.6520 |

Excluded: E9, counting calls, regional uplift (10 % / 1.1×), taxes, account fees, any post-expiry price. These are not expected bills, not a verified ceiling, and not an authorization.

---

## G. Remaining correction requests to Codex (routine; no gate implied)
1. In `PROVIDER_FEASIBILITY.md`, consider stating explicitly that the post-2026-11-21 Sol price is unknown and naming the expiry policy the freeze must contain.
2. Record the outcome of the Chat Completions `system_fingerprint` check for Sol (populated or not) as part of the G-MODEL evidence record, whichever way it falls.
3. When the E9 plan is drafted, name the single selected candidate/configuration and its non-performance rationale in the same document as the fixture hashes.

## H. Status notes taken from the correction brief (`[CODEX]`, not verified by me)
Repository `main` contains the initial milestone and README via merged PR #1/#2; draft PR #3 adds a budget planner; 233 tests and Ruff pass; no experimental data exists. Protocol v0.4 unchanged and unfrozen.

*End of v2. v1 preserved. No protocol, receipt, Project Context, GitHub or Linear content altered; no generation or token-count call made.*
