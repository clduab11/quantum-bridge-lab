# Candidate Sol Chat Completions request contract — 2026-09-08

**Status: CANDIDATE.** Prepared by Claude Science under Chris's 2026-09-08 proceed instruction ("perform all three steps"). This document proposes one complete request profile for `gpt-5.6-sol` on `POST /v1/chat/completions`. No request has been sent. No provider is selected for the study, no gate is closed, no money is authorized, protocol v0.4 (SHA-256 `0df9242fd2d0ad5d30b75ea91f498842ac68fe0df9616afd4c9c04518233eda5`) is unchanged and unfrozen. Where a contract element could not be resolved from direct primary documentation, it is recorded as a precise missing contract, not filled with a guess.

Inputs read: repository commit `b89297cfbbca1a922110ef22c9c157e3f63f7fa7` (all nine named paths plus `src/qbridge/runner.py`, `journal.py`, `proposals.py`, `custody.py`, `tests/test_runner.py`, `docs/plans/2026-09-08-offline-preflight.md`, `research/provider/VERIFICATION.md`); every SHA-256 in `research/provider/verification.json` matched the fetched snapshot. Provider documentation fetched directly from `developers.openai.com` on 2026-09-08 and hashed (table at the end; mutable pages, not immutable releases). openai-python pinned to release **v3.9.0**, commit `182af73b39998d51ad672bbd9c200ee3f4121fad`, published 2026-09-08.

## 1. Request profile (complete candidate wire payload)

This section fully specifies what would be sent. It does **not** establish verified effective decoding or verified model identity: those exist only as observed response metadata (`model`, `system_fingerprint`, `service_tier`, usage), and the sampling-parameter contract for Sol is undocumented (§3).

