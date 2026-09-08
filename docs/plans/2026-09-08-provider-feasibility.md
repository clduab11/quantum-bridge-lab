# Provider feasibility and publication plan

## Goal and authority

Chris's 2026-09-08 request to push all updates, add a plain-language README and continue the work authorizes repository publication and the next bounded offline milestone. Existing delegation covers technical research and pre-freeze corrections. No paid API call, spending ceiling, freeze or study execution is inferred from this request.

Publish the reviewed design and offline implementation through PRs #1 and #2, preserving commit history and original research artifacts. Continue on a separate provider-feasibility branch so the completed milestone stays distinguishable from new work.

## Scope and checks

- [x] Inspect local and remote Git state, existing review evidence and public-file inventory; independently review the revised README and resolve its wording findings.
- [x] Preserve the invalid local loose ref `research/offline-preflight 2` outside Git refs, then verify successful fetch and connectivity. Its contents referenced the existing design commit; no research data or valid branch was deleted.
- [x] Use Context7 and Exa to check at most two API candidates against current primary documentation; preserve explicit unknowns, pricing categories and protocol constraints.
- [x] Submit the concrete evidence to a fresh Claude Science project conversation through the existing Edge tab. Request documentation review and arithmetic only, with no protocol or Project Context edits.
- [x] Reconcile the saved Claude review, preserving factual corrections and disagreements. An amendment is not yet shown to be unavoidable: investigate the optional deprecated Chat Completions fingerprint before drawing that conclusion. No provider route is execution-ready.
- [x] Integrate and independently verify the small offline budget calculator described in `2026-09-08-budget-planning.md`. All monetary scenarios remain conditional, with no provider defaults or execution authorization.
- [x] Record new source hashes, test evidence and limits; preserve historical preflight reports as records of their original commit rather than rewriting them to fit later files.
- [x] Push the new branch and synchronize the current status in Linear and Claude Science with immutable source references.

No provider SDK or new dependency is needed for this milestone. No study objective or real model adapter is added. Missing billing categories and unverified tokenizer bounds remain open requirements.

## Completion record — 2026-09-08

PRs [#1](https://github.com/clduab11/quantum-bridge-lab/pull/1), [#2](https://github.com/clduab11/quantum-bridge-lab/pull/2) and [#3](https://github.com/clduab11/quantum-bridge-lab/pull/3) are merged into `main`. The PR #3 merge is `17ca96d5fcc963684a15f417851ec5366e39f15b`; its tree equals reviewed content commit `d2e9021e6d46f2f457ddab73e37429671bf7d5ec`. GitHub readback confirmed the merge, successful CodeRabbit and Kilo review checks, and no inline review comments. The new README explains the research question, practical motivation, limitations and local setup in plain language.

The integrated verification remains **233 tests passed**, including 59 budget tests, with Ruff lint/format and the unchanged lockfile check passed; see [the verification record](../../research/provider/VERIFICATION.md). This completion note does not change the tested source.

Linear's project, ADV-36 and existing pursuit/readiness document now reference the same immutable `d2e9021` provider decision, endpoint evidence and verification record. Readback confirmed the merged milestone, corrected review v2, next endpoint-contract task and unfrozen status in all three; the prior pursuit decision text was preserved. ADV-36 remains In Progress.

Claude Science acknowledged the final handoff in the existing **Provider Feasibility Review 2026-09-08** conversation as Codex-reported status. It did not independently fetch or verify the final links, rerun tests, or save an acknowledgment artifact. No Project Context update was requested. This is a status acknowledgment, not an additional independent verification of repository contents. The original v1/v2 review files and their prior byte-verification evidence remain preserved.

The next bounded task is to document the candidate Sol Chat Completions request, identity, tokenizer and billing contract. No provider is selected, no amendment is established as unavoidable, and no paid preflight, freeze or study execution occurred. All ten complete readiness gates remain open.
