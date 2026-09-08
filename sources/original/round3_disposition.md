# Round 3 Disposition — Focused review of protocol v0.3

Revision: round3-disposition, 2026-09-08. Status of the reviewed protocol: **NOT FROZEN. NO EXPERIMENT RUN. NO BLINDING IMPLEMENTED.**
Reviewed file: `ai_quantum_control_protocol_v0.3.md`, SHA-256 `784940f63b2bb1eae5355c476d505cdbfc015969bacac34a880f348d78e2e762` (verified in-workspace before review; saved unchanged). Also read: `round3_review_request.md` (`f16f58f4…ae18`), `median_inference_review.md` (`8052dba6…99d8`).
Scope observed: document review only. No experiment, simulation, controller code, package install, model call, or freeze. Arithmetic performed: finite binomial sums and the §7.2 time-allowance sum; the §4.2 mapping formula was exercised on six hand-chosen numeric pairs as a formula check on the document text, not as an engineering check of any implementation.

## 1. Review conclusion

**No blocking design contradiction was found in v0.3.** The six statistical corrections named in the review request are present and internally consistent (§0, §7.4, §7.7, §9.2–9.5, §14.3); the operational corrections are present (§4.2, §6.7, §7.1–7.5, §8.2, §10.2–10.3, §12 G-COST). v0.3 is therefore saved unchanged as the operative draft.

This conclusion is a **design-consistency judgement**, not empirical validation. Nothing in v0.3 has been executed; every readiness gate in §12 remains open (§4 below). I do not assert that R1–R10 are closed; that reconciliation belongs to Codex across the independent reviews.

## 2. What was checked and agreed (design agreement, not validation)

| Area | Check | Result |
|---|---|---|
| Estimand | Lower-median convention θ = inf{x : F_D(x) ≥ ½} fixed in §0/§9.2; interval covers any fixed median, hence this one | Consistent with `median_inference_review.md` |
| Interval arithmetic | Σ_{j≤5} C(20,j) = 21 700; q = 21 700/2²⁰ = 0.020694…; 1−2q = 1 005 176/1 048 576 = 0.958610… | Re-derived; matches §9.3 and the independent review |
| Two-stage statements | (1−2q)² = 0.91893…; 1−4q = 0.91722…; q² = 0.000428… | Re-derived; v0.3 correctly makes **no** joint-95% claim (§9.5) |
| Decision-rule direction | Supports ⇔ D₍₁₅₎ < −m ⇔ ≥15 of 20 strictly below −m; under θ ≥ −m, P(D < −m) ≤ ½ so false-support probability ≤ q. Excludes ⇔ D₍₆₎ > −m; under θ ≤ −m, F(−m) ≥ ½ so P(D > −m) ≤ ½, false-exclusion ≤ q. Endpoint equality → inconclusive | Directions and strictness correct |
| Validity failures | SVF/IVF prohibit both confirmatory support and confirmatory exclusion (§7.7); finite I outside [0,1] is simulator-invalid (§7.4); model/decoding change is IVF (§7.4, §8.3) | Consistent across §5.2, §7.4, §7.7, §9.5, §13.5 |
| Mapping | §4.2 a>1 branch: after scaling by a = max(|x|,|y|), h ∈ [1, √2], so no overflow; result is the unit-norm projection; the 0<a≤1 branch is the ordinary rule. Formula check on (1.7e308, 1.7e308), (1e300, −3), (0.6, 0.9), (0.3, 0.4), (−1, 1e−320), (2, 0) gave finite unit-or-unchanged outputs | Formula is correct; note item N3 below |
| Time allowance | 114×300 + 38×25 = 35 150 s; 36 000 s deadline leaves 850 s for local work — a cap with a forfeit path, not a runtime guarantee | Arithmetic correct; consequence disclosed in §7.2 |
| Parser/slot rule | Envelope-invalid (extra keys, ≠10 elements) → correction path; per-slot salvage after valid envelope; no packing; fixed reason codes | Consistent with §6.5 wording "its evaluation slot is lost" |
| Prompt fields | `{remaining_after}` = 200 − 10(b+1): 180 at b=1, 0 at b=19 | Correct |
| C2–C4 resolutions | Automated locked sequencing explicitly labelled *not* independent evaluator blinding; exact shortest-round-trip observations; retained constants (10⁻¹² floor, 8192, 300 s, 5/20 s, E = 20260908) with G-COST ceilings required before paid work | Reflected in §4.3, §6.1, §7.2, §10.3, §12 |
| C5 | E9 is a permitted-implementation-stage activity requiring an actual decision; §13.2 step 2 says design-review closure is not authority | Consistent with the review request |

