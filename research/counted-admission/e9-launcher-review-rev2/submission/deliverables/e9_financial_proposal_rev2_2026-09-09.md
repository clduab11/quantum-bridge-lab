# E9-only spending proposal — revision 2, UNAPPROVED

**Status: proposal for review. No money is authorized by this document. Neither USD 25 nor USD 32 is approved.** No credits were purchased, no billing setting was changed, no spending authority was issued, no count or generation request was made, and no probe of the account's charging behaviour is proposed or authorized here. Every figure below is arithmetic over published rates. None of it is an invoice, a measurement, or a prediction.

Scope: the bounded E9 model preflight only — four fixed fixtures, at most 12 count attempts and at most 12 generation attempts against `gpt-5.6-sol`. The full-study figures appear only in a separated reference section and are not part of this request.

This revision supersedes `e9_financial_proposal_2026-09-09.md` (revision 1), which is preserved unchanged. Revision 1's claims are retracted below by name.

---

## 1. Retractions from revision 1

Codex's review identified three unsupported claims; an independent verification pass found a fourth, in this revision's own first draft. All four are withdrawn.

| Revision 1 said | Why it was wrong | Revision 2 says |
|---|---|---|
| "$32 covers every case" | The count-attempt figure it rests on is an **assumption**, not a bound. If a rejected or failed count attempt is billed differently, or if any category applies that the published tables do not cover, $32 covers nothing in particular. | $32 is the cent-rounded ceiling of **one identified scenario** (D). It bounds nothing outside the four scenarios below. |
| "the smallest round ceiling that cannot be reached by the maximum number of attempts the software will permit" | Unreachability was asserted from an assumed per-count charge. The software cannot make a ceiling unreachable; it can only refuse to reserve beyond it, and its refusals are conditional on the recorded rates being the rates actually applied. | The software refuses to dispatch when the recorded arithmetic says the remaining headroom is insufficient. That is a client-side refusal, not an unreachable ceiling. |
| Nine specific prepaid-billing facts attributed to the help-centre article (credit expiry, refundability, consumption order, depletion behaviour, automatic replenishment) | The article could not be read: direct fetch is refused and the web search returned no page text. Those statements were written from recollection as if sourced. | **Withdrawn in full.** Section 4 now records the timing of payment as unresolved. |
| "Amount the evidence supports: $32.00" | No evidence establishes a total. The count-request charging question is unresolved, so no scenario can be selected as the applicable one. | The evidence supports **four scenarios and no selection among them.** $25 and $32 are both retained as unapproved scenario figures. |

A further correction to revision 1's presentation: it claimed the test environment "matched Codex's recorded environment exactly." That claim is withdrawn. Section 7 records the actual versions.

---

## 2. What is actually established, and what is not

**Established from published documentation** (sources and hashes in `e9_billing_source_register_rev2_2026-09-09.json`):

- `gpt-5.6-sol` text rates: input $4.00, cached input $0.40, cache writes $5.00, output $20.00 per 1M tokens. Cache writes are 1.25× the uncached input rate.
- Prompts above 272,000 input tokens are priced at 2× input and 1.5× output **for the full request**.
- A hard spend limit returns HTTP 429 with `organization_spend_limit_exceeded` or `project_spend_limit_exceeded`, and **enforcement is not instantaneous** — recorded spend can exceed the configured amount.
- Prepaid credits exist for an organization, and `credit_balance_exhausted` means that prepaid balance is depleted.

**Not established, and not inferable:**

1. **Whether a request to the token-count endpoint is billed at all.** The pricing page states the Responses API family is not priced separately and that tokens are billed at model rates. It does not say whether tokens submitted to the count subresource are billed tokens. This establishes neither a zero fee nor a positive one.
2. **Whether a failed or rejected request is billed, and if so on what basis.** No source addresses this.
3. **There is no established maximum for a count attempt.** The $1.088 figure used below is `272,000 × $4/1M` — the cost *if* a count request were billed exactly like ordinary generation input. It is an assumption chosen for arithmetic, not a ceiling. In particular: **the admission limit L\* = 272,000 is checked *after* a count returns, so it cannot bound the cost of a count request that is itself rejected for being too large.** A rejected count's billable size is unknown.
4. **The mechanics of prepaid API billing**, and therefore when money leaves the account. See section 4.
5. **Every account fact**: billing mode, credit balance, whether any automatic credit replenishment is configured, usage tier and assigned monthly limit, whether any hard spend limit is currently configured, month-to-date spend, other traffic in the same project, tax treatment, contracting entity.

**What a successful E9 would establish about charges:** the charges for the specific count and generation calls that ran, as they appear in that account's usage records. Nothing more. It would not establish a per-call fee schedule, would not establish the treatment of failed or rejected calls, and would not license the study's arithmetic.

---

## 3. The four scenarios

Exact rational arithmetic; per-attempt figures at the admission limit and the 8,192-token output cap.

| Per attempt | USD |
|---|---|
| Generation, input at the uncached rate + full output cap ("optimistic") | 1.251840 |
| Generation, input at the worst applicable category (cache writes) + full output cap ("conservative") | 1.523840 |
| Count attempt, **assumed** to be billed as ordinary input | 1.088000 |

| E9 scenario (12 attempts of each class) | Exact | Cent ceiling |
|---|---|---|
| A — count unbilled, no cache writes | 15.022080 | **15.03** |
| B — count unbilled, worst-case cache writes | 18.286080 | **18.29** |
| C — count billed as input, no cache writes | 28.078080 | **28.08** |
| D — count billed as input, worst-case cache writes | 31.342080 | **31.35** |

