# Offline implementation readiness — 2026-09-08

Current phase: permitted offline implementation and analytic/synthetic preflight. Protocol v0.4 is unchanged and not frozen. No study objective evaluation or experimental model call has occurred. Chris's 2026-09-08 instruction to continue the repo is recorded in docs/plans/2026-09-08-offline-preflight.md as authority for this work.

Context7 preflight resolved /cma-es/pycma and /numpy/numpy, then queried manual ask/tell and SeedSequence child generators. Retrieved source examples came from the official pycma development notebooks and NumPy main documentation; those branch examples are not claimed to be exact installed-release documentation. We check actual pinned release behavior through narrowly scoped synthetic characterization tests.

Actual installed environment observed: CPython 3.11.15, numpy 2.4.6, scipy 1.17.1, cma 4.4.4. uv.lock pins dependency resolutions. The initial pytest 8.4.2 audit finding PYSEC-2026-1845 was corrected by upgrading pytest to 9.1.1; the fixed dependency audit is recorded separately. Full component verification is in progress.

Primary documentation: https://github.com/cma-es/pycma/blob/development/notebooks/notebook-usecases-basics.ipynb ; https://github.com/numpy/numpy/blob/main/doc/source/reference/random/parallel.rst . Use the installed versions' code/signatures and tests for the operational conclusions.

Scope of this phase: numerical component identities and mapping; strict proposer/parser and literal prompts; durable failure accounting and synthetic transport; locked all-pairs inference and custody checks. No provider adapter or study-run command is enabled. Actual model identity/settings, token and monetary ceilings, paid-call authority and full-run manifest remain pending.

The accompanying VIABILITY_ASSESSMENT_2026-09-08.md records a new targeted Exa/arXiv review with five shared source IDs. Its recommendation is bounded research value, limited standalone novelty and no current commercial evidence. Claude Science will challenge that judgment in a fresh project conversation.
