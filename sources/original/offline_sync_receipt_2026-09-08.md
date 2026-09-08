# Offline milestone synchronization receipt — 2026-09-08

**Scope of this receipt:** artifact synchronization only. Claude Science fetched exact bytes from an immutable GitHub commit, verified the stated SHA-256 digests, and saved the original bytes as project artifacts. No code execution, tests, model preflight, study-objective evaluation, provider call, new decision, or change to protocol v0.4 or Project Context occurred in this session. Engineering results stated below are Codex's, as recorded in the fetched documents; they were not independently re-run here.

## Source

- Repository: `clduab11/quantum-bridge-lab`
- Commit: `7273921111e3152543b150d959c2bc2ec09a5fad` (committer date 2026-09-08T18:59:33Z; subject "Verify offline preflight and record the pursuit decision") — confirmed via GitHub API
- Draft PR #2: open, draft, `research/offline-preflight` → `research/protocol-hardening` (stacked on PR #1), head = the commit above — confirmed via GitHub API
- Fetch path: `raw.githubusercontent.com/clduab11/quantum-bridge-lab/7273921111e3152543b150d959c2bc2ec09a5fad/<path>`, HTTP 200 for all three files
- Linear: ADV-36 and the pursuit document/project were updated by Codex with the same commit, phase and five shared source IDs (stated by Codex; not independently checked here — no Linear connector was used)

## Verified files (original bytes saved unmodified)

| Repository path | Saved project artifact | Bytes | SHA-256 (recomputed = stated) |
|---|---|---|---|
| `research/PURSUIT_DECISION.md` | `pursuit_decision_reconciled_2026-09-08.md` | 6,535 | `b7c4b22d9de90d3ab7f849111b77d3305c0cfa7e58f7b00394431677a9b8f11c` ✔ |
| `research/IMPLEMENTATION_READINESS.md` | `offline_implementation_readiness_2026-09-08.md` | 5,001 | `ab116adc0ba16ca7a10c58d23c73226aee2381297fcbb66d7a8795222a28ce8e` ✔ |
| `research/preflight/VERIFICATION.md` | `offline_verification_2026-09-08.md` | 4,919 | `50226e54f1e1ed9e6abf5532cc64a16f2c6988b5dbc0952ead20a39f886bd6e3` ✔ |

Cross-reference preserved: the reconciled decision cites Claude Science's review v3 as `sources/original/pursuit_decision_review_2026-09-08_v3.md`, SHA-256 `7b0a23ca9d7231f40c942ebe8504865e1a6bbbc649fab493f7f979fa513ad8ca`, artifact `7d5ee2ca-029f-48c8-b49f-29d7e07090da` version `e447c368`. That matches the v3 saved in this project; v3 is retained unchanged and is not superseded by this receipt.

Note: `research/IMPLEMENTATION_READINESS.md` at this commit (SHA-256 `ab116adc…`) supersedes the earlier version read at commit `f1fb6bd7` (SHA-256 `faf3cdb8…`) that the review v3 provenance table cites; the review's citation remains correct for the commit it names.

## Actual scope of the published milestone (as recorded by Codex)

- Phase: permitted offline implementation and analytic/synthetic preflight. Protocol v0.4 unchanged and NOT FROZEN (SHA-256 `0df9242f…3eda5`).
- Codex reports 174 integrated tests passed, preflight groups E1–E8 passed, Ruff 0.16.6 lint/format passed; pinned environment Python 3.11.15, NumPy 2.4.6, SciPy 1.17.1, pycma 4.4.4, pytest 9.1.1, pip-audit 2.10.1; final run in a fresh temporary environment from the same unchanged lockfile.
- No study-objective evaluation of any control candidate; no experimental model call; no real provider adapter; no whole-study launcher; no real study mapping; no independent evaluator blinding claimed.
- Component arithmetic/parser timing reported (0.0064 s per 100 repetitions, imports excluded) is explicitly **not** study-objective, optimizer-performance or full-run timing.

## Reconciled decision — status of agreements and disagreements

The reconciled decision records: continue through the offline engineering milestone; decide **separately** whether the fully costed two-stage experiment earns further investment; no demonstrated LLM advantage, no publication novelty for the exact design, no commercial proposition. It includes a prospective 3 × 3 pre-exposure decision map and the strict-boundary decision-rule arithmetic (P(both Supports) ≈ 0.173 at p = 0.70, 0.647 at p = 0.80; exclusion via q = P(D > −log₁₀ 2)).

**Disagreements Codex explicitly retains against the Claude Science review (not consensus; recorded as such):**

1. Codex does **not** adopt an unconditional prediction that the paid study will most likely be inconclusive — the per-block effect distribution is unknown.
2. Codex does **not** accept that the bounded literature search proves the exact quantum-control configuration has already been studied; the review's novelty language is to be read within that limit.
3. Codex does **not** adopt the review's unmeasured "seconds to minutes on any laptop" objective-runtime characterization; 6.0 × 10⁶ segment propagations is a protocol-derived upper count, not a measurement, and the 76,000 history-row figure is the complete-valid-history scheduled path that forfeits can reduce.

Claude Science's position on each is as stated in review v3 §1–§4 and §9; neither party's position is altered by this receipt.

## Pending gates (all ten remain open per `IMPLEMENTATION_READINESS.md`)

| Gate | Remaining requirement |
|---|---|
| G-ENV | Full environment manifest; exact-release documentation/behavior reconciliation |
| G-CMA | Bind demonstrated configuration and seed records into the full manifest |
| G-MODEL | Actual provider identity/settings, tokenizer/context ceiling, stable metadata, authorized E9 |
| G-TRANSPORT | Provider adapter, actual timeout/usage semantics, all billing categories, E9 |
| G-CUSTODY | Named actual operator, analyst and custody process owner |
| G-LOCK | Freeze hashes of all analysis dependencies and invocation |
| G-EXPOSURE | Full pre-freeze exposure audit across every participating workflow |
| G-STORAGE | Actual protected locations for study mapping, logs and transcripts |
| G-RUNTIME | Provider latency/window estimate and full scheduled launcher; study runtime unmeasured |
| G-COST | Concrete token/billing limits, monetary ceiling and authority covering both stages |

Subsequent distinct recorded gates, none opened by this receipt: recorded permitted-implementation decision for paid preflight (E9), full-manifest freeze, experimental execution.

## Project artifacts touched in this session

- Saved (new): `pursuit_decision_reconciled_2026-09-08.md`, `offline_implementation_readiness_2026-09-08.md`, `offline_verification_2026-09-08.md`, `offline_sync_receipt_2026-09-08.md`
- Retained unchanged: `pursuit_decision_review_2026-09-08.md` v3 (artifact `7d5ee2ca`, version `e447c368`)
- Not modified: `ai_quantum_control_protocol_v0.4.md`, `research_evidence_brief_v2.md`, `protocol_governance_v2.md`, Project Context