| Element | Value | Basis (primary source) | Resolution |
|---|---|---|---|
| Endpoint | `POST https://api.openai.com/v1/chat/completions`; global base URL, **no** `us.`/`eu.` regional base URL | Sol model page lists Chat Completions "Supported"; data-residency guide shows regional base URLs and a 10% uplift | Resolved (global) |
| `model` | `"gpt-5.6-sol"` literal; the `gpt-5.6` alias is never sent | Sol model page: "Default snapshot: `gpt-5.6-sol`"; the only listed snapshot is `gpt-5.6-sol` — no dated snapshot ID exists | Resolved; **identity caveat**: a single undated snapshot name is weaker than a dated release ID |
| `messages` | exactly two: `{"role":"developer","content":<system_v0.3.txt bytes>}`, `{"role":"user","content":<rendered user message bytes>}`; `content` is a plain string | Chat reference: developer message = "Developer-provided instructions… With o1 models and newer, developer messages replace the previous system messages"; system-message entry says to use developer for newer models | Resolved (role mapping). Prompt bytes unchanged: system SHA-256 `5165cfc3…97f7e`, template `80aa634b…44ba1` |
| `reasoning_effort` | `"medium"`, sent explicitly | Model page: "Reasoning.effort supports: none, low, medium (default), high, xhigh, and max"; migration guide: "If omitted, GPT-5.6 defaults to `medium`" | Resolved as a **supported explicit configuration** that equals the documented default; chosen on non-performance grounds (it is the documented default; no outcome informed it). Alternative efforts are not evaluated. |
| `max_completion_tokens` | `8192` | Chat reference: "An upper bound for the number of tokens that can be generated for a completion, including visible output tokens and reasoning tokens" | Resolved; inclusive cap = protocol §6.1 design value. Deprecated `max_tokens` never sent |
| `n` | `1` | Chat reference (`n`, 1..128, "Keep n as 1 to minimize costs") | Resolved |
| `stream` | `false` | Chat reference | Resolved (one body, one usage object) |
| `store` | `false` | Chat reference: "Whether or not to store the output… for use in our model distillation or evals products" | Resolved as a data-retention choice; not a statelessness proof |
| `service_tier` | `"default"` | Chat reference: default = "standard pricing and performance"; when set, response echoes the tier actually used | Resolved; response tier must equal `default` or the attempt is flagged |
| `prompt_cache_options` | `{"mode":"explicit"}`, **zero** breakpoints; `ttl` omitted | Chat reference: "Set mode to explicit to disable the implicit breakpoint"; prompt-caching guide (GPT-5.6-and-later section) states that with no explicit breakpoints the request does not use caching or create cache writes | Resolved as **documented request semantics**; realized `cached_tokens`/`cache_write_tokens` = 0 remains an E9 observation. Plain-string content makes a breakpoint structurally impossible |
| Omitted, never sent | `temperature`, `top_p`, `seed`, `tools`, `tool_choice`, `response_format`, `logprobs`, `top_logprobs`, `stop`, `prediction`, `metadata`, `user`, `safety_identifier`, `prompt_cache_key`, `prompt_cache_retention`, `verbosity`, `modalities`, `audio`, `web_search_options`, `parallel_tool_calls`, `frequency_penalty`, `presence_penalty`, `logit_bias`, `max_tokens`, `stream_options` | Protocol §6.1 (no tools, no seed, no memory, no fallback) and §7 | Enforced by `FORBIDDEN_FIELDS` at build time and by a pre-send httpx hook that compares the full serialized request (all fields, roles, prompt strings, URL) with the intended body and refuses dispatch on any difference |
| Conversation linkage | none: no assistant history, no `previous_response_id`/`conversation` (Responses-only fields anyway), each logical call is a fresh two-message request | Protocol §6.3 statelessness | Resolved |
| SDK | openai-python 3.9.0, `OpenAI(max_retries=0)`; per-call `with_options(timeout=httpx.Timeout(t, connect=min(10,t)), max_retries=0)`; `with_raw_response` to capture headers and raw body bytes | `src/openai/_constants.py`: `DEFAULT_MAX_RETRIES = 2`, `DEFAULT_TIMEOUT = httpx.Timeout(timeout=600, connect=5.0)` — both overridden | Resolved; test proves one HTTP attempt per call on HTTP 429 |
| Outer timeouts/retries | unchanged: runner owns 3 attempts, 5 s/20 s backoff, ≤300 s per attempt via its process executor, 36,000 s arm deadline | protocol §7.2–7.3; `runner.ArmRunner._logical` | Unchanged; adapter maps exceptions to the runner's `ConnectionError`/`TimeoutError`/other-exception classes |

Canonical serialized body for fixture F1 (short) is 4,931 bytes, SHA-256 `9da05de0c1516a3e…` (full hashes in `fixtures_summary.json`); the maximal renderer fixture F2 is 103,648 bytes, `7aea7dd9ff0470d0…`.

## 2. Response, error, usage and identity checks (what the adapter records before parsing)

Recorded per attempt into the durable journal (`TransportResponse.metadata`/`usage`): HTTP status; `model`; `system_fingerprint` (nullable); `id`; `created`; `service_tier`; `finish_reason`; choice count; `refusal`; whether `content` is a string; `x-request-id`, `openai-processing-ms`, `x-ratelimit-remaining-*` headers; raw body SHA-256 and length; canonical request-body SHA-256; elapsed seconds; usage categories `prompt_tokens`, `completion_tokens`, `total_tokens`, `reasoning_tokens`, `cached_tokens`, `cache_write_tokens`, prompt/completion `text_tokens`, `audio_tokens`, `image_tokens`, `accepted/rejected_prediction_tokens` — every absent category is `None` (unknown), never 0.

