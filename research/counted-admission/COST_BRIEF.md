# Preflight and study costs

Prepared 2026-09-08 local date / 2026-09-09 UTC. This is a planning note, not spending authority. No billing account was inspected or changed for this note.

## Who receives payment?

The proposed experimental model is OpenAI's `gpt-5.6-sol`, accessed through the API. Charges would go to the OpenAI organization whose project credentials the launcher uses. API billing is separate from a ChatGPT subscription. See [OpenAI's billing guidance](https://help.openai.com/en/articles/9039756-billing-settings-in-chatgpt-vs-platform).

Claude Opus 5 is the requested research and implementation assistant in Claude Science. Selecting it for that conversation does not replace the experimental model. Claude Science's own subscription or metered usage is a separate development expense; its payment arrangement has not been checked here.

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

## Proposed decision

Use **$25 USD for E9 only as a proposed client spending limit**, pending a complete calculation, Codex review and Chris's explicit approval. This amount is neither approved nor demonstrated sufficient. Claude must show whether verified generation costs, count fees and applicable extras fit within it. If they do not, return a revised proposal; do not alter fixtures or invent zero fees. Leave the full-study budget unapproved until E9 evidence and both-stage costs can be reviewed.

Claude subsequently proposed **$32**, but the [independent launcher review](e9-launcher-review/README.md) found that it still assumes an unverified $1.088 maximum per count attempt. Under that assumption and the documented cache-write rate, 12 attempts of each class total $31.34208, or $31.35 rounded upward. This is a conditional scenario, not evidence that $32 covers all charges. The count limit is checked after the count request, and two successful billing observations cannot establish failure or rejection fees. Neither amount is approved. The provider's generation reservation also needs a correction before it covers the applicable cache-write category.

A client limit bounds further reservations under the verified billing assumptions. It is not an unconditional guarantee about a provider's final invoice. The provider records known overruns without clipping them and halts subsequent calls; unresolved charges keep their reservations.

## Funding and controls

For a prepaid API account, money leaves the payment method when credits are purchased; usage then consumes that balance. Monthly billing follows the account's terms. Current prepaid guidance lists a $5 minimum purchase, enables auto-reload by default during setup, and warns that exhaustion is not an instantaneous cutoff. Purchased credits expire after a year and are non-refundable. An approved experiment budget and a credit purchase are separate decisions. See [prepaid billing](https://help.openai.com/en/articles/8264644-how-can-i-set-up-prepaid-billing).

Current [spend-limit documentation](https://developers.openai.com/api/docs/guides/spend-limits) supports both alerts and enforced organization/project limits. Alerts alone do not stop requests. Hard-limit enforcement can lag, so it supplements the launcher's pre-dispatch reservations. Check the actual project configuration; do not assume an older soft-budget control is enforced. Prefer a dedicated experiment project and explicit limits, with automatic recharges off for a bounded preflight unless separately approved.

Project limits are monthly and cover all traffic in that project; launcher authority is per run. Existing and concurrent project usage must be included when choosing the account limit.

The [Claude handoff](../../docs/handoffs/2026-09-08-claude-opus5-e9-launcher.md) requests working offline code and a billing proposal. It authorizes no credit purchase, payment-setting change or experimental API request. Chris will return the completed package for Codex review.
