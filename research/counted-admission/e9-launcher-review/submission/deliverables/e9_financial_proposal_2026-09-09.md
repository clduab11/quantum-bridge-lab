# E9-only spending proposal — UNAPPROVED

**Status: proposal for review. No money is authorized by this document. No credits were purchased, no billing setting was changed, no spending authority was issued, and no API request was made.** Every figure below is arithmetic over published rates, not an invoice and not a measurement.

Scope: the bounded E9 model preflight only — four fixed fixtures, at most 12 count attempts and at most 12 generation attempts against `gpt-5.6-sol`. **The full-study budget is deliberately excluded and appears only in a clearly separated reference section at the end.**

---

## 1. Headline recommendation

| | |
|---|---|
| Amount you proposed | **USD 25.00** |
| Amount the evidence supports | **USD 32.00** |
| Reason for the difference | $25 is sufficient **only if** requests to the token-count endpoint are not billed. Public documentation does not establish that. If a count request is billed as ordinary input at the model rate, the enforced worst case is **$28.08**, rising to **$31.34** if the provider also charges cache-write rates before E9 detects the cache activity and fails. |

$32 is not a prediction of what E9 will cost. It is the smallest round ceiling that cannot be reached by the maximum number of attempts the software will permit, under the least favourable charging assumption consistent with the retrieved documentation. The most likely actual spend is materially lower, because the four fixtures are far smaller than the admission limit and a clean E9 uses only 4 attempts of each class.

**Plain-language version.** We are asking to set a hard spending cap on a small test run. The test can, in the worst case, make 24 paid requests. We know exactly what the model charges. We do *not* know whether the "how many tokens is this?" pre-check request is itself charged. If it is free, $25 is plenty. If it is charged like a normal request, $25 runs out before the test finishes and the run stops part-way, wasting it. $32 covers every case we can construct from the published prices, with about 66 cents to spare.

---

## 2. Itemization

Verified rates for `gpt-5.6-sol`, short context (input ≤ 272,000 tokens), USD per 1M tokens — source S2/S3, retrieved 2026-09-09:

| Category | Rate |
|---|---|
| Input | $4.00 |
| Cached input | $0.40 |
| Cache write | $5.00 (= 1.25 × uncached input) |
| Output | $20.00 |

Enforced E9 profile: admission limit `L* = 272,000` input tokens, `max_output_tokens = 8,192`, ≤ 12 count attempts, ≤ 12 generation attempts.

### Per attempt, at the admission limit

| Line item | Arithmetic | USD |
|---|---|---|
| Generation input | 272,000 × $4 / 1M | 1.08800 |
| Generation output (full cap) | 8,192 × $20 / 1M | 0.16384 |
| **Generation attempt, no cache activity** | | **1.25184** |
| Generation input if billed as cache writes | 272,000 × $5 / 1M | 1.36000 |
| **Generation attempt, worst-case cache writes** | + output | **1.52384** |
| Count attempt — lower bracket (not billed) | assumption, unverified | 0.00000 |
| Count attempt — upper bracket (billed as ordinary input) | 272,000 × $4 / 1M | 1.08800 |

`1.25184` is not only arithmetic: it is the exact value `contract.reservation_for_generation(272000, rates)` returns, asserted in `test_count_at_exactly_the_admission_limit_is_admitted`. The software reserves that amount before each generation attempt and refuses the attempt if the reservation would breach the ceiling.

### Full E9 allowance (12 attempts of each class)

| Scenario | Count endpoint | Cache writes | Ceiling needed |
|---|---|---|---|
| A | not billed | none | **$15.03** |
| B | not billed | worst case | **$18.29** |
| C | billed as input | none | **$28.08** |
| D | billed as input | worst case | **$31.35** |

$25 covers A and B. It does not cover C or D — it falls **$3.08 short of C** and would fund about 9 of 12 attempt pairs under D before the ledger halts.

---

## 3. Who receives payment, and when money leaves the account

**Payee.** OpenAI, as the API provider. The documentation directs credit purchases and billing changes to the organization's billing settings at `platform.openai.com/settings/organization/billing` (source S4). The contracting legal entity and its invoicing address are **not stated in any source retrieved** and are an account fact.

**Timing — two mechanisms exist and it is unresolved which applies to this account.**

1. *Prepaid credits.* Source S4 documents a `credit_balance_exhausted` error meaning "prepaid credit balance is depleted" and instructs adding credits to restore access. Under this mechanism **money leaves the account when credits are purchased, before any request runs**, and E9 usage draws that balance down.
2. *Monthly billing.* Source S1 describes spend controls in terms of tracking *monthly* API costs, and source S6 documents OpenAI-assigned *monthly* usage limits. Under this mechanism **usage accrues during the period and is charged afterwards**.

