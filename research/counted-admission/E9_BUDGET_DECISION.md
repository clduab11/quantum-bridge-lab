# E9 budget allocation: US$32 approved, spending release pending

Decision date: 2026-09-09. Approver: Codex Astra, acting under Chris Dukes's explicit instruction to independently review the corrected package, resolve billing and approve the finalized preflight budget.

**Approve an allocation of US$32.00 for the total incremental cost of one bounded E9 preflight, including taxes and mandatory fees.** This fixes the amount available for the preflight. It does not certify unresolved provider fees, approve the current launcher or issue executable live spending authority. The [second independent review](e9-launcher-review-rev2/README.md) still identifies execution defects, and the API account cannot yet be inspected because its browser session is signed out.

The allocation is for the four existing fixed fixtures, with at most 12 count attempts and 12 generation attempts against the unchanged `gpt-5.6-sol` profile. Failed, rejected and uncertain requests count against it. It does not fund the full study, an automatic rerun, another model, new cloud services or a subscription purchase. Existing subscription costs and local equipment are outside this incremental experiment allocation. No additional funds are approved by this record.

The [machine-readable allocation](e9-budget-allocation.json) deliberately has a different schema from the provider's `AuthorityRecord`. It cannot substitute for the missing billing evidence or enable a live request.

## What the amount can cover

At the recorded short-context prices, conservative generation reservations use the highest applicable input category, $5 per million tokens, and $20 per million output tokens:

`12 × (272000 × 5 + 8192 × 20) / 1000000 = $18.286080`

The count-attempt fee is still unknown. If it were bounded by the illustrative $1.088 per attempt, including failed and rejected requests, the 12-count/12-generation scenario would total **$31.342080**, or **$31.35** rounded upward to cents, before any extra charges. That leaves only $0.65792 within the allocation for applicable taxes and fees. This scenario is not a forecast or verified invoice ceiling. The [Sol pricing page](https://developers.openai.com/api/docs/models/gpt-5.6-sol) establishes token-category rates; it does not establish the missing count fee.

With no tax or other mandatory charge, $32 covers the full conservative allowance only if the verified maximum for each count attempt is at most **$1.142826666…**. Mandatory charges reduce that headroom. For example, only where the account's actual tax rules support applying a single tax rate `t` to API usage and a fixed tax-inclusive extra `E`, the available usage budget is `(32 - E) / (1 + t)`. Do not assume `t = 0`, invent `E`, or use that formula for a different tax treatment.

The 272,000-token generation limit is checked after counting. It therefore cannot establish the fee for a count request rejected for excessive size. A successful count/generation pair would show charges for those observations only, not general failure or rejection terms. The pinned SDK, Context7, Exa and current official [counting documentation](https://developers.openai.com/api/docs/guides/token-counting) did not establish a comprehensive count-fee bound in this review.

## Claude Science compute and the API bill

Claude Science is being used for research, coding and local execution. Its settings showed an existing Max plan and local compute; no connected cloud provider or model endpoint established funding for the selected Sol/count route. Account usage details are retained privately rather than published here. Anthropic describes Claude Science as a research environment that can run local analyses and connect to the user's compute resources. See [Claude Science documentation](https://support.claude.com/en/articles/16563838-get-started-with-claude-science).

That capacity supports the ongoing engineering work. The reviewed provider, however, explicitly calls OpenAI's Responses and input-count endpoints. No reviewed billing arrangement shows those calls drawing from Claude Science's subscription or usage credits. The experimental model and endpoint contract have not been changed to obtain different billing.

For OpenAI prepaid accounts, credits are purchased before usage and consumed as requests are billed. The current official article lists a $5 minimum purchase, auto-reload enabled by default during setup, one-year expiry and nonrefundable purchased credits. It warns that depleted-credit enforcement can lag. These are public terms, not evidence of this account's balance, tax treatment or configuration. See [prepaid billing](https://help.openai.com/en/articles/8264644-how-can-i-set-up-prepaid-billing), checked 2026-09-09.

## Release conditions

Before this allocation can be used for E9:

1. Independently verify the remaining deadline, restart and approval-expiry corrections, the gate-only fixture checks, and the required conservative reservation implementation.
2. Inspect the chosen API organization/project: billing mode, balance or payment arrangement, tax and mandatory charges, monthly limits, existing spend and other project traffic. The OpenAI Platform tab was opened in Edge; Chris was asked to sign in and select the paying organization. No credentials or payment details were requested in chat.
3. Establish an applicable maximum fee for all permitted count attempts, including failed, rejected and uncertain outcomes, plus the model-category prices and their validity. Account controls cannot turn an unknown fee into verified evidence.
4. Show that the resulting maximum and mandatory charges fit the $32 total allocation. If they do not, retain the allocation without dispatch; do not change scientific inputs to fit or spend above it.
5. Complete the prospective scientific adoption requirement and create a run-specific provider authority bound to the approved code, inputs, rates, account evidence, duration and expiry. Keep the full-study authority absent.

Project hard limits apply monthly to all traffic in that project, with possible enforcement delay. They supplement the client's reservations. Neither a prepaid balance nor a monthly cap is an instantaneous invoice guarantee. See [spend limits](https://developers.openai.com/api/docs/guides/spend-limits).

No credits were purchased, account settings changed, or experimental requests sent for this decision. The budget amount is approved; billing resolution and live spending release remain incomplete. This distinction follows the existing provider evidence requirements, not a request for Chris to repeat the approval already delegated.