$25 covers A and B. It falls **$3.07808 short of C** and **$6.34208 short of D**. $32 exceeds D by $0.65792 but is not thereby a bound on anything: change the count assumption and every C/D figure moves.

Note on the conservative column: E9 **fails** on any cache activity. Reserving for the cache-write rate is a solvency measure, not permission for it to happen — the money is spent before the failure is detected, which is why the reservation must cover it. See finding 5 in `e9_review_response_rev2.md`.

---

## 4. Who receives payment, and when money leaves the account

**Payee:** OpenAI, through the organization's API billing settings.

**When money leaves the account: unresolved, and I am not able to answer it from evidence.** This was one of the questions put to me, and the honest position is that it is unanswered:

- The only retrieved statement about the mechanism is that prepaid credits exist for an organization and that `credit_balance_exhausted` means that balance is depleted (`error-codes.md`, hashed).
- The help-centre article that documents prepaid billing — the one named in the work order — could not be read. Direct fetch returns HTTP 403 to automated clients, and a web search confirmed only that the article exists and is current (page age 30 July 2026), returning no page text. Its contents are therefore not asserted anywhere in this proposal.
- Consequently: whether this organization is on prepaid credits or on periodic billing, whether credits expire, whether they are refundable, in what order credit types are consumed, what happens to in-flight usage when a balance empties, and whether any automatic replenishment can top a balance up are all **unrecorded**. A first revision of this document asserted several of those points; they had no source and have been withdrawn.

Two consequences worth stating plainly. First, **an amount of credit is not demonstrably a spending cap** — that would require knowing the depletion and replenishment behaviour, which is unknown. Second, one timing fact *is* established, for a different control: hard spend-limit **enforcement is not instantaneous**, so recorded spend can exceed the configured amount (`spend-limits.md`, hashed).

The launcher's own client-side ledger refuses to reserve past its recorded ceiling before each attempt. That is a second line of defence, not a guarantee about the invoice.

**To answer the question, read from the account** (costs nothing, no request): the billing mode, the current balance, whether any automatic replenishment is configured and with what threshold and amount, the usage tier and its assigned monthly limit, any configured hard spend limit, month-to-date spend, other traffic in the intended E9 project, and the tax treatment and contracting entity.

---

## 5. Included and excluded

**Included in this scope:** `gpt-5.6-sol` tokens for at most 12 generation attempts and at most 12 count attempts, including retries, failures and rejected attempts; attempts whose dispatch outcome is unknown, for which the accounting retains the full reservation rather than assuming zero.

**Excluded:** the full study; taxes and any jurisdiction-specific charge; any other model, endpoint or tool; a re-run after a failed E9 (a failed E9 forfeits its spend and produces no baseline); non-provider costs; and any charge arising from a mechanism not in the published tables.

---

## 6. The approval this proposal asks for — and its limits

> Record the account facts in section 2 item 4, then decide a numeric E9-only limit and configure a hard spend limit at that figure on a project used only for E9.

Two properties of that control that must be understood before it is relied on:

- **A project hard spend limit is monthly and applies to all traffic in that project.** It is not a per-run budget. If anything else runs in the same project during the same calendar month, that spend counts against the same limit; if month-to-date spend already exists, the remaining headroom is less than the configured figure. This is why the gate now requires month-to-date spend and concurrent project traffic to be recorded before a live run.
- **Enforcement is not instantaneous.** Recorded spend can exceed the configured amount.

If you prefer to hold $25, that is coherent with a stated consequence: under scenario C or D the run halts part-way with a recorded refusal, the spend to that point is lost, and E9 must be re-authorized and re-run. It is a safe failure, not a free one. This proposal does not recommend a figure, because selecting one requires resolving item 1 of section 2, and that resolution is not available from documentation.

---

## 7. Actual environment (not a matching-environment claim)

Recorded from the environment these results were produced in, on macOS 26.5.2 (arm64), 2026-09-09:

```
python 3.11.16
openai 3.9.0          httpx 0.28.1         pydantic 2.12.0
numpy 2.4.6           scipy 1.17.1         cma 4.4.4
pytest 9.1.1          ruff 0.16.6          pip-audit 2.10.1
```

`openai==3.9.0` and `httpx==0.28.1` are the versions pinned by `counted_responses_provider.authority` and checked by `provider._versions_ok`; any other pair refuses to dispatch. `pip-audit` is required by `qbridge.preflight`.

This is **not** a claim that the environment matches Codex's. Codex's own record for this project names a local interpreter of 3.11.15 against this sandbox's 3.11.16, and the frozen study environment is undefined. Any other package version differences between the two environments are unknown to me and were not compared.

---

## 8. Full study — reference only, NOT part of this request

Same rates, same admission limit, 4,560 attempts of each class:

| Scenario | Exact | Cent ceiling |
|---|---|---|
| A — count unbilled, no cache writes | 5708.390400 | **5708.40** |
| B — count unbilled, worst-case cache writes | 6948.710400 | **6948.72** |
| C — count billed as input, no cache writes | 10669.670400 | **10669.68** |
| D — count billed as input, worst-case cache writes | 11909.990400 | **11910.00** |

These figures supersede the illustrative $5,321.08 in `research/counted-admission/BUDGET.md` **as arithmetic only** — that figure used the superseded L\* = 200,000 and illustrative $5/$20 rates. Nothing here authorizes any study spending. The study also remains blocked on amendment adoption, protocol freeze and a successful E9, and its C and D columns rest on the same unestablished count-charging assumption as E9's.
