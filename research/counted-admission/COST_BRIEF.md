# Preflight and study costs

Updated 2026-09-09. Codex Astra has [approved a $32 all-in allocation for one E9](E9_BUDGET_DECISION.md) under Chris's delegation. The API account, count-request fee bound and mandatory charges remain unverified, so live spending release is pending. No billing settings have been changed.

## Who receives payment?

The proposed experimental model is OpenAI's `gpt-5.6-sol`, accessed through the API. Charges would go to the OpenAI organization whose project credentials the launcher uses. API billing is separate from a ChatGPT subscription. See [OpenAI's billing guidance](https://help.openai.com/en/articles/9039756-billing-settings-in-chatgpt-vs-platform).

Claude Opus 5 is the research and implementation assistant in Claude Science. Its existing Max plan and local compute were observed. They support engineering work, but no reviewed payment arrangement covers the selected OpenAI API calls through that allowance. Private account details are excluded from this research record.

The qubit simulation and classical optimizers run locally in the planned study. There is no quantum-hardware provider to pay and no planned cloud-compute rental. Local electricity and storage still have costs. Optional hosted execution, research tools or additional subscriptions would need separate estimates.

## What the API numbers mean

The current [Sol model page](https://developers.openai.com/api/docs/models/gpt-5.6-sol) lists $4 per million ordinary input tokens and $20 per million output tokens. Input over 272,000 tokens changes the full-request rates. The [pricing table](https://developers.openai.com/api/docs/pricing) also distinguishes cached input and cache writes. These public prices are not proof of this account's terms or of count-request fees.

At the proposed admission limit of 272,000 input tokens and output cap of 8,192, one generation attempt costs at most $1.25184 under the ordinary-input, no-cache, stated-rate assumptions:

`(272000 × 4 + 8192 × 20) / 1000000 = 1.25184 USD`

| Path | Generation attempts | Generation-only arithmetic, rounded upward |
| --- | ---: | ---: |
| Four E9 fixtures, one successful attempt each | 4 | $5.01 |
| E9 with the full retry allowance | 12 | $15.03 |
| Both study stages, scheduled calls only | 760 | $951.40 |
| Both stages, all allowed corrections and retries | 4,560 | $5,708.40 |

These are conditional maxima for the specified paths, not forecasts. The scheduled path excludes extra corrections and retries. Shorter inputs or outputs reduce generation charges; no observed counts or expected bill are available yet. At most 12 E9 count attempts and 4,560 study count attempts are additional. Their maximum fee must cover failed and rejected requests too. A count result is not a bill for the counting service.

The exact combined generation-only maximum is $5,723.41248 including E9. Counting fees, any applicable account charges and taxes remain outside that amount. Unknown fees prevent a verified numeric total. The [original calculations](BUDGET.md) and scenarios remain unchanged. Cache activity is a validity failure under the proposed profile, but any resulting charge still has to be recorded; halting later requests cannot undo a charge already incurred.

## Current preflight allocation

The initial $25 proposal was never approved. The current allocation is **$32 total incremental cost**, including taxes and mandatory fees, for the four fixed E9 fixtures and their existing retry allowance. It excludes a full study, automatic rerun or subscription purchase. [The allocation record](e9-budget-allocation.json) is deliberately distinct from executable provider authority. It approves an amount without claiming the current launcher or unresolved billing terms are ready.

Conservative reservations cover the highest applicable input category, including a possible cache write even though cache activity would fail E9. At the recorded rates, that is $1.523840 per generation attempt and $18.286080 for 12. If the maximum per count attempt were $1.088, the full allowance would total $31.342080, or $31.35 rounded upward, leaving just $0.65792 for mandatory extras. The count fee remains unverified. The [revision 2 review](e9-launcher-review-rev2/README.md) confirms the new arithmetic but requires the provider reservation correction on every retry.

The count limit is checked after the count request, and successful billing observations cannot establish failure or rejection fees. With no extras or taxes, the full allowance fits $32 only if the verified count-attempt maximum is at most $1.142826666…; applicable charges reduce that headroom. An insufficient full-allowance budget is rejected before the current CLI dispatches, rather than beginning a knowingly underfunded run. The earlier generation-only study calculations above remain conditional; they are not a conservative all-category spending authorization.

A client limit bounds further reservations under the verified billing assumptions. It is not an unconditional guarantee about a provider's final invoice. The provider records known overruns without clipping them and halts subsequent calls; unresolved charges keep their reservations.

## Funding and controls

For a prepaid API account, money leaves the payment method when credits are purchased; usage then consumes that balance. Monthly billing follows the account's terms. Current prepaid guidance lists a $5 minimum purchase, enables auto-reload by default during setup, and warns that exhaustion is not an instantaneous cutoff. Purchased credits expire after a year and are non-refundable. An approved experiment budget and a credit purchase are separate decisions. See [prepaid billing](https://help.openai.com/en/articles/8264644-how-can-i-set-up-prepaid-billing).

Current [spend-limit documentation](https://developers.openai.com/api/docs/guides/spend-limits) supports both alerts and enforced organization/project limits. Alerts alone do not stop requests. Hard-limit enforcement can lag, so it supplements the launcher's pre-dispatch reservations. Check the actual project configuration; do not assume an older soft-budget control is enforced. Prefer a dedicated experiment project and explicit limits, with automatic recharges off for a bounded preflight unless separately approved.

Project limits are monthly and cover all traffic in that project; launcher authority is per run. Existing and concurrent project usage must be included when choosing the account limit.

The [original Claude handoff](../../docs/handoffs/2026-09-08-claude-opus5-e9-launcher.md) remains historical. The newer delegation permits Codex to resolve billing and approve the preflight budget; the [allocation decision](E9_BUDGET_DECISION.md) records what has been completed and what still prevents spending. Claude is correcting the launcher offline. The chosen OpenAI organization must be accessible before its account terms can be checked.
