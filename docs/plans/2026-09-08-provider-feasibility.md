# Provider feasibility and publication plan

## Goal and authority

Chris's 2026-09-08 request to push all updates, add a plain-language README and continue the work authorizes repository publication and the next bounded offline milestone. Existing delegation covers technical research and pre-freeze corrections. No paid API call, spending ceiling, freeze or study execution is inferred from this request.

Publish the reviewed design and offline implementation through PRs #1 and #2, preserving commit history and original research artifacts. Continue on a separate provider-feasibility branch so the completed milestone stays distinguishable from new work.

## Scope and checks

- [x] Inspect local and remote Git state, existing review evidence and public-file inventory; independently review the revised README and resolve its wording findings.
- [x] Preserve the invalid local loose ref `research/offline-preflight 2` outside Git refs, then verify successful fetch and connectivity. Its contents referenced the existing design commit; no research data or valid branch was deleted.
- [x] Use Context7 and Exa to check at most two API candidates against current primary documentation; preserve explicit unknowns, pricing categories and protocol constraints.
- [x] Submit the concrete evidence to a fresh Claude Science project conversation through the existing Edge tab. Request documentation review and arithmetic only, with no protocol or Project Context edits.
- [ ] Reconcile the saved Claude review, preserving factual corrections and disagreements. Identify whether an explicit prospective protocol amendment is required before a provider can meet the existing contract.
- [ ] Integrate and independently verify the small offline budget calculator described in `2026-09-08-budget-planning.md`. All monetary scenarios remain conditional, with no provider defaults or execution authorization.
- [ ] Record new source hashes, test evidence and limits; preserve historical preflight reports as records of their original commit rather than rewriting them to fit later files.
- [ ] Push the new branch and synchronize the current status in Linear and Claude Science with immutable source references.

No provider SDK or new dependency is needed for this milestone. No study objective or real model adapter is added. Missing billing categories and unverified tokenizer bounds remain open requirements.
