# Round 2 Disposition

Revision: round2-disposition, 2026-09-08. Status: **NOT FROZEN**; document correction only. No simulation, controller code, package install, experimental model call, blinding implementation, or freeze occurred. v0.1 and the Round 1 response are preserved unchanged. Inputs `research_evidence_brief_v1.md` and `protocol_governance_v1.md` were saved as artifacts byte-for-byte (SHA-256 `2f53b434…74b9` and `02a29464…58bf8`). Output: `ai_quantum_control_protocol_v0.2.md`.

Arithmetic in this round was limited to combinatorial identities (binomial sums, the pycma default population formula, prompt-size bounds); no objective was evaluated.

## 1. Item-by-item disposition

| # | Item | Disposition | Where in v0.2 | Notes / disagreement |
|---|---|---|---|---|
| 1 | Scope: remove dev instance, held-out grid, BB1 similarity, extra runs; synthetic fixtures only; no performance tuning | **Accept** | §1, §11 | Round 1's "exploratory" label did smuggle in objective variants. Consequence accepted: the only permitted pre-freeze model call is a format-compliance smoke test on fabricated history (E9), and runtime is measured on a timing fixture with unrelated nodes, not on the study grid. |
| 2 | Restore N=10, T=4π, d=20, B=200, K=10; drop BB1 solvability premise; CMA popsize=10 labelled nondefault, σ₀=0.5, no restarts, settings at pinned revision; not the strongest comparator | **Accept** | §2, §5 | My Round 1 change to N=12/T=6π rested on a solvability premise that was (i) unnecessary for a relative comparison and (ii) wrong in its reasoning: idle segments under nonzero δ accumulate z-rotation, so an appended-idle BB1 is not the BB1 action. No validity defect in the original instance was identified, so it is restored. pycma default λ for d=20 is 12; popsize=10 is labelled batch-matching. |
| 3 | Metric name; no worst-case/continuum language; no conversion to evaluations/shots; remove floating-point guarantee | **Accept** | §2, §3, §9.1 | Named "mean process (entanglement) infidelity on the fixed 25-node joint ensemble" with the Nielsen conversion 2I/3 reported as algebra only. The 10⁻¹² floor is a design choice; count of floored endpoints is reported. |
| 4 | Statistics: replace Wilcoxon+bootstrap with order-statistic median interval; margin m=log₁₀2 as research choice; three categories; both stages always completed; no pooling; explain assumptions | **Accept; coverage derived** | §9, §8.3 | Σ_{j≤5} C(20,j) = 21700; 21700/2²⁰ = 0.020695; coverage ≥ 1 − 2(0.020695) = **0.95861**. Adjacent attainable levels 0.8847 ([D₍₇₎,D₍₁₄₎]) and 0.9882 ([D₍₅₎,D₍₁₆₎]). Round 1's Wilcoxon targets the symmetry center, not the median, and percentile bootstrap of a median at n=20 has erratic coverage — the criticism is correct. **One addition, not a disagreement:** the interval's position relative to 0 and the sample median are reported as descriptive facts with no decision weight, so a "benefit smaller than m" pattern is visible without becoming a fourth category. Exact ties D=0 are plausible (both arms ending at the shared initial best) and are covered conservatively. |
| 5 | Identical raw domain; overflow-safe mapping; coordinate order; common observation format; which vector enters CMA tell/history; initialization use as method choice; literal prompts and schema; tie policy; no hidden state | **Accept** | §4, §5.2, §6.5–6.7 | Raw domain = ℝ²⁰ finite doubles for all methods; `hypot`-based disk projection; segment-major interleaved ordering. **Design decision beyond the challenge:** observations use shortest round-trip decimals (exact), eliminating the rounding asymmetry entirely rather than harmonizing a rounding rule. Cost: worst-case history ≈ 1.1×10⁵ characters at batch 19 (bounded; must fit the context limit — gate G-MODEL). CMA-ES is told its own raw samples with the objective of their mapped images. Full literal system prompt, user template, and JSON schema included. |
| 6 | Resource contract: call vs attempt; consistent caps; ordering of retry vs correction; no replacements or exclusions; keep incumbent; slot/call/valid/forfeit vocabulary; SVF for simulator failure | **Accept** | §7 | ≤2 logical calls/batch → ≤38/block; ≤3 transport attempts/logical call → ≤114/block; wall-clock bound follows from caps (no separate cap). Correction call only on zero valid vectors; partial validity fills what it can and forfeits the rest. No replacements, no exclusions; simulator failure → SVF preserved, prohibits a "supports" claim. **Disclosed consequence:** provider reliability becomes part of the configured method's outcome. That is the honest reading of "the configured proposer under this contract", and it is stated, not hidden. |
| 7 | Blinding: executable all-pairs locked summary, sealed, custodian selection; no fictitious independent custodian; custody as readiness gate; automated alternative and its limits | **Accept** | §10 | Six ordered-pair nuisance summaries, sealed by hash, then custodian selection. Codex and Claude Science are explicitly not independent custodians. Two fulfilments named for gate G-CUSTODY: (a) Chris as custodian, or (b) automated sequencing with the stated limitation that it proves order, not blindness. |
| 8 | Governance: actual authority; freeze/execution as separate recorded gates; complete freeze contents via metadata; unresolved values block freeze; non-circular gate order | **Accept** | §12, §13 | Authority recorded as Chris's delegation per governance-v1. Gate order: design review → permitted implementation/preflight → run-manifest freeze → evaluation. Model ID and decoding defaults captured from metadata or recorded as unavailable; nothing invented. |
| 9 | Citation review: verified brief sources, bounded paraphrase, preserve dissent, remove unsupported references; acknowledge SciPy header mismatch; don't assert trap-free assumptions all fail | **Accept, with a provenance finding** | §14.1, §15 | I checked the persisted retrieval record for Round 1's four searches: it contains **titles and URLs only** — the abstract text I quoted is not in the record. The quotations are therefore not re-verifiable and are withdrawn from the protocol. The landscape point now rests on PHY-RIVIELLO-2015 and is stated as non-establishment of applicability, not failure of assumptions. SciPy documentation snapshot mismatch acknowledged; installed version to be pinned (G-ENV). |

