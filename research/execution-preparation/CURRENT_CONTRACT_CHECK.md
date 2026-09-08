# Current Sol Chat contract check — 2026-09-08

**Result: Sol is a documented candidate, but a complete execution-ready contract has not been established.** This bounded check resolves request structure, output-cap semantics and Chat usage fields. It does not resolve model-specific effective sampling, an adequate returned fingerprint, or the protocol's tokenizer-derived full-input ceiling. Those are precise open requirements, not evidence that no compliant provider can exist. No credentials, account metadata, generation or token-count API calls were accessed. Protocol v0.4 and repository files were not changed.

## Supported evidence and candidate choices

The direct [model page](https://developers.openai.com/api/docs/models/gpt-5.6-sol) identifies both model ID and current snapshot as `gpt-5.6-sol`, supports Chat Completions, and publishes 1,050,000 context, **922,000 maximum input**, and 128,000 maximum output tokens. The `gpt-5.6` family alias routes to Sol but should not replace the explicit candidate ID. This verifies documentation, not account entitlement or actual response identity. The page supports `none`, `low`, `medium`, `high`, `xhigh`, and `max`; medium is the published effort default. A preselected medium effort is a defensible candidate choice without using objective outcomes, not a measured optimum.

Use the model-specific [GPT-5.6 guide](https://developers.openai.com/api/docs/guides/latest-model?model=gpt-5.6) and [Sol migration guide](https://developers.openai.com/api/docs/guides/upgrading-to-gpt-5p6-sol.md). The unqualified latest-model page currently describes GPT-6 Astra. Astra's sampling restrictions cannot silently be transferred to Sol. Neither checked Sol guide supplied an explicit temperature/top_p support/default matrix.

Proposed wire skeleton, **not approved to send** and incomplete pending the decoding disposition:

```json
{
  "model": "gpt-5.6-sol",
  "messages": [
    {"role": "developer", "content": "EXACT system_v0.3.txt content"},
    {"role": "user", "content": "EXACT rendered user_template_v0.3.txt content"}
  ],
  "reasoning_effort": "medium",
  "max_completion_tokens": 8192,
  "n": 1,
  "stream": false,
  "store": false,
  "service_tier": "default",
  "prompt_cache_options": {"mode": "explicit", "ttl": "30m"}
}
```

The placeholder strings above are descriptions, never literal study inputs. The [official developer-message type](https://github.com/openai/openai-python/blob/main/src/openai/types/chat/chat_completion_developer_message_param.py) directs o1 and newer models to use developer messages for what earlier APIs called system instructions. Mapping the existing system-prompt file to that role preserves its text; record and review this mapping before use.

Omit tools, function definitions, search, prediction, seed, assistant history, server conversation links, output schemas, response-format enforcement, and cache breakpoints. These are study design choices; adding them would introduce behavior beyond the fixed text-only proposer. A normal text response leaves the existing parser and malformed-output rules operative. The [Chat reference](https://developers.openai.com/api/reference/resources/chat/subresources/completions/methods/create) supports one choice, nonstreamed requests, explicit storage/tier fields, and documents no-tool behavior when tools are absent. The complete combined Sol request remains untested.

The [token-counting guide](https://developers.openai.com/api/docs/guides/token-counting) states that `max_completion_tokens` limits all generated tokens, including hidden reasoning and formatting. Thus 8192 is inclusive, not 8192 visible JSON tokens. The direct [cache guide](https://developers.openai.com/api/docs/guides/prompt-caching) documents explicit mode with zero breakpoints as avoiding both reads and writes. This is a documented request contract, not observed invoice evidence; `ttl: 30m` does not imply a write when there are no breakpoints.

## Exact open questions

1. **Effective sampling.** The generic Chat reference exposes temperature/top_p but does not establish a Sol-specific compatibility/default contract. This check found no source permitting a fabricated numeric default, nor evidence that omission closes v0.4 §6.1. If explicit settings are chosen, document their semantics and preflight acceptance; if relying on a fixed default, obtain versioned documentation. Do not treat Astra guidance, a generic SDK field, or an example response as Sol's contract. Also resolve any effective verbosity/penalty settings relevant to the selected configuration instead of assuming all omissions mean zero.
2. **Identity and fingerprint.** The Chat schema makes `system_fingerprint` optional/deprecated. The [official response type](https://github.com/openai/openai-python/blob/main/src/openai/types/chat/chat_completion.py) still declares it nullable. Its description concerns backend configuration, not cryptographic attestation. Actual Sol population and sufficient semantics are unmeasured. A snapshot heading cannot substitute for the protocol's per-call metadata. Null/absent metadata keeps the corresponding gate open; it must not become an invented fingerprint. A constant observed value is not proof of stationarity.
3. **Tokenizer-derived input ceiling.** `/v1/responses/input_tokens` counts the rendered Responses input, including structural tokens. No checked source promises that converting Chat messages yields identical counts. Local numeric byte bounds and finitely observed Chat `usage.prompt_tokens` are not a worst-case proof. The documented 922,000 model maximum is a possible very conservative accepted-request planning constraint, **not** the required tokenizer-derived proof that every legal prompt fits, not evidence of how rejected oversized attempts are billed, and not authority to send one. Do not close G-MODEL with this number alone.
4. **Account, rate and transport realization.** Public prices do not establish the account's region, tier, invoice categories, entitlement, rate limit or SDK version. All must be concrete before a spending cap is represented as complete.

## Response, billing and transport implementation requirements

Capture original HTTP response bytes, status, headers/request ID, response model, fingerprint, actual service tier, choice count, finish reason, message content/refusal and complete usage before parsing. Preserve unknown fields. The [official usage type](https://github.com/openai/openai-python/blob/main/src/openai/types/completion_usage.py) provides Chat `prompt_tokens`, `completion_tokens`, `total_tokens`; `prompt_tokens_details` can include nullable `cache_write_tokens` and `cached_tokens`, while `completion_tokens_details` can include nullable reasoning and prediction categories. Missing categories are unknown, not measured zeros. Keep reasoning inside inclusive completion billing, and reject inconsistent category arithmetic rather than normalize it silently.

Context7's `/openai/openai-python` query corroborated the official [SDK README](https://github.com/openai/openai-python/blob/main/README.md): default retries include more statuses than v0.4 permits. Set `max_retries=0`; retain the runner's identical-request retry policy, fixed 5/20-second waits, three-attempt limit, outer 300-second attempt and 36,000-second arm deadlines. Success `_request_id` and failed `APIStatusError.request_id` support logging. HTTP-layer cancellation is not proof of server cancellation/refund. Reserve the full attempt ceiling when usage is unavailable. Pin SDK/transport versions and validate synthetic HTTP fixtures separately.

The model page currently prices ordinary input/output at $4/$20 per million up to 272,000 input tokens, with full-request multipliers of 2x input and 1.5x output above that threshold. It specifies cache writes at 1.25x ordinary input and the promotion through at least 2026-11-21. Reverify actual applicable rates and account adjustments before a decision; a future post-promotion price is not established. A model-maximum scenario belongs in sensitivity planning, not an asserted likely study bill.

## Evidence scope and provenance

Read the existing provider decision, endpoint/provider evidence and protocol §§6.1, 7.2, 8.3 and 12–13. Used Exa for **2 focused searches, 10 requested results** (duplicates and a community post are not independent evidence); full-page fetches and direct OpenAI Docs MCP reads supported seven distinct first-party guide/reference pages. Context7: one library resolution, two focused documentation queries (SDK transport, Sol sampling). The sampling query did not answer the needed compatibility/default matrix. Four official SDK source files were read directly from mutable main, without installing them. Chat reference Markdown retrieval returned 404, so its live HTML and SDK sources were checked instead.

SDK source SHA-256 on retrieval:

- `chat_completion.py`: `ba016e84df4d9232dfab10c9e3699096fa33ccd5faacabdf892b91bcb94ceb96`
- `completion_usage.py`: `505975694e13d13a3cac7e9b2eff707ef8b125f0de91e32ccc89fc4b7c2161a2`
- `chat_completion_developer_message_param.py`: `8caf6b4852b94979f4c403b588e74addad1f6efb7559860988e5f7a86a36d788`
- `chat_completion_system_message_param.py`: `ce5bbeef8c5cdbf0a17250182d153ac97350266a7d142739b0ede146b79d87bb`

These hashes identify retrieved source bytes, not a pinned or tested installed SDK. **No readiness gate, E9 result, study result, provider selection or freeze is claimed.** Root and Claude Science should resolve the exact open questions before dependent action, or record a prospective, independently reviewed change with its inferential limitation explicit.