## 3. Non-blocking clarifications recommended before freeze (editorial or specification-completeness; none contradicts the design)

- **N1 — Arm continuation after a simulator-invalid evaluation.** §5.2 terminates the CMA-ES arm (a `tell` cannot be completed). For the LLM and RS arms, §7.4 records the slot as `simulator_invalid` and sets SVF but does not say whether the arm continues. The definitions imply it continues (history = valid evaluations only). Recommend stating this explicitly so the asymmetry with CMA-ES is visible.
- **N2 — Stale gate wording.** §12 G-CUSTODY reads "fulfilment (a) or (b) chosen", but §10.3 already selects (b). Recommend "(b) implemented; process owner and roles named".
- **N3 — Mapping rounding tolerance value.** §4.2 refers to "a prespecified component-test tolerance" for post-mapping norm violations, but no value is declared. Mapped norms of 1 ± a few ulp are expected (e.g., 0.9999999999999999 in the formula check). The tolerance must be a declared constant before freeze; otherwise "material constraint violation" is undefined and could trigger SVF non-deterministically.
- **N4 — Bare code fence.** §6.5 permits an optional ```` ```json ```` fence and §6.7 strips "at most one surrounding `json` code fence". A bare ```` ``` ```` fence would be `invalid_json`. Acceptable as written, but E5 should include that fixture and the rule should say so explicitly.
- **N5 — Reported quantities.** §9.6 lists SVF events but not IVF events; §7.7 treats both. Add IVF to §9.6.
- **N6 — Wording in §7.4.** "Block remains in analysis unless SVF/IVF applies" could be read as exclusion; §7.7 and the "No excluded blocks" paragraph make clear that SVF/IVF blocks confirmatory interpretation rather than removing the block. Recommend "Block remains in analysis; SVF/IVF blocks confirmatory interpretation".
- **N7 — Duplicate-key rejection.** §6.7 rejects duplicate JSON object keys; standard parsers accept them (last wins). This requires a custom or hooked parser and belongs in E5. Implementation item, not a design issue.

## 4. Unresolved execution-readiness gates (facts, not documents; each blocks freeze)

G-ENV, G-CMA, G-MODEL, G-TRANSPORT, G-CUSTODY (option (b) implementation and named roles), G-LOCK, G-EXPOSURE, G-STORAGE, G-RUNTIME, G-COST. **None is satisfied.** None can be satisfied by document work. In particular: no model identifier, decoding configuration, tokenizer-derived input ceiling, package version, or spending ceiling exists yet; no permitted-implementation decision has been recorded; E9 calls are not permitted in this turn.

## 5. Explicit distinctions

- **Agreement with a design choice** (this document): the order-statistic interval, the lower-median convention, the three-category rule, the no-replay/no-replacement contract, automated locked sequencing, exact observations, and the declared constants are coherent and I concur with them under Chris's delegation.
- **Empirical validation** (not done, not claimed): whether the simulator, parser, runner, CMA-ES integration, provider transport, or locked analysis behave as specified; whether the iid/stationarity model holds for the provider; the actual runtime, token, and cost figures.
- **Closure of R1–R10**: not asserted here; to be reconciled by Codex across the independent statistical and operational reviews.

## 6. Evidence and citations

No new literature search was performed; none was needed for a factual contradiction. Evidence IDs used by v0.3 are those of `research_evidence_brief_v1.md` plus STAT-GEYER-2007 and STAT-IWASAKI-2005 introduced by `median_inference_review.md`, whose stated limitations (lecture-note uniqueness overstatement; interpolated/mid-P variants not adopted) are accepted as written.

## 7. Layperson summary

The corrected plan was checked for internal contradictions: whether its scoring rule, its definitions of "too broken to count", its rules for lost or crashed attempts, and its arithmetic all say the same thing in every section. They do. That is a statement that the plan is coherent, not that it works — nothing has been built or run, and a list of practical facts (which model, which software versions, how much it may cost, who owns the sealed key) still has to be established before anything can be frozen.
