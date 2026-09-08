# Independent integration review — 2026-09-08

Codex reviewed Claude Science's candidate components using direct source inspection and synthetic HTTP responses. No provider request, token-count request, or study-objective evaluation was performed. These are candidate implementation defects, not scientific results.

## Corrections requested

1. The initial schedule was AI, CMA, RS instead of protocol v0.4 section 8.1's RS, CMA, AI. The revised coordinator uses the normative order.
2. The initial ledger clipped a known token charge to the reserved amount. The initial reproduction recorded USD 0.008202 when the fabricated usage implied USD 0.029. The revised ledger records the known amount without clipping and halts after an overrun.
3. Bind and validate actual spending authority, rates, input limit, scope, purpose, attempt limits, profile, and price validity. Missing applicable usage is unknown, not zero. Authority validation must also cover direct construction and state changes.
4. Preserve original request/response/error bytes and enforce response findings. A hash by itself is not retained raw evidence.
5. A repeated-call test using the real ProcessExecutor showed a reported model-mismatch halt disappearing at the next worker process. Durable halt and fingerprint state is required.
6. A mocked HTTP authentication layer changed the allowed reasoning-effort field and user text; the adapter still dispatched. Compare the complete actual request with the intended body before network dispatch, not only a subset of fields afterwards.

The JSON files alongside this record preserve exact reviewed source hashes and observed synthetic results. `reproduce_process_and_wire.py` is the discovery harness for findings 5–6; it targets the recorded rejected source snapshot and is not the final acceptance suite. It imports an explicit candidate source path and uses only httpx.MockTransport. Final corrected-source verification will be recorded separately.

## Document review

The review rejected treating 272,000 tokens (a pricing threshold) as a verified Chat input ceiling, calling the 922,000-token scenario unconditional, treating historical rates as guaranteed future prices, and requesting user approval of a speculative cap as though the protocol gate were satisfied. Exact Decimal subtotals replace inconsistently rounded displays. Price validity must be checked at every dispatch. The renderer's 190-row limit does not itself settle the protocol's 200-row boundary requirement.

The documented cache-write replacement rate is supported by the official caching guide; the review did not require double-counting ordinary input plus that replacement rate. Missing billing categories and account facts still remain unknown.

## Scope

The coordinator is a scheduling/accounting component. A complete study launcher, recovery driver, masked export and committed-manifest freeze sequence remain separate work. Candidate wire parameters do not establish effective decoding, stable model identity or universal token bounds. Protocol v0.4 is unchanged. No readiness gate, experimental result or live spending authorization follows from these code corrections.