## 2. Self-identified defects not raised in the challenge (fixed in v0.2)

- **CMA-ES early termination.** pycma's default stop conditions (tolerance-based) could halt the strategy before 19 generations; v0.2 states that stop conditions do not govern control flow and makes the ask/tell-after-stop behavior a readiness item (G-CMA). Round 1 was silent on this.
- **Crash/resume determinism.** Round 1 had no resume rule. v0.2 specifies append-only logs plus per-batch checkpoints, with a fallback ("remaining CMA slots forfeited") if serialization continuation cannot be verified (E7).
- **Seed streams.** Round 1 used ad hoc offsets (s, s+10000, s+20000). v0.2 uses `SeedSequence(entropy=20260908, spawn_key=(s,))` with three spawned children in fixed order, which is the documented way to obtain independent streams.
- **Parser leniency policy.** Round 1's "reject/resample malformed vectors" was undefined. v0.2 defines an exact, non-selective per-vector rule (§6.7) with a single correction call only when zero vectors are valid.

## 3. Proposed evidence-registry additions (NOT relied on in v0.2; pending independent full-text verification)

Round 1 cited these from search-result abstracts. Titles/URLs are in the persisted record; abstract text is not. They are listed so the registry can decide on them; none supports any v0.2 decision.
- Pechen & Tannor, "Are there traps in quantum control landscapes?", PRL 106, 120402 (2011) — https://link.aps.org/accepted/10.1103/PhysRevLett.106.120402
- Rabitz et al., Comment on the above, PRL 108, 198901 (2012) — https://journals.aps.org/prl/abstract/10.1103/PhysRevLett.108.198901 (dissent; preserve alongside)
- Moore & Rabitz, "Exploring constrained quantum control landscapes" — https://arxiv.org/pdf/1111.1269
- Pechen & Il'in, "Coherent control of a qubit is trap-free", Proc. Steklov Inst. Math. (2014) — https://link.springer.com/article/10.1134/S0081543814040166
- Russell, Rabitz & Wu, "Quantum control landscapes are almost always trap free" — https://arxiv.org/pdf/1608.06198 (with the published Comment/Reply, not retrieved)
- de Fouquieres & Schirmer, "A closer look at quantum control landscapes…" (2013) — title only in Round 1; no URL in the persisted record; lowest verification status.

## 4. Remaining required corrections (design-level; close by independent review, not by me)

| ID | Item | Why still open |
|---|---|---|
| C1 | Independent review of v0.2 against R1–R10 | Closure of a finding requires review other than the author's (governance-v1). |
| C2 | Decide custody fulfilment (a) human custodian vs (b) automated sequencing | A design choice with different validity consequences; requires Chris's decision. |
| C3 | Confirm the exact-decimal observation format is acceptable given prompt-length cost (§4.3), or direct a declared rounding rule applied identically to what the LLM sees | Design trade-off, not an operational value. |
| C4 | Confirm `max_tokens` = 8192, timeout 300 s, backoff 5/20 s, entropy E = 20260908, floor 10⁻¹² as declared design constants | Declared by me under delegation; flagged for reviewer objection before freeze. |
| C5 | Whether pre-freeze E9 smoke calls (fabricated history) are permitted at the implementation stage | E9 is a model call; the current authorization excludes model calls. Needs the implementation-stage authorization to say so explicitly. |

## 5. Execution-readiness gates (operational facts; each blocks freeze) — see v0.2 §12

G-ENV, G-CMA, G-MODEL, G-TRANSPORT, G-CUSTODY, G-LOCK, G-EXPOSURE, G-STORAGE, G-RUNTIME. None is satisfied. None can be satisfied by document work.

## 6. Layperson summary of this round

The reviewer found that the earlier plan still had too many moving parts, used a statistical test that answers a slightly different question than the one we care about, and quoted papers whose exact wording I can no longer verify from my records. The corrected plan puts everything back to one contest, one scoring rule that needs no assumptions about the shape of the results, one declared "twice as good" bar, two independent rounds of twenty, and a locked scoring program that runs before anyone knows which competitor is which. Nothing has been run; several practical facts (software versions, the exact model, who holds the sealed key) must be measured or decided before anything can be frozen.

## 7. Speculative-commercial boundary

Unchanged from v0.2 §14.3: no outcome of this experiment supports a commercial inference, a hardware inference, or a "fewer evaluations/shots" inference.
