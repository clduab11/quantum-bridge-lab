# Prospective provider-contract resolution — not adopted

Codex recommendation, 2026-09-08: do not freeze the current Chat candidate under protocol v0.4, and do not turn the 272,000-token hypothesis into a verified ceiling. The engineering components can be reviewed offline while the provider contract is resolved. No scientific result has been observed, so a technical amendment can still be considered prospectively and recorded transparently.

## Preferred investigation

Investigate a Responses request with the same literal developer/user prompt texts and one explicit effort, using the documented Responses input-count endpoint to count each exact request before generation. The count endpoint includes role and formatting overhead for Responses; it does not establish a Chat count. A provider switch would require a new wire-profile hash, fixed fabricated fixtures and a separate review before any paid call. No tools, conversation linkage or previous-response ID would be supplied.

An amended admission rule could choose a fixed numerical input limit before exposure, obtain the provider's count for each distinct logical request, and reject requests above that limit before generation. Generation retries would reuse the identical counted body. This directly enforces an admission limit; it does not prove that every legal future history will fit. The existing deterministic failure/forfeit path would remain, and context-fit limitations must be explicit. Boundary fixtures would be engineering examples, not a proof over all possible histories.

If the provider cannot expose or document all effective decoding defaults and a stable fingerprint, a separate scientific amendment could define the evaluated method as the exact archived request profile plus all observable response metadata. Unobservable provider state and stationarity would remain assumptions. Observed identity changes would retain the protocol's invalidation rules. This would change the interpretation of reproducibility and must be approved by technical review and recorded before exposure; unknown defaults must never be labelled known.

## Evidence still needed

- Confirm compatibility of the exact Responses wire profile, count endpoint and selected model in the actual account, without inferring support from another model.
- Establish billing for counting, failed requests and account-specific charges. Public documentation retrieved in this phase does not establish that counting is free.
- Budget and bound count requests separately from generation. The current four-fixture/12-attempt allowance and 4,560 study transport attempts do not silently include extra network operations.
- Validate count-to-send body identity, all retry and timeout paths, fixed expiry, durable reservations and no replay with synthetic inputs before E9.
- Reconcile any change to v0.4's worst-case-context and effective-decoding requirements; record the accepted amendment, reviewer disagreements, new source hashes and exposure audit before freeze.

Until those requirements are met, this document is an investigation proposal only. It changes neither protocol v0.4 nor the chosen provider, and it authorizes no spending. A complete launcher should bind the reviewed final contract rather than embed an unverified default now. Actual API access and a numerical financial decision remain external setup requirements; protected storage and automated role selection are covered by the existing delegation.

Primary documentation checked in this phase: [token counting](https://developers.openai.com/api/docs/guides/token-counting), [Responses input count](https://developers.openai.com/api/reference/python/resources/responses/subresources/input_tokens/methods/count), [pricing](https://developers.openai.com/api/docs/pricing). The recommendation above is Codex's inference from the documented distinction between Responses counts and the unresolved Chat contract, not a provider guarantee.
