# Counted Responses request and accounting contract — implementable draft, revision 3 (2026-09-08)

**Status.** Draft for Codex's execution design, revised after Codex's technical review, second offline check, and review of the full candidate diff (rev 3: anomaly/halt reconciliation, fixed 1 s dispatch margin, `transport_reservation` journal key). Candidate contract; never sent a request; selects no provider, closes no gate, authorizes no spending, and claims no integration with the existing `qbridge_ext` components (Codex's integration finding — `arm_started` without `started`, `arm_closed` vs `arm_finished` — is open; those components are components, not a launcher). Every provider fact is from the project's hashed 2026-09-08 documentation set or direct inspection of openai-python 3.9.0; account facts are marked UNKNOWN. Rates quoted below are the documented `gpt-5.6-sol` list prices (`sol_model.md` SHA `6aaf0b71…`: "$4 per million input tokens and $20 per million output tokens … promotional pricing is available at least through November 21, 2026"; `pricing.md` `244b537c…` row `gpt-5.6-sol | $4.00 | $0.40 | $5.00 | $20.00 | $8.00 | $0.80 | $10.00 | $30.00`); the OpenAI Cookbook article (`856bc6ae…`) is cited only for the control pattern — its own example rates are fictitious and are not used. Reference implementation of the pure functions: `counted_responses_reference.py` (SHA-256 `9804ad049dcb9cc2e367e7734bced79b377945a00350b2af0b8c4cab2670d0f4`), tests `test_counted_responses_reference.py` (`f3a3d3901e2910fa95b82f9272e4c2b01b7f1973c2acb074491066b21b8eb4e3`), 152 passed, Ruff clean, CPython 3.11.16 in the `qbridge` sandbox env (not the study environment). **Admission limit under this revision: L\* = 272,000** (Codex's prospective selection; 200,000 superseded).

## 1. Endpoints, SDK, transport

| Item | Contract |
|---|---|
| Generation | `POST https://api.openai.com/v1/responses` (no regional base URL) |
| Count | `POST https://api.openai.com/v1/responses/input_tokens`; SDK: `client.responses.input_tokens.count(**C)` (non-beta resource in 3.9.0) |
| SDK | openai-python pinned (3.9.0 inspected); `OpenAI(max_retries=0, timeout=<runner-supplied ≤ 300 s>)`; SDK defaults (2 retries, 600 s) must be overridden — same as the Chat candidate |
| Pre-send hook | httpx event hook compares the outgoing URL and canonical body bytes against the intended `C` or `G`; any difference raises before the request leaves; zero dispatches on altered fields |
| Streaming/background | never (`stream:false`; `background` omitted) |
| Retention of every attempt | bound canonical bytes journaled **before** dispatch (process-kill audit), request URL, sent bytes + SHA-256, HTTP status, **all response headers excluding request authorization material**, raw body bytes, wall-clock start/end, attempt number and class, reservation id, settlement record, outcome class |

## 2. Bodies

Generation body `G` (runner supplies `system`, `user`, `max_tokens == 8192`; texts ASCII, copied byte-for-byte):

```json
{
  "model": "gpt-5.6-sol",
  "input": [
    {"role": "developer", "content": "<system_v0.3.txt bytes>"},
    {"role": "user",      "content": "<rendered user message bytes>"}
  ],
  "reasoning": {"effort": "medium"},
  "text": {"verbosity": "medium"},
  "truncation": "disabled",
  "max_output_tokens": 8192,
  "store": false,
  "stream": false,
  "service_tier": "default",
  "prompt_cache_options": {"mode": "explicit"}
}
```

Count body `C` = exact projection onto the count schema (SDK 3.9.0: `conversation, input, instructions, model, parallel_tool_calls, personality, previous_response_id, reasoning, text, tool_choice, tools, truncation`) ⇒ under this profile exactly:

```json
{"model": "...", "input": [...], "reasoning": {...}, "text": {...}, "truncation": "disabled"}
```

Rules: before projection the full profile of `G` is validated value by value with strict types (`validate_generation_body`: exact model string; exactly two plain-string items with roles `developer`, `user`, ASCII; `reasoning` exactly `{"effort": <fixed>}`; `text` exactly `{"verbosity": "medium"}`; `max_output_tokens` the int 8192 (not bool/float); `store`/`stream` the bool `false`; `prompt_cache_options` exactly `{"mode": "explicit"}`); the projection is a deep copy (no aliasing) and the canonical bytes of `C` and `G` are bound and journaled before dispatch. `G` may contain only `C`'s keys plus `{max_output_tokens, store, stream, service_tier, prompt_cache_options}`; `personality` (count-only), `instructions`, all tool/linkage/sampling/caching-key fields are forbidden on both; content is a plain string so no `prompt_cache_breakpoint` can exist; `reasoning` carries only `effort`. Hashes: `sha256(canonical(C))` = count-receipt key; `sha256(canonical(G))` = generation-body hash; both plus `sha256(sent_bytes)` in every log row. Canonical form: JSON, sorted keys, separators `,`/`:`, ASCII.

Documentation notes to carry into the manifest: `truncation` is marked *Deprecated* in the reference but `disabled` is the documented default and is what makes over-context input fail with HTTP 400 — send it; a future rejection is a contract failure, not a field to drop. `text.verbosity` default is documented as `medium`; it is on the provider's list of prefix-affecting settings, hence sent explicitly and counted. `prompt_cache_options.mode: "explicit"` with no breakpoints: "the request does not use prompt caching" (create reference; GPT-5.6-and-later section of the caching guide).

## 3. Logical-call state machine (per batch; correction is a second logical call with its own count)

```
reserve count attempt n (durable) → dispatch C → classify (Table A)
  count_retryable & n<3 → backoff(n) → reserve n+1 → dispatch C
  count_terminal | exhausted → FORFEIT batch only (ordinary failure), no correction, stop
  count_contract_anomaly | body/profile validation failure | pre-send bytes/URL mismatch → COMPATIBILITY HALT (all future LLM dispatch), current proposal not evaluated, stop
  count_halt_credential → CREDENTIAL HALT (all future LLM dispatch), forfeit remaining LLM slots, stop
  count_ok → receipt = (sha256(C), input_tokens, response id/headers, t)
admission: input_tokens ≤ L*  ? continue : FORFEIT batch (admission_rejected), stop
reserve generation attempt m (durable) → reserve money (§5) → dispatch G → classify (Table B)
  gen_retryable & m<3 → backoff(m) → reserve m+1 → dispatch identical G (same receipt)
  gen_terminal | gen_failed_terminal | exhausted → FORFEIT batch only, no correction, stop
  gen_contract_anomaly (unexpected status, unparseable/duplicate-key body, bytes mismatch) → COMPATIBILITY HALT, current proposal not evaluated, stop
  gen_halt_credential → CREDENTIAL HALT as above
  received_completed | received_incomplete → settle (Table C) → consequence:
      no halt → parse §6.7 → evaluate valid / forfeit rest; zero valid & call 1 → correction logical call (new C, new receipt, new G)
      accounting_halt → parse §6.7 and evaluate this already-received text; NO correction, NO further provider calls; forfeit remaining future LLM slots; unknowns stay reserved
      ivf_halt (mismatch / cache activity / identity or profile change) → current proposal NOT evaluated (raw text retained for audit); forfeit; halt all future LLM dispatch
```

**Order for every 2xx generation object (any `status`):** strict parse (duplicate keys ⇒ anomaly) → settle usage and applicable-rate charge, preserve the received usage, validate the echoed profile → only then classify retry/received (`handle_generation_response`). A settlement halt (`ivf_halt`, `accounting_halt`, `e9_fail`) overrides any retry.

`backoff(n)` (predetermined, `retry_decision`): nominal 5 s after attempt 1, 20 s after attempt 2; if `Retry-After` is present the wait is max(nominal, server minimum) and is **never shortened**; retry only if wait ≤ 300 s and wait + a fixed dispatch margin of exactly 1 s (`DISPATCH_MARGIN_S`) fits the remaining arm deadline, which must be a known finite number (unknown/NaN/∞ ⇒ no retry); malformed `Retry-After` ⇒ no retry; delta-seconds parsed as non-negative integers, HTTP-dates measured against the response `Date` header else receipt time, past dates ⇒ minimum satisfied; `retry-after-ms` recorded, not interpreted. Bool attempt numbers and non-int waits are contract violations. All waits and dispatches are inside the 36,000 s monotonic arm deadline; at expiry stop new work, cancel in-flight work, forfeit remaining slots, retain unknown usage for any in-flight reservation.

### Table A — count class

| Observation | Class | Retry? | Effect |
|---|---|---|---|
| connection failure / timeout | `count_retryable` | yes (≤3) | attempt consumed; usage unknown |
| HTTP 429, 5xx | `count_retryable` | yes | as above; `Retry-After` honored |
| HTTP 401/402/403 | `count_halt_credential` | no | halt LLM dispatch for run |
| other HTTP 4xx | `count_terminal` | no | batch forfeited only, no correction (ordinary failure) |
| 2xx, `object=="response.input_tokens"`, `input_tokens` non-negative int (not bool) | `count_ok` | — | receipt stored |
| 2xx otherwise (malformed / duplicate keys / missing fields), body or profile validation failure, pre-send bytes/URL mismatch | `count_contract_anomaly` / `contract_violation` | no | **compatibility halt**: all future LLM dispatch stops; not automatically IVF |

### Table B — generation class (Responses object; applied only after Table C settlement of any 2xx object)

| Observation | Class | Retry? | Effect |
|---|---|---|---|
| connection / timeout / 429 / 5xx | `gen_retryable` | yes (≤3, per `retry_decision`) | attempt consumed; **usage unknown → reservation retained** |
| unknown transport error string, non-int status, 3xx | `gen_contract_anomaly` | no | compatibility halt (never defaulted to retryable) |
| 401/402/403 | `gen_halt_credential` | no | halt |
| other 4xx | `gen_terminal` | no | batch forfeited only, no correction (ordinary failure) |
| 2xx `status:"completed"` | `received_completed` | — | parse |
| 2xx `status:"incomplete"` (`incomplete_details.reason` recorded: `max_output_tokens`, `content_filter`, …) | `received_incomplete` | — | received response (§7.4 truncation row); usage recorded if present |
| 2xx `status:"failed"`, `error.code ∈ {server_error, rate_limit_exceeded}` | `gen_failed_retryable` | yes, unless settlement halted | attempt consumed; its usage/charge already recorded |
| 2xx `status:"failed"`, other/missing/non-object `error` | `gen_failed_terminal` | no | batch forfeited only |
| 2xx any other status (`in_progress`, `queued`, `cancelled`, missing), unparseable or duplicate-key body | `gen_contract_anomaly` | no | **compatibility halt**; current proposal not evaluated, raw bytes retained |

Output text for parsing = concatenation of `output_text` parts of `message` items in `output`; `refusal` parts or empty output ⇒ zero valid vectors ⇒ correction path. Reasoning items are never parsed.

### Table C — settlement and identity checks on every 2xx object (before Table B)

| Check | Pass | Fail handling |
|---|---|---|
| mandatory usage as non-negative ints: `input_tokens`, `output_tokens`, `total_tokens`, `input_tokens_details.cached_tokens`, `.cache_write_tokens`; and `total_tokens == input_tokens + output_tokens` (the provider's own spending-controller check) | all present and consistent (`reconciled: true`) | `*_unknown` / `total_tokens_inconsistent` / `cache_categories_exceed_input`: report is **not reconciled**; any computable category-based charge and the raw inconsistent report are preserved, nothing is substituted by zero, **full reservation retained**, `accounting_halt` (study) / `e9_fail` (E9); a received text is still evaluated per §7.3. `output_tokens_details.reasoning_tokens` is informational (inside `output_tokens`, never charged again); an impossible value is recorded only |
| `usage.input_tokens == receipt.input_tokens` | equal | `count_usage_mismatch` → **IVF** (`ivf_halt`; E9: `e9_fail`); applicable-rate charge recorded unclipped first |
| `cached_tokens == 0` and `cache_write_tokens == 0` | both zero | `cache_activity` → IVF; charge includes cache categories at their rates, unclipped |
| applicable-rate charge ≤ reservation | ≤ | overrun recorded unclipped → `accounting_halt` / `e9_fail` |
| **required echo** (strict types): `object == "response"`, `model == "gpt-5.6-sol"`, `service_tier == "default"`, `truncation == "disabled"`, `max_output_tokens == 8192` (int), `store == false` (bool), `reasoning.effort == <fixed>`, `text.verbosity == "medium"`, `prompt_cache_options.mode == "explicit"` | all equal | `profile_echo_missing/mismatch` → before baseline: unverified compatibility, E9 fails, no baseline; after baseline: IVF |
| **optional-safe**: `background` absent or `false`; `tools` absent or `[]` | safe | `profile_unsafe_value` → same as above, even on the first response |
| **identity vector** vs baseline: presence-tagged canonical values for every identity key, including the **whole** `reasoning`, `text`, `prompt_cache_options` objects and `temperature`, `top_p` | identical | `identity_change:<key>` → IVF |

Halt classes are distinct: `credential_halt` (401/402/403), `compatibility_halt` (malformed count/body/wire evidence; not automatically IVF), `accounting_halt` (unverified accounting: unknown mandatory usage or known overrun), `ivf_halt` (evidence of contract breach or drift). Every halt stops all future LLM dispatch for the run, forfeits remaining LLM slots without replay, and lets RS/CMA-ES continue; only IVF blocks confirmatory interpretation. **Treatment of the current attempt's text (pre-exposure method selection):** `accounting_halt` on a received `completed`/`incomplete` object → the received text is parsed and its valid vectors evaluated, corrections and any new provider call are suppressed, unknowns stay reserved; `ivf_halt`, identity/profile failure, `credential_halt`, `compatibility_halt` → the current proposal is not evaluated, raw text retained for audit. Ordinary failures (count exhaustion, terminal HTTP, `failed` with a non-retryable code) forfeit only that batch. Encoded in `attempt_consequence`. Baseline = identity vector of the first profile-valid `completed` E9 response; written to the journal and manifest; re-read before every dispatch (forked workers).

## 4. Journal events (append-only, re-read before every dispatch)

`halt_state`, `identity_baseline`, `price_validity {rate_source_hash, price_valid_through_utc}`, `authority {scope: e9|study, ceilings per class, L*, profile_hash}`, `reservation {class, attempt_no, body_hash, money_reserved | null}` — the top-level `reservation` key is owned exclusively by the reserve/complete pair (`DurableJournal.complete` refuses completion if extra matches exist); every auxiliary dispatch/retention/settlement event references it as `transport_reservation`, never `reservation`, `count_receipt {C_hash, input_tokens, response_headers, t}`, `dispatch {class, attempt_no, sent_bytes_hash, url}`, `outcome {class, http_status, outcome_class, usage | unknown, findings[]}`, `forfeit {batch, cause}`, `halt {class ∈ credential|compatibility|accounting|ivf, reason, transport_reservation}`, `ivf {reason}`; `provider_halted` is re-read by the parent before accepting any child text (Codex runner design: parent reserves each transport attempt, child performs the single HTTP request and its ledger, parent completes the attempt). Raw bodies/headers to protected `raw/`; nothing identity-bearing in the public repo.

## 5. Accounting ledger (two request classes, one monetary ceiling per scope)

- **Money grammar.** All rates and amounts are exact rationals (`Fraction`) built from decimal strings or `Decimal`s; floats, bools, NaN and infinities are rejected; rates must be strictly positive, finite and below 1 USD per token (bounded grammar); exactly the four documented categories (`input`, `cached_input`, `cache_write`, `output`). Arithmetic is independent of the ambient `Decimal` context and traps; rendering uses a fresh 60-digit context and refuses to round a non-terminating value silently. Rates, reservations and policy (`e9`|`study`) are validated on every entry point.
- **Generation reservation (exact input, capped output):** `reserve_gen = receipt.input_tokens × R_in + 8192 × R_out` at the rates bound in the authority record (documented list rates 4/0.4/5/20 USD per MTok, promotional, dated at least through 2026-11-21 per the hashed model page; price page hash and validity checked before every dispatch including retries). Settlement on any 2xx object with complete usage: `actual = ordinary_input × R_in + cached × R_cached + cache_write × R_write + output × R_out` (cache categories are themselves an IVF finding), unclipped; unused reservation released. Unknown usage (transport failure, timeout, missing categories, unresolved reservation): **full reservation retained permanently**; known actual above reservation: recorded unclipped and halts.
- **Count reservation:** the count fee is **UNKNOWN** (no pricing row). An assumed count rate, if the authority record names one and labels it an assumption, yields a *conditional mathematical total* in Codex's separate count-budget calculator; it never establishes billing completeness, and **the combined monetary total is `null` while the count fee is unknown**. A null total cannot satisfy G-COST.
- **Scenarios vs authority (not circular).** Prospective scenarios may be written now from documented rates and the caps: per generation attempt (L\* + 8192 tokens) 1.25184 USD at L\* = 272,000 (superseded 200,000: 0.96384); 760 / 1,520 / 4,560 attempts: 951.3984 / 1,902.7968 / 5,708.3904 USD (200,000: 732.5184 / 1,465.0368 / 4,395.1104); E9 12 attempts 15.02208 (200,000: 11.56608); stress 5/30 at 4,560: 7,322.2656 (200,000: 5,680.6656); count class 4,560 / 12 requests, price unknown. Exact subtotals; only a calculator's combined total is rounded (up, cents) and only when non-null. **Dispatch authority is separate:** before any live dispatch the record must hold account/provider contract evidence covering count-request charges (including failed and rejected counts) and the applicable model rates, or an explicitly adopted and bounded financial-risk exception — none is proposed or adopted. Four E9 observations or delayed daily Costs totals cannot prove a fee maximum or free counting; E9 cost reconciliation against the account's cost records is a post-hoc check, not the evidence that licenses E9.
- **Enforcement vs guarantee:** the software enforces attempt caps and reservation limits **conditional on the recorded prices and on provider compliance**; it does not enforce the invoice. Provider project spend limits "may not take effect immediately" and "alerts do not stop requests"; the Costs API shows daily totals (Cookbook, SHA-256 `856bc6ae…`, control pattern only). Price overruns and unknown charges remain possible and are recorded unclipped; the actual invoice is reconciled after the fact and recorded even if it differs.
- **Account evidence (operational context; required before dispatch authority, not before writing this amendment):** organization usage tier and monthly usage limit; `gpt-5.6-sol` RPM/TPM in the project (rate-limit consumption is a character-based estimate per the rate-limit guide, so exact counts do not predict it; `x-ratelimit-*` headers are retained on every response); whether `/v1/responses/input_tokens` produces a billed line item; current price page hash and validity; whether any enforceable project hard stop exists; credential custody outside Git and conversations. Each is UNKNOWN today.

## 6. E9 plan under this contract (requires its own recorded authority; nothing here runs it)

| Fixture | Body | Count attempts | Gen attempts | Pass conditions |
|---|---|---|---|---|
| F1 | batch 1, 10 rows | ≤3 | ≤3 | valid count; admitted (or recorded rejection); Table C all pass incl. required echo and optional-safe; §6.7 parse result logged |
| F2 | batch 19, 190 rows (renderer max) | ≤3 | ≤3 | as F1 |
| F3 | byte-identical F2 | ≤3 | ≤3 | `count(F3) == count(F2)`; `cached_tokens == 0` despite identical prefix within cache lifetime; identity vector identical to F2 |
| F4 | F2 + fixed correction suffix (one normative reason code) | ≤3 | ≤3 | as F1; `count(F4) > count(F2)` recorded (not required) |

Totals: ≤12 count + ≤12 generation attempts; monotonic stop limit 7,400 s = the nominal fixed-backoff HTTP allowance 24×300 + 8×25 (server-imposed `Retry-After` waits and overhead consume it; not every maximum attempt is promised to fit). Any profile mismatch or unsafe optional value, unknown mandatory usage, count/usage inequality or cache activity fails E9 and records no baseline. E9 follows adoption of the amendment and its own E9 gate; freeze follows closure of all §12 gates. Offline-mocked, not live: over-limit rejection, count-only, count failure paths, compatibility halt (malformed count body, duplicate keys, bytes mismatch), `Retry-After` (delta, HTTP-date, malformed, over-cap, deadline-insufficient, non-finite deadline), `status: failed/incomplete`, 401/402/403 halt, unknown usage → accounting halt, mismatch → IVF, cache activity → IVF, unsafe optional values, forked-worker journal re-read, killed-writer retention of pre-dispatch bytes. E9 outputs that enter the manifest: identity baseline, per-fixture counts and usage, header set, price page hash, cost reconciliation against the account's cost records (count fee measured or still unknown).

## 7. What this contract does not do

Runner integration is Codex's (final counted-runner tests: 15 cases passing per Codex; live transport unwired; all calls fabricated; immutable `RequestPair`, `DispatchContext`, `CountReceipt`, classified `AttemptResult`; parent/child attempt protocol; mocked class/correction/admission/deadline tests passing; a `ProcessExecutor` child-halt propagation defect reported as being fixed; budget and request-record components at `adbf03d19f86f7f2d5592ae77ccb8c9b28672edf` on `research/counted-admission`) — Codex's statements, not verified here; the old source is left unchanged. Does not itself select L\* (Codex selected 272,000 prospectively; 200,000 is the superseded proposal — see the amendment file); does not authorize spending; does not select the provider finally; does not implement custody or blinding; does not measure latency or cost; does not change any inferential rule.
