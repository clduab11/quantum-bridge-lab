# Sol endpoint and cache follow-up — 2026-09-08

**Conclusion: the claim that neither provider can ever meet the literal fingerprint requirement is not established.** The earlier feasibility check inspected OpenAI Responses and Anthropic Messages. Current OpenAI Chat Completions documents a backend fingerprint field and Sol supports that endpoint. This is a possible path to investigate before changing protocol v0.4; it is not evidence that Sol actually returns a usable fingerprint, that any field never changes or disappears, or that all readiness gates can close.

Research only: no model calls, token-count calls, credentials, account inspection or provider selection. No source or protocol files changed. All sources below were retrieved on 2026-09-08.

## Fingerprint field: present in schema, optional and deprecated

The current [Chat Completions create reference](https://developers.openai.com/api/reference/resources/chat/subresources/completions/methods/create) marks response `system_fingerprint` deprecated and optional. Its documented meaning is a description of the backend configuration used by the model, intended to help observe changes that could affect determinism. The [official Python response type](https://github.com/openai/openai-python/blob/main/src/openai/types/chat/chat_completion.py) declares `system_fingerprint: Optional[str] = None`; absence/null is therefore explicitly possible. The fetched source bytes had SHA-256 `ba016e84df4d9232dfab10c9e3699096fa33ccd5faacabdf892b91bcb94ceb96`; main is a mutable source, not the pinned study SDK.

The [advanced usage guide](https://developers.openai.com/api/docs/guides/advanced-usage) also discusses the fingerprint as an aid to monitoring configuration changes. Its examples include older models and do not establish field population for Sol. Mention of `seed` in this documentation is not a requirement to send one to obtain the field, and the protocol's prohibition on sending an LLM seed remains in force. Do not silently add a seed as a workaround.

None of these sources guarantees a non-null fingerprint for `gpt-5.6-sol`, durable availability of a deprecated field, complete coverage of every serving/sampling change, or that the fingerprint is a cryptographic attestation. A constant model name, request ID, request hash or locally invented configuration hash is not a substitute for the provider's fingerprint. Absence of observed drift remains weaker than proof of stationarity, as v0.4 already acknowledges.

## Sol compatibility and the inclusive output cap

The [Sol model page](https://developers.openai.com/api/docs/models/gpt-5.6-sol) lists Chat Completions, and the [Sol migration guide](https://developers.openai.com/api/docs/guides/upgrading-to-gpt-5p6-sol.md) explicitly shows `model: gpt-5.6-sol` with the Chat request field `reasoning_effort`. This is direct API documentation, independent of Codex UI labels.

Chat's `max_completion_tokens` is the correct candidate translation of the protocol's 8192 inclusive output cap. The current [token-counting guide](https://developers.openai.com/api/docs/guides/token-counting) explains that it covers all generated output, including hidden reasoning and non-visible formatting tokens. Using deprecated `max_tokens` would be the wrong default adapter choice. Actual acceptance of `max_completion_tokens: 8192` together with the chosen complete Sol request is still an E9 matter. No effort or sampling setting is selected by this report.

Sol's migration guide restricts Chat function tools to effective reasoning `none`; the study sends no tools, so that particular restriction does not by itself disqualify its text-only request. It is not permission to assert every remaining sampling parameter works with every Sol effort. The exact model-specific temperature/top_p/default contract still needs resolution. A candidate Chat adapter would send exactly one completion (`n: 1`), no tools, no prior assistant history or server conversation linkage, no prediction input, and the unchanged literal prompt contents, with the precise role mapping documented and reviewed before use. It must preserve the existing no-replay retry, timeout, parsing and usage rules.

## Token counting does not transfer automatically between endpoints

The current [input-token counting guide](https://developers.openai.com/api/docs/guides/token-counting) describes `POST /v1/responses/input_tokens` and promises a rendered count for the matching **Responses** request format, including structural tokens. It does not establish that converting Chat messages into a Responses request yields an identical token count. The [advanced usage guide](https://developers.openai.com/api/docs/guides/advanced-usage) explains that Chat messages include role/content plus additional formatting whose accounting may change.

Therefore the strongest justified position is: a Chat endpoint may improve the fingerprint evidence, while leaving an additional endpoint-specific input-ceiling question unresolved. Do not relabel a Responses count as a verified Chat count or use the plain-text byte bound as a full request token ceiling. A future authorized, finite synthetic interface check can record actual Chat `usage.prompt_tokens` for its fixtures; observed fixtures alone do not prove the maximum over all permissible numeric histories. The model/endpoint tokenizer and wrapper bound, or another defensible conservative contract, remains required.

## Direct OpenAI evidence for explicit mode without breakpoints

The [direct OpenAI prompt-caching guide](https://developers.openai.com/api/docs/guides/prompt-caching), in its GPT-5.6-and-later explicit-mode section, states:

> When no explicit breakpoints are placed, the request does not use prompt caching or create cache writes.

That is a 17-word quotation from OpenAI's own documentation, not Azure documentation. The same page says to set `prompt_cache_options.mode` to `explicit` to select only developer-placed breakpoints; `ttl: 30m` is the supported default lifetime if any breakpoint is written. The current [Chat create schema](https://developers.openai.com/api/reference/resources/chat/subresources/completions/methods/create) directly exposes this option for GPT-5.6 and later and repeats that explicit mode without breakpoints does not use caching. Thus the no-cache **documented request semantics** are supported for a candidate direct OpenAI Chat configuration too.

This does not claim the study adapter has sent or verified that configuration, does not make a missing usage field a measured zero, and does not establish account invoice behavior. Keep separate testable assertions for request serialization, absence of breakpoint markers, no-cache usage reconciliation and full reservation of unknown attempts. There is a minor unrelated documentation discrepancy: the guide describes looking back through 50 breakpoints, while the Chat schema says 80. That does not alter the documented zero-breakpoint case; avoid presenting the broader documents as wholly identical.

## Consequence for the protocol decision

v0.4 does not prescribe Responses versus Chat Completions; it prescribes one stable model/decoding contract, actual metadata, the inclusive output cap, stateless prompts, no tools and the fixed failure/accounting rules. An endpoint choice made before freeze could satisfy the existing wording **if** an actual authorized readiness process produces adequate evidence for the fingerprint, identity, defaults, request caps, input counting and transport/accounting requirements. Endpoint schema inspection alone satisfies none of those measured gates.

A precise response to the review is: modern Responses/Messages inspection did not establish a fingerprint, while Chat Completions offers an optional deprecated candidate field whose Sol behavior is unmeasured. Preserve that uncertainty and investigate it before claiming an amendment is unavoidable. If the selected endpoint returns null/absent or the required semantics cannot be established, G-MODEL stays open; any later alternative governance/observability standard must be an explicit reviewed pre-freeze amendment rather than a silent relaxation.
