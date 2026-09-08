# Preimplementation review

Revision: evidence-brief-v1, 2026-09-08. Status: research preparation; not a frozen protocol or experimental result.

## Authority and common scope

Chris delegated expert research and pre-freeze corrections to Codex and Claude Science. The first experiment contains exactly one small simulated system, one joint noise model, one objective, one AI approach, one conventional optimizer and random search under one fixed budget contract. Independent seed replication of the same procedure is allowed; extra targets, grids, ablations and reference optimizers are outside this first experiment.

The unchanged v0.1 source is historical evidence, not the operative protocol. Claude Science Round 1 is in progress and any intermediate file is provisional. No new inference request follows until this source brief has been synchronized. The initial Round 1 request preceded the user's source-preflight instruction; this chronology is preserved.

## Evidence registry

Access date for every entry: 2026-09-08. Exa searched seven targeted queries with five results each (35 result slots, including duplicate representations). Statistical and physics agents fetched seven distinct primary works; root reviewed the CMA tutorial and official SciPy documentation. This is a bounded review, not an exhaustive literature survey. Search rankings and generated summaries are not evidence of correctness. Common IDs below are used in every project surface.

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

Classification vocabulary: fatal validity threat; required correction before protocol freeze; optional improvement; open question; accepted limitation. All R findings below are **required correction before protocol freeze**. They remain open until a saved revised artifact and independent review establish closure.

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
