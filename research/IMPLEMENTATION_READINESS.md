# Offline implementation readiness — 2026-09-08

Current phase: permitted offline implementation and analytic/synthetic preflight. This status supersedes the implementation-phase status in the historical governance-v2/design-review snapshot; its governance rules still apply. Protocol v0.4 is unchanged and not frozen. No study objective evaluation or experimental model call has occurred. Chris's 2026-09-08 instruction to continue the repo is recorded in docs/plans/2026-09-08-offline-preflight.md as authority for this work.

Context7 preflight resolved /cma-es/pycma and /numpy/numpy, then queried manual ask/tell and SeedSequence child generators. Retrieved source examples came from the official pycma development notebooks and NumPy main documentation; those branch examples are not claimed to be exact installed-release documentation. We check actual pinned release behavior through narrowly scoped synthetic characterization tests.

Actual installed environment observed: CPython 3.11.15, numpy 2.4.6, scipy 1.17.1, cma 4.4.4. uv.lock pins dependency resolutions. The initial pytest 8.4.2 audit finding PYSEC-2026-1845 was corrected by upgrading pytest to 9.1.1; the fixed audit found no known vulnerabilities in audited dependencies. **174 integrated tests and all eight offline check groups passed; Ruff 0.16.6 passed.** See [verification evidence](preflight/VERIFICATION.md) and [machine-readable report](preflight/report.json), including environment limitations and the local project's advisory-audit exclusion.

Primary documentation: https://github.com/cma-es/pycma/blob/development/notebooks/notebook-usecases-basics.ipynb ; https://github.com/numpy/numpy/blob/main/doc/source/reference/random/parallel.rst . Use the installed versions' code/signatures and tests for the operational conclusions.

Scope of this phase: numerical component identities and mapping; strict proposer/parser and literal prompts; durable failure accounting and synthetic transport; locked all-pairs inference and custody checks. No provider adapter or study-run command is enabled. Actual model identity/settings, token and monetary ceilings, paid-call authority and full-run manifest remain pending.

The accompanying VIABILITY_ASSESSMENT_2026-09-08.md records the initial targeted Exa/arXiv review with five shared source IDs. Claude Science challenged it in a fresh project conversation; its corrected v3 is preserved under sources/original. PURSUIT_DECISION.md records the resulting recommendation, explicit disagreements and prospective outcome decision map. The offline engineering milestone has value; the paid two-stage experiment is a separate cost, stationarity and decision-relevance choice. There is no current commercial evidence.

## What remains before freeze

All ten complete readiness gates remain open until the required evidence and actual decisions are assembled in a full manifest. Partial engineering evidence must not be presented as a completed freeze gate.

| Gate | Evidence in this implementation | Remaining requirement |
| --- | --- | --- |
| G-ENV | Locked resolutions and actual package-version capture; dependency audit | Full environment manifest and exact-release documentation/behavior reconciliation |
| G-CMA | Installed-release synthetic ask/tell characterization and effective option dump | Bind the demonstrated configuration and seed records into the full manifest |
| G-MODEL | Strict schema, literal prompts and fabricated-history tests | Actual provider identity/settings, tokenizer/context ceiling, stable metadata and authorized E9 |
| G-TRANSPORT | Mocked retry/accounting/identity-change tests and local process cancellation | Provider adapter, actual timeout/usage semantics, all billing categories and E9 |
| G-CUSTODY | Synthetic private mapping, commit/seal verification and pair-selection tests | Named actual operator, analyst and custody process owner |
| G-LOCK | Locked all-pairs analysis with strict boundaries, missingness and invalidity | Freeze hashes of all analysis dependencies and invocation |
| G-EXPOSURE | Engineering logs explicitly record analytic/synthetic inputs | Full pre-freeze exposure audit covering every participating workflow |
| G-STORAGE | Local private journal and synthetic custody permission checks | Actual protected locations for study mapping, logs and transcripts |
| G-RUNTIME | Component-only timing and bounded local cancellation fixtures | Provider latency/window estimate and full scheduled launcher; study runtime remains unmeasured |
| G-COST | Protocol-derived call ceilings and explicit unknown usage accounting | Concrete token/billing limits, monetary ceiling and authority covering both stages |

No real study mapping was created. Independent evaluator blinding is not claimed. Local cancellation cannot undo provider work or charges for a request already accepted remotely. The current shared-journal identity tracking requires a future whole-study coordinator to use that common history across blocks.
