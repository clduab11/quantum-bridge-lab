# Offline budget planning

`python -m qbridge.budget` calculates conditional cost ceilings for the fixed two-stage protocol. It makes no network calls and cannot authorize spending or enforce a live account limit. All five inputs are required; absent prices never become zero.

## Arithmetic example

The following values are deliberately fabricated for checking the calculator. They are not provider prices, a tokenizer-derived input ceiling or an approved budget:

```sh
PYTHONPATH=src uv run --frozen python -m qbridge.budget \
  --input-token-ceiling 1000 \
  --input-usd-per-million 2 \
  --output-usd-per-million 3 \
  --extra-usd-reserve 0.001 \
  --max-e9-attempts 2
```

The JSON output separates 760 scheduled calls, the maximum 4,560 attempts including corrections and retries, two additional E9 attempts, and the reserve. For this example, combined ceilings rounded **up** to cents are $20.26 on the scheduled path and $121.25 on the retry/correction path. Neither is an expected bill. The 24,000 allotted objective slots are counted but not priced.

Input rates must cover the conservative effective cost of each input token, including any applicable cache costs. Output rates must cover all billed generation within the fixed 8,192-token cap; hidden reasoning must not be counted twice or omitted. Additional costs require a sufficient explicit reserve. E9 uses the same per-attempt assumptions, and its supplied count is already an attempt limit. Explicit zero excludes a category from that scenario; it does not prove the category is free or absent.

The output always states `tokenizer_cap_verified: false`, `billing_complete: false` and `spending_authorized: false`. A full budget needs external evidence and an actual authorization record. Arithmetic tool limits are documented in the [implementation plan](../docs/plans/2026-09-08-budget-planning.md).

## Research inputs

[Provider feasibility](PROVIDER_FEASIBILITY.md) records current primary-source prices, candidate contracts and unresolved identity/billing issues. [The prompt byte bound](PROMPT_BYTE_BOUND.md) supplies a conditional limit on the literal text size. Bytes are not provider tokens; a plausible-looking synthetic history is not a proof of a worst-case token ceiling. These documents support the next decision and do not close G-MODEL, G-TRANSPORT or G-COST.
