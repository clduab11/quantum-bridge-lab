# Preimplementation review

Revision: evidence-brief-v2, 2026-09-08. Status: design corrections resolved in protocol v0.4; implementation readiness and run-manifest freeze remain open. No experimental result.

## Authority and common scope

Chris delegated expert research and pre-freeze corrections to Codex and Claude Science. The first experiment contains exactly one small simulated system, one joint noise model, one objective, one AI approach, one conventional optimizer and random search under one fixed budget contract. Independent seed replication of the same procedure is allowed; extra targets, grids, ablations and reference optimizers are outside this first experiment.

The unchanged v0.1, Round 1 and protocol v0.2 are historical evidence. The operative reviewed design is [protocol v0.4](https://github.com/clduab11/quantum-bridge-lab/blob/research/protocol-hardening/specification/ai_quantum_control_protocol_v0.4.md). The first Round 1 request preceded the user's source-preflight instruction. Evidence-brief-v1 was then synchronized to GitHub, Linear and Claude Science before Round 2. This revision records the subsequent independent reviews and Fable's focused v0.3 check and the v0.4 clarification disposition; no history is retroactively represented as preflight.

## Evidence registry

Access date for every entry: 2026-09-08. Exa searched eight targeted queries with five results each (40 result slots, including duplicate representations). The eighth search supported the independent median-interval review. Statistical and physics agents fetched seven distinct primary works; root reviewed the CMA tutorial and official SciPy documentation. This is a bounded review, not an exhaustive literature survey. Search rankings and generated summaries are not evidence of correctness. Common IDs below are used in every project surface.

| ID | Primary source / version observed | Supported statement and limit |
| --- | --- | --- |
| PHY-NIELSEN-2002 | [Nielsen, average gate fidelity](https://arxiv.org/pdf/quant-ph/0205035); [published paper](https://doi.org/10.1016/S0375-9601(02)01272-0) | Applying the paper's relation to a qubit unitary error gives F_e = abs(Tr(X†U)/2)^2 and F_avg=(2F_e+1)/3. Thus the proposed I is mean process/entanglement infidelity; Haar-average gate infidelity is 2I/3. This conversion is an algebraic inference, not measured hardware fidelity. |
| PHY-RIVIELLO-2015 | [Searching for quantum optimal controls under severe constraints](https://journals.aps.org/pra/abstract/10.1103/PhysRevA.91.043401), published primary research | Duration, strength and control-variable constraints can obstruct optimization. Unconstrained landscape assumptions do not establish this ensemble problem is trap-free. The source also does not prove this particular instance has traps. |
| PHY-ZHANG-2025 | [Smolyak algorithm assisted robust control](https://arxiv.org/html/2410.14286v3), arXiv v3; journal status not checked | Distinguishes a distributional expectation from finite weighted quadrature and treats a similar quasi-static Hamiltonian. Our uniform 25-node ensemble is a discrete model; its mean does not certify continuous-range or worst-case robustness. Published numerical performance is not imported. |
| PHY-KOSUT-2022 | [Robust Quantum Control: Analysis & Synthesis via Averaging](https://arxiv.org/pdf/2208.14193), primary preprint; journal status not checked | Robustness depends on the specified uncertainty set; piecewise-constant propagation uses matrix exponential products. Analytic propagation within that model does not eliminate floating-point or physical-model error. |
| STAT-ASA-2016 | [ASA statement on p-values](https://www.tandfonline.com/doi/full/10.1080/00031305.2016.1154108), primary methodological statement | Non-significance is not evidence of no benefit; a p-value is not effect magnitude or the probability a hypothesis is true. Does not choose this project's test, margin or decision threshold. |
| STAT-LAKENS-2022 | [Sample Size Justification](https://doi.org/10.1525/collabra.33267), primary methods paper | Resource constraints, desired precision and a-priori power are different justifications. Project-specific precision/power needs explicit assumptions; a round seed count does not establish adequate power. |
| BENCH-COCO-2016 | [COCO](https://arxiv.org/abs/1603.08785), primary benchmark paper/preprint | Supports explicit objective-call resource accounting; its central runtime measure is calls to a target. It does not validate this project's different final-budget estimand. Equal objective calls alone imply neither equal total compute nor lower money/time/hardware shots. |
| OPT-CMA-TUTORIAL | [Hansen, CMA Evolution Strategy tutorial](https://arxiv.org/html/1604.00772v2), primary author tutorial | Describes Gaussian population search and covariance adaptation. It is method documentation, not evidence CMA-ES is the strongest baseline at the proposed budget, or that it reaches a certified global optimum. |
| DOC-SCIPY-PAIRED | [SciPy permutation_test](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.permutation_test.html); [wilcoxon](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.wilcoxon.html) | Within-pair swaps require the corresponding assignment/exchangeability null. Wilcoxon concerns symmetric paired differences; ties/zeros affect exact p-values. Shared seeds alone do not establish those assumptions. |
| DOC-SCIPY-BINOM | [SciPy binomtest](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.binomtest.html) and its exact proportion interval | Provides inference for a Bernoulli success probability. This is an available candidate if the estimand becomes a prespecified paired win probability; it does not itself choose that estimand or establish independent, identically distributed blocks. |

Context7 resolved `/scipy/scipy` (catalog lists v1.16.1) and returned repository `main` snippets for paired permutation, exact binomial intervals and Wilcoxon ties/zeros. Exa fetched official SciPy pages whose retrieved headers differ (Wilcoxon 1.17.0; permutation/binomial 1.18.0). These are documentation observations, not installed-version claims. A future implementation must pin one actual package version, verify its matching documentation and exercise ties, zeros, failures and degenerate data. No package was installed to create this brief.

## Adversarial correction register

Classification vocabulary: fatal validity threat; required correction before protocol freeze; optional improvement; open question; accepted limitation. All R findings below were classified **required correction before protocol freeze**. Their design-text corrections are resolved in v0.4, following separate statistical and operational reviews and Claude Science's focused check. This does not claim the future implementation or readiness checks have passed. The original requirement and its closure evidence remain visible below.

| ID | Correction required | Evidence / verification condition |
| --- | --- | --- |
| R1 | Reduce v0.1 to exactly one AI, one conventional method and random search on one instance. | No additional development target, held-out grid, sensitivity family or reference optimizer in the first experiment. Analytic identities and dummy interface data must not become tuning experiments. |
| R2 | Use one minimize objective and name it correctly. | PHY-NIELSEN-2002; precise coordinate ordering, mapping, numerical observation format and objective direction agree everywhere. |
| R3 | Define estimand, population, independent unit, matching uncertainty method, decision rules and sample-size rationale. | DOC-SCIPY-PAIRED; STAT-ASA-2016; STAT-LAKENS-2022. No unsupported symmetry/exchangeability, post-data comparator, unexplained exact test, or equivalence claim from non-significance. An interval must support the stated meaningful margin, not just a point estimate. |
| R4 | Correct simulator work and bound every resource path. | N × 25 segment propagations per valid evaluation (250 for v0.1 N=10). Initialization, duplicates, invalid submissions, retries, tokens, latency and preparation separately counted; runtime unmeasured until observed. BENCH-COCO-2016. |
| R5 | Prevent outcome exposure from silently becoming tuning. | Log every evaluative access; preserve pre-exposure/post-exposure amendments. No new objective instance smuggled in as development or exploratory checking. |
| R6 | Remove result-dependent redesign and selective exclusion. | No requirement that a baseline first reaches a favorable outcome. Predetermine infrastructure failure, timeout, intervention, rerun and scoring rules without dropping difficult cases. |
| R7 | Separate controller information from evaluator blinding. | Neutral labels alone are insufficient; lock analysis before exposure, protect mapping and raw identity-revealing logs, define how the prespecified comparison is evaluated without selecting it after unmasking. Report residual leakage and actual operator/analyst roles. |
| R8 | Remove reasoning/retrieval causal claims and reconcile efficiency language. | Retrieval is an admissible explanation for the configured proposer. Better final objective at a fixed budget does not establish fewer calls to a target, hardware shot reduction or commercial savings. |
| R9 | Specify operational choices and honest readiness gates. | Exact action format, feasible mapping, optimizer configuration, prompt/model/configuration, seed streams, failure rules, caps, logs and availability audit. No invented package versions, model IDs or measured precision floors. |
| R10 | Freeze the complete protocol prospectively and preserve provenance. | PROTOCOL_REGISTER.md; actual hashes and authority records, immutable originals, additive amendments, recorded outcome access and all-result preservation. No historical authorization or complete blindness invented. |

## Source disagreements and unresolved choices

No source establishes that a particular conventional optimizer is strongest on this instance. A chosen single comparator limits the claim to that exact configuration. No cited source supplies a hardware-relevant minimum effect or a project-specific power guarantee. A practical margin must be a declared research design choice.

The finite-grid objective is a mean; it is neither worst-case robustness nor a continuum guarantee. A feasible pulse bounds the minimum infidelity from above; multiple optimization restarts would still not certify the optimum. Landscape assumptions, finite precision and physical model limits remain separate.

Exa and Context7 are retrieval services, not writable protocol stores. Superpowers is the planning/review/verification workflow. Uniform information means identical source IDs, scope, correction status and revision pointers in GitHub, Claude Science and Linear, with uncertainty and disagreement retained.


## Independent review resolution and current design

The operative v0.4 has SHA-256 `0df9242fd2d0ad5d30b75ea91f498842ac68fe0df9616afd4c9c04518233eda5`. Codex authored the derivative; Claude Science authored the preserved v0.2 and critically reviewed v0.3; v0.4 applies its seven non-blocking clarifications. Independent statistical re-review resolved six findings; independent operational review resolved its three findings and a subsequent missing-RS-endpoint wording regression. Fable independently reported no blocking design contradiction after reading v0.3 and checking its arithmetic. Its N1–N7 clarifications are explicitly resolved in v0.4 §16; final artifact readback verifies identity separately from scientific review. These are document reviews, not empirical validation.

| Finding | v0.4 closure evidence |
| --- | --- |
| R1 | §§1–3 and 11: N=10, T=4π, d=20, one 25-node joint ensemble/X objective, one AI, one CMA-ES configuration, random search; no alternate-grid or target development experiment. |
| R2 | §§3–6: process-infidelity name, minimize direction, segment-major ordering, common finite-float domain, overflow-safe disk mapping, shortest round-trip observations and explicit raw/mapped CMA flow. |
| R3 | §§0 and 8–9: lower 0.5 quantile of the floored paired log ratio; closed order-statistic interval retaining ties; declared log10(2) margin; separate always-completed stages; conditional iid assumptions; no Wilcoxon, post-data comparator or pooled confirmatory test. |
| R4 | §§2 and 7: 250 segment propagations per valid evaluation; slots/calls/attempts/forfeits/uncertain reservations separated; true deadlines, token ceilings and later cost gate. No measured runtime claim. |
| R5 | §§6, 11 and 13: no outcome-driven prompt tuning; analytic identities and stubbed fixtures; actual objective/model access logged; prospective exposure amendments. |
| R6 | §§5 and 7–9: no favorable-baseline gate, no run replacements, no dropped failed blocks; no replay after crash; simulator/inferential failures block both confirmatory support and exclusion. |
| R7 | §10: locked all-ordered-pair summaries, sealed output, precommitted pair selection; nonce-protected commitment; automated sequence selected and expressly not independent blinding. |
| R8 | §§0, 9 and 14: claims limited to the floored paired ratio for this configured instance; no reasoning/retrieval mechanism, target-hitting, hardware or commercial inference; inconclusive distinct from exclusion. |
| R9 | §§4–8 and 11–12: complete normative prompts/schema, response-envelope/per-slot salvage, finite-input and partial-CMA handling, bounded retries and failure state, fixed seed policy; unknown operational metadata blocks readiness. |
| R10 | §§12–13: real authority records and distinct design/implementation/freeze/run gates; complete future manifest, protected originals and additive amendments. |

Declared expert decisions: CMA popsize10 is explicitly nondefault; exact-decimal observations preserve precision at a context-cost tradeoff; the 10^-12 floor and factor-two floored-ratio margin are research choices; automated sequencing supports autonomy while sacrificing independent evaluator blinding. The user's scientific delegation covers these design decisions. Monetary limits, provider identity/settings and paid preflight/run authority remain actual readiness decisions, not invented facts.

### Additional median-inference evidence

- **STAT-GEYER-2007:** [Geyer, Nonparametric Tests and Confidence Intervals](https://www.stat.umn.edu/geyer/s06/5102/notes/rank.pdf), author lecture notes, §§1.1–1.3. Supports sign-test inversion/order-statistic coverage. Its suggestion that continuity ensures a unique median is not adopted; v0.4 defines the lower quantile explicitly.
- **STAT-IWASAKI-2005:** [Iwasaki, Less Conservative Distribution-free Confidence Intervals and Tests for the Median](https://doi.org/10.5691/jjb.26.65), primary methods paper. Corroborates binomial median intervals and ties; its interpolated/mid-P alternatives are not adopted.
- [Independent proof and review](https://github.com/clduab11/quantum-bridge-lab/blob/research/protocol-hardening/research/median_inference_review.md): closed [D_(6),D_(15)] has at least 95.8610534668% coverage under iid blocks, conservatively including atoms/ties. This is a mathematical derivation using binomial sums, not a simulation. Separate stage intervals are not a joint 95% region. Width/power depends on the unknown outcome distribution.

Unverified Round 1 quotations and proposed extra landscape references remain visible in the original Round 2 disposition, explicitly not relied on. No missing retrieval provenance is fabricated to make sources appear uniform.
