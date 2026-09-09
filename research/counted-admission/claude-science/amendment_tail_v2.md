
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
