# Claude Opus 5 handoff: bounded E9 launcher and billing proposal

You are Claude Opus 5 working in the existing Claude Science project `quantum-bridge-lab`. Finish the bounded model-preflight launcher and prepare a costed E9 spending proposal. Implement and test the software; do not stop at a design or checklist. I will bring your completed package back to Codex for independent review before any live preflight.

## Starting point

Repository: https://github.com/clduab11/quantum-bridge-lab

Use immutable engineering commit `a8c3e1e83c28db80642ab0123dd1fbf4d9ff5bc2`. It is on `research/counted-admission`, in draft PR #5 stacked on `research/execution-readiness` / PR #4. Verify the actual branch/PR metadata and identify later changes before using them. Fetch a complete checkout or artifact set at that commit; do not infer current code from old chat summaries. Raw files are available beneath:

`https://raw.githubusercontent.com/clduab11/quantum-bridge-lab/a8c3e1e83c28db80642ab0123dd1fbf4d9ff5bc2/`

Read these first, following their relevant implementation references:

- `research/counted-admission/STATUS.md`, `VERIFICATION.md`, `integrated-verification.json` and `REVIEW_FOLLOWUP.md`.
- `research/counted-admission/provider-candidate/README.md`, `COMPATIBILITY_AND_LIMITATIONS.md`, `HASH_MANIFEST.json`, provider sources and tests.
- `src/qbridge/counted_runner.py`, `runner.py`, `request_records.py`, `journal.py` and their tests.
- `research/counted-admission/e9-inputs/manifest.json` and its README and eight request bodies.
- `research/counted-admission/BUDGET.md`, `scenarios.json`, and the proposed A1 revision 2, candidate v0.5 and request/accounting contract under `research/counted-admission/claude-science/`.
- Operative `specification/ai_quantum_control_protocol_v0.4.md`, the amendment registry, and `research/execution-preparation/operational-setup.json`.

Codex reports 607 offline tests passed on that commit: 289 core, 53 earlier Chat-candidate, 152 original counted-reference and 113 new Responses-provider cases. Treat that as recorded evidence until you run the relevant checks yourself. Preserve original source packages and logs. The separate 150-pass/2-failure compatibility probe reflects old tuple assertions versus JSON-stable list tags; do not revert the fix or claim those two assertions passed. Use the existing locked SDK review environment; record your actual Python and package versions.

## Scope and authority

You are the implementation/review model. The experimental model candidate remains exactly `gpt-5.6-sol`; do not substitute Opus 5, a routing alias or another model. Protocol v0.4 is unchanged and unfrozen. A1 and candidate v0.5 remain proposed. All experimental count/generation calls and study-objective candidate evaluations are still zero.

This work order authorizes offline implementation, mock tests, public-documentation research and preparation of a financial proposal. Do not run E9, evaluate the study objective, create a real comparison mapping, issue live financial authority, adopt A1, freeze or launch the study. Do not purchase credits, enter payment details, enable auto-recharge, change account billing/limits, or send support messages. If account evidence is unavailable, finish the independent work and list the exact missing facts. Never request API keys or payment details in chat or include them in artifacts.

## Implement the launcher