The help-centre article on prepaid billing that the work order names was **not retrievable** (HTTP 403 from automated-client protection, on a plain request and one retry with standard content negotiation; the refusal page is retained as evidence). No browser impersonation, mirror or proxy was attempted, so nothing about prepaid mechanics is asserted from it.

**A hard spend limit is not a hard guarantee.** Source S1 states that enforcement is not instantaneous and recorded spend can slightly exceed the configured amount. A configured $32 limit is therefore a strong control, not a contractual maximum.

---

## 4. What the amount includes

- `gpt-5.6-sol` token charges for **up to 12 generation attempts**, counting retried and failed attempts that still returned usage.
- Whatever the provider charges for **up to 12 count attempts**, including failed and admission-rejected ones.
- Charges for attempts whose outcome is unknown. The reviewed accounting treats an unresolved settlement as retaining the **full** reservation rather than assuming zero, so a dispatch of uncertain outcome consumes ceiling exactly as a successful one does.

## 5. What the amount excludes

- **The full study.** Separate; see section 8.
- **Taxes.** No source retrieved states any tax, VAT or invoicing term.
- Any other model, any tool call, storage, container or hosted-tool charge.
- Any charge arising from a repeat of E9 after a failure. A failed E9 forfeits its spend; a second attempt needs its own authority.
- Non-provider costs: Claude Science usage, Codex review, engineering time.
- Charges after the promotional-pricing date. Source S2 states current pricing is available *at least* through 2026-11-21; rates after that date are unknown and the authority record's `price_valid_through_utc` should not be set past it.

---

## 6. What remains unknown — and is therefore blocking

The launcher's gate treats every one of these as a **failure**, not a default. It will refuse a live dispatch until each is resolved with retained, hashed evidence.

1. **Whether the token-count endpoint is billed at all.** Source S3 states the Responses API family is "not priced separately" and that tokens are billed at model rates; source S5 describes the count endpoint's purpose as estimating costs before making API calls. Neither says whether tokens submitted *to the count subresource* are billed tokens. This establishes **neither a zero fee nor a positive fee**, and an explicit zero is as much an assumption as the $1.088 upper bracket.
2. **Whether a failed or rejected request incurs any charge.** No retrieved source addresses this.
3. **Account billing mode** — prepaid credits or monthly invoicing.
4. **Current credit balance** (if prepaid) and **usage tier** with its assigned monthly limit.
5. **Whether any hard spend limit is presently configured** on the organization or the project.
6. **Tax treatment and the contracting entity.**

Items 1 and 2 are answerable from a single low-cost observation: send **one** minimal count request and **one** minimal generation request and read the resulting line items in the account's usage or billing export. That is itself a paid live action and is **not** part of this proposal — it would need its own small authority. Items 3–6 are readable from the account without spending anything.

---

## 7. The approval that is actually needed

After Codex's review, the specific decision is:

> Set a hard **project-level** spend limit of **USD 32.00** for the project that holds the E9 API key, record the account facts in items 3–6 above, and sign a numeric E9-only authorization record naming that same figure.

Three properties make this safer than a bare limit:

- The limit should be **project-level, not organization-level**, so a breach cannot interrupt unrelated organization traffic (source S1).
- The launcher's ledger enforces the same figure independently, in exact rational arithmetic, before each attempt — so the provider's non-instantaneous enforcement is backed by a client-side stop.
- The launcher additionally refuses to retry the four documented billing rejections, so a limit breach halts the run instead of consuming the remaining attempt allowance against a condition retrying cannot fix.

**If you prefer to hold the line at $25**, that is a defensible choice with a stated consequence: under scenario C or D the run halts part-way with a recorded `monetary_ceiling_reached`, the spend to that point is lost, and E9 must be re-authorized and re-run. It is a safe failure — the ledger refuses the attempt rather than overspending — but it is a wasted one.

---

## 8. Full study — reference only, NOT part of this request

Shown separately, at the same rates and the same admission limit, for 4,560 attempts of each class:

| Scenario | Ceiling |
|---|---|
| Count not billed, no cache writes | $5,708.39 |
| Count not billed, worst-case cache writes | $6,948.71 |
| Count billed as input, no cache writes | $10,669.67 |
| Count billed as input, worst-case cache writes | $11,909.99 |

These figures supersede the illustrative $5,321.08 in `research/counted-admission/BUDGET.md` **as arithmetic only** — that figure used the superseded `L* = 200,000` and illustrative $5/$20 rates. Nothing here authorizes any study spending, and the study also remains blocked on amendment adoption, protocol freeze and a successful E9.