Findings emitted (not fatal to the run; recorded for G-MODEL/G-TRANSPORT and for the runner's IVF logic): `model_mismatch`, `system_fingerprint_absent`, `service_tier_not_default`, `choice_count_not_one`, `truncated_at_cap` (finish_reason `length`), `refusal_returned`, `completion_tokens_exceed_cap`, `reasoning_not_subset_of_completion`, `total_mismatch`, `cached_tokens_nonzero`, `cache_write_tokens_nonzero`, `*_unknown`, and always `effective_decoding_not_echoed:<effort>`.

Error mapping: HTTP 429/5xx → `TransportResponse(status, text="")` (runner retries); other 4xx → `TransportResponse(status)` (runner terminates the logical call, forfeits batch, no correction); `openai.APIConnectionError` → `ConnectionError` (retry); `openai.APITimeoutError` → `TimeoutError` (retry); anything else → ordinary exception (runner `client_error`, no retry). Refusal (`content` null, `refusal` text) is a received 2xx response with empty text → parse failure → the protocol's correction path; the refusal text is preserved in metadata.

## 3. Unknowns resolved vs. precisely missing contracts

**Resolved from primary documentation:** endpoint support; model ID and alias; documented reasoning-effort set and default; `max_completion_tokens` inclusive semantics; `n`; `store`; `service_tier` echo; explicit-mode no-breakpoint caching semantics; SDK retry/timeout defaults; response `system_fingerprint` typed `Optional[str] = None` (deprecated); usage schema including `cache_write_tokens` and `reasoning_tokens`; documented pricing rows and the ≤272K/>272K tiers; 10% data-residency uplift; documented model maxima (1,050,000 context; 922,000 max input; 128,000 max output).

**Missing — no direct primary source found (searched the model page, GPT-5.6 latest-model guide, Sol migration guide, reasoning guide, Chat reference):**

1. **Sampling parameters for `gpt-5.6-sol`.** No page states whether `temperature`/`top_p` are accepted, rejected, or what their effective values are for Sol. (The GPT-6 Astra guide explicitly says to remove them; the GPT-5.6 guide is silent.) Consequence: they are omitted; the provider-effective sampling configuration is **unknown and undocumented**, so the protocol §6.1 requirement "record the exact request parameters … A documented fixed default may be used only when its versioned semantics are recorded" is met only for `reasoning_effort`, not for sampling. This is a precise open item for G-MODEL, not something E9 can resolve (E9 can only show acceptance, not effective values).
2. **`system_fingerprint` population for Sol.** Schema-optional and deprecated; whether Sol returns a non-null value, and whether it changes, is unmeasured. If E9 returns null, the literal §6.1 "model fingerprint" requirement is unmet and the two honest outcomes remain: stop before paid exposure, or a separately reviewed pre-exposure amendment to the identity-evidence standard. Neither is chosen here.
3. **Effective decoding echo.** Chat responses do not return `reasoning_effort`; the "effective decoding" the runner compares is therefore the request value only.
4. **Endpoint-specific input-token ceiling.** The Responses `input_tokens` counting endpoint promises an exact count for the Responses format only; no Chat-format counting endpoint is documented. The gpt-5.6-sol tokenizer is not documented. No local token estimate was produced in this session (tiktoken vocabulary download is outside the sandbox allowlist, and a local estimate would not be a provider count anyway). See the budget proposal for how a financial cap can still be bounded.
5. **`verbosity` default.** Omitted; its Sol default value is undocumented on the retrieved pages. It is a style control, but it affects output length within the 8192 cap.
6. **Account facts:** billing region, service-tier project default, rate-limit tier, whether rejected/400 requests incur charges, and promotional-price expiry behavior. These are account-level, not documentation-level, facts.
7. **Credential and custody (observed setup gap):** no OpenAI credential is configured in this project (the configured credential names are GitHub, JINA_API_KEY, OpenAlex; no values are displayed or stored in any artifact). The adapter fails closed without `QBRIDGE_OPENAI_API_KEY`, a validated `AuthorityRecord` (with `scope`, `profile_sha256`, `price_valid_through_utc`, `rate_source`), a bound `SpendLedger`, a `ProtectedStore` and an explicit `HaltPolicy`.
8. **Worst-case input wording.** G-MODEL names a 200-row shortest-repr worst case; the current renderer cannot emit more than 190 rows, so no 200-row request was constructed here. That is a fixture limitation, not evidence that such a request cannot exist; see the E9 proposal §1.

## 4. Retained disagreements and things this document does not do

It does not select Sol over Fable 5.1 for the study; it completes the Sol Chat candidate that `research/PROVIDER_DECISION.md` asked for. It does not adopt v2's "stop-or-amend" wording as exhaustive, and it does not convert Codex's byte bound into a token bound. It does not claim evaluator blindness, custody, or a verified price beyond the documented promotional minimum window (at least through 2026-11-21).

## 5. Documentation sources (fetched 2026-09-08; SHA-256 of retrieved bytes)

| File | Bytes | SHA-256 |
|---|---:|---|
| `sol_model.md` (`/api/docs/models/gpt-5.6-sol.md`) | 3,945 | `6aaf0b7116c48f427f3bbcd1d3f908d140ae3bfa44ea060bec3d007678b9c5df` |
| `latest_model_gpt56.md` (`/api/docs/guides/latest-model/gpt-5.6.md`) | 18,924 | `21ba6bdb6c2b127319a5db20849fdbc06b701cb885418a8ccbcffa9c9fef317a` |
| `latest_model_sol.md` (`/api/docs/guides/latest-model.md?model=gpt-5.6` — returns the GPT-6 Astra guide) | 16,564 | `2a59b26078e001a4e4e3da10693e80ad5ee1c02cbe472afa6b682308f27b8b22` |
| `sol_migration.md` (`/api/docs/guides/upgrading-to-gpt-5p6-sol.md`) | 24,243 | `d4d2494240bc124bde81d96a9a389f3ed7122deabc4b508c18d26a3ebd20c74f` |
| `chat_create.html` (Chat Completions create reference) | 1,628,592 | `57cc9112113cbb07fecec69f818a9ec8230ab14074b5ac279a9bda8dfc36b93c` |
| `pricing.md` | 21,646 | `244b537c06fb94e4d7214ba7f076f2bd18cace4ad165d30ad5da77cbaaad36c6` |
| `prompt_caching.md` | 45,072 | `116afe3d8639c788318605d870229b178bdb8f4d7369062e13fcfc7d457d1837` |
| `token_counting.md` | 22,604 | `c60315cf603d0cdd6ec1e7dd27ff00fb1196c180db90c3a052a02d3afb5ecd05` |
| `reasoning.md` | 70,155 | `24fea701de256cde7aa544bd0aac5b387bae06d6f8e68b5b6ed168a01a6d49bd` |
| `rate_limits.md` | 20,170 | `4a10e75768a5c246a1f9ea942b7547d0e72e8d555e36d8997ddb8282107c4f35` |
| `data_residency.md` (`/api/docs/guides/your-data.md`) | 71,686 | `87e998eef3eb815414d677ed0f09c462c744bc51c46f240d2aa4b6986ec4d6fb` |
| `advanced_usage.md` | 11,061 | `83ab62ea9f48844a3a2ca9738eb7330733585bebed9bfa367b41590da398f93f` |
| SDK v3.9.0 `_constants.py` | 414 | `eeccbc82822f0e4372f42f666afd1d1e1fe80cb2ef71357018a0170ac6b9ce32` |
| SDK v3.9.0 `types/chat/chat_completion.py` | 8,723 | `ba016e84df4d9232dfab10c9e3699096fa33ccd5faacabdf892b91bcb94ceb96` (identical to the bytes Codex hashed from `main`) |
| SDK v3.9.0 `types/chat/completion_create_params.py` | 22,634 | `eceb8cbb71c845057898f185168db9280854f12121bbf3028402be7bc8e89d73` |
| SDK v3.9.0 `types/completion_usage.py` | 2,281 | `505975694e13d13a3cac7e9b2eff707ef8b125f0de91e32ccc89fc4b7c2161a2` |

Machine-readable copy: `documentation_sources_2026-09-08.json`. Implementation: `qbridge_ext/sol_chat_adapter.py` (53 offline tests pass after the 2026-09-08 code reviews, including fork-safe durable halt state and pre-send enforcement of the exact serialized request; see the gate execution record and proposal §7). Unimplemented and stated as such: the whole-study launcher, crash-recovery driver, masked export, freeze manifest writer, and live acceptance of any request.