1. Provide an executable CLI with an offline dry-run as the default. A mock run must exercise the complete E9 orchestration and produce a report without loading a real key or dispatching network requests. Document separate commands for offline verification and a future gated live run.
2. Load and verify the four committed fixtures in their declared order. Bind all eight hashes, the builder/source hashes and the full request profile. Keep developer/user text identical between each count and generation body; keep F2/F3 byte-identical. Do not change prompts, effort, admission, output cap or fixtures based on observations or to fit a budget.
3. Integrate the reviewed single-attempt provider with durable journals, raw request/response retention and monetary reservations. Use separate E9 records outside Git; do not consume study slots or create a study arm merely to reuse its machinery. The provider owns one HTTP attempt; the orchestrator owns retries and deadlines. Keep SDK retries disabled and prevent duplicate dispatch on reopen or interruption.
4. Enforce at most 12 count and 12 generation attempts in total, including retries, across four fixtures under one 7,400-second monotonic stop limit. Apply the specified 300-second attempt limits, retry rules and full server minimum waits. Overhead consumes the deadline; there is no promise every attempt will fit. A count failure or admission rejection cannot dispatch generation. Retain the 272,000-token admission limit and 8,192-token output cap.
5. Define acceptance from the reviewed A1/E9 requirements and document a traceable mapping to code. Distinguish provisional identity observations from an accepted E9 baseline. Passing one request or receiving HTTP 200 is insufficient. Preserve usage/profile/identity failures and incomplete results. Record actual F2/F3 timing; claim no cache-window coverage that was not demonstrated. Do not weaken existing halt precedence or the treatment of unknown charges.
6. Require valid adoption evidence, complete billing evidence, an explicit E9-only numeric authority and the expected environment/profile before a live dispatch. Proposals and synthetic authorities must fail the live gate. Record unresolved requirements as failures, not defaults. Keep spending-limit errors distinct from retryable throughput errors; verify current error semantics.
7. Add meaningful mock and real-worker regression tests for refusal with missing/expired/forged evidence, shared monetary and attempt caps, deadline/Retry-After exhaustion, crash/reopen behavior, strict fixture identity, usage/identity anomalies and baseline acceptance. Never weaken strict tests to fit your environment. If you find a defect in a dependency component, provide a minimal separate patch with reproducing evidence and its effect on existing tests.

## Prepare the billing decision

Recheck current primary documentation and the installed SDK. Use Context7 and Exa if available, but resolve cached or contradictory claims against official sources and actual pinned behavior. Record source URLs, retrieval dates, relevant evidence hashes and validity assumptions. More quantum literature is unnecessary unless a specific implementation decision depends on it.

Start with **$25 USD as a proposed E9-only client limit**, not an approval or a promise of sufficiency. Produce a reproducible calculation showing whether all applicable fees fit. If they do not, recommend a different amount with reasons; do not reduce the experiment or invent free counting. Keep the full-study authorization absent.

At the prior 4/20 USD-per-million ordinary-input/output assumptions, one maximum-size generation is `(272000*4 + 8192*20)/1000000 = $1.25184`. E9's 12-generation allowance is $15.02208; both study stages' 4,560-generation allowance is $5,708.3904. Those figures exclude count fees and extras and are not expected bills. The full scheduled path has 760 generation calls; corrections and retries raise the maximum. E9 adds at most 12 count calls; the study adds at most 4,560. Do not multiply the retry allowance twice.

Verify all token categories, reasoning/output treatment, cache settings, long-context thresholds, rate expiry, regional/account charges and taxes as applicable. Establish a count-attempt fee ceiling that covers failed and rejected calls. Missing evidence stays unknown: a returned token count, a mock zero fee or an arbitrary reserve cannot establish billing. Separate public prices from actual account terms and actual user approval.

Explain who is paid and when: OpenAI API organization billing for the proposed study model; Claude Science's separate research-chat arrangement; local simulation costs; optional hosted services only if proposed. ChatGPT subscriptions are not API credit. Document whether the relevant account uses prepaid credits or monthly billing, if this can be established without changing it.

Check https://developers.openai.com/api/docs/guides/spend-limits and https://help.openai.com/en/articles/8264644-how-can-i-set-up-prepaid-billing . Current docs distinguish alerts from enforced project/organization limits and warn that enforcement can lag. Prepaid depletion can also lag. Do not repeat the outdated claim that every project budget is only an alert. Recommend a dedicated project, appropriate account controls and the launcher's pre-dispatch checks; explain the remaining invoice risk. Prepare setup instructions for me, without applying them or funding the account.

## Return a reviewable package, then stop

Save the launcher, tests, minimal patches, exact commands and dependency records as project artifacts with a SHA-256 manifest. Include an implementation report, E9 acceptance specification, offline dry-run report, failed/passed test evidence, billing-source register and itemized financial proposal. Include an unapproved authority template that cannot accidentally dispatch live requests; clearly separate fabricated test records from actual evidence.

End with a short decision sheet: what works, what is still missing, proposed E9 USD limit, costs included/excluded, remaining account facts, and the exact approval needed after Codex review. Link every deliverable with its artifact ID and hash. Retain review disagreements. Update Project Context only if a specific documented project requirement calls for it.

Do not continue into live execution or another autonomous phase. I will tell Codex when you are finished so it can inspect this conversation with Playwright, verify the artifacts and review the code and financial proposal.
