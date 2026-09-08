# Round 1 Response — Adversarial Review of `ai_quantum_control_minimal_experiment.md` v0.1

**Status:** Reasoning response only. Not a protocol, not a freeze, not an approval. v0.1 is preserved unchanged.
**Authorization scope observed:** research and document reasoning. No simulations, controller code, package installation, model calls, or hash/freeze claims were made in producing this document.
**What this document is not:** it does not claim any measured runtime, any installed package version, any model ID, or any experimental outcome. Where a fact requires measurement, a readiness gate is stated instead.

---

## Part A — Disposition of review findings R1–R10

| Finding | Disposition | Reasoning |
|---|---|---|
| **R1 Scope** | **Accept** | v0.1 was a programme, not an experiment. Two LLM arms, four optimizers, a reference optimizer, and four variant families multiply comparisons and researcher degrees of freedom. Corrected design (Part B) has exactly one AI arm, one conventional optimizer, one random-search baseline. Justification for the optimizer choice is in B.5; it is chosen on configuration-surface and standing grounds, not on expected outcome. |
| **R2 Objective** | **Accept** | v0.1 §3 minimized I(θ) while §4's blind arm was told to maximize an undefined f. Single representation adopted: every method minimizes I(θ) ∈ [0,1], receives the same numeric table, same direction, same precision. |
| **R3 Statistics** | **Accept, with one qualification** | v0.1 mixed a paired design with an unpaired test, chose the comparator after seeing outcomes, and left the bootstrap unit, effect-size sign, and precision rationale unspecified. Corrected: paired estimand, exact Wilcoxon signed-rank, seed as the resampling unit, sign convention fixed, one primary comparison (no multiplicity), smallest effect size of interest declared, five mutually exclusive decision categories including "inconclusive". *Qualification:* pairing via a shared initial batch induces only weak dependence; the paired analysis is retained because it is valid under either dependence or independence and is conservative in the latter. Non-significance is **not** equivalence; equivalence requires the CI to lie inside the declared margin. |
| **R4 Accounting** | **Accept** | v0.1's "~25 exponentials per evaluation" was wrong by a factor of N: each evaluation propagates all 25 grid points through all N segments. With the corrected N = 12 that is 300 closed-form SU(2) exponentials per evaluation. Runtime was asserted, not measured — replaced by readiness gate G3. Full accounting contract in B.7: evaluation definition, initialization, duplicates, invalid outputs, retries, infrastructure failures, tuning, human iteration, tokens/time, resource stops. Equal evaluation counts are not represented as equal compute. |
| **R5 Data separation** | **Accept, with one qualification** | Prompt/interface development is confined to a development instance D that differs from the evaluation instance P in target and error grid. Any evaluation of P by any optimizer or LLM before freeze is an outcome-exposure event and is logged. *Qualification:* one held-out noise-grid check is retained as a **single descriptive, exploratory** quantity computed on each run's final best θ — it is not a second experiment and carries no test. Conclusions are constrained to the evaluated model, prompt, optimizer configuration, problem instance, and budget. |
| **R6 Outcome-dependent redesign** | **Accept** | v0.1 §10 step 3 ("if S4 fails, redesign") and criterion S4 itself used baseline outcomes to gate the protocol. Both removed. Solvability is now addressed by analytic preflight checks that evaluate *known* pulses (not optimizer outputs) — see B.8. Failed protocols are preserved; any redesign requires a dated prospective amendment and a new evaluation instance with fresh seeds. |
| **R7 Blinding** | **Accept, with disclosure** | v0.1 conflated controller-input obfuscation with evaluator blinding. Corrected: neutral labels A/B/C assigned by a custodian via sealed random permutation; masked analysis dataset restricted to (label, seed, eval_index, cumulative_best); analysis script locked by hash before unmasking; unmasking is a separately authorized step. Residual leakage disclosed in B.9 — the run operator necessarily knows the arm; the locked script removes analytic discretion but not interpretive discretion. |
| **R8 Mechanisms** | **Accept** | Informed-vs-blind performance differences cannot identify "reasoning" vs "retrieval" vs "prior": prompt length, numeric formatting, the blind arm's lack of scale information, and stochastic decoding are all confounded with the manipulation. All mechanism language removed. A3 and F5 were contradictory (retrieval permitted as a mechanism, then declared a failure); resolved by adopting a single stance — the hypothesis is about the *configured proposer's parameter-discovery efficiency*, and how it arrives at proposals is not a claim of this experiment. A similarity-to-known-sequences summary is retained as exploratory description only. |
| **R9 Operational completeness** | **Accept** | Single baseline configuration, exact feasibility mapping, model/prompt/version requirements, JSON validity rules, failure/exclusion/rerun rules, seed scheme, raw-artifact list, and null-result preservation are specified in B.6–B.8. No package versions or availability are asserted; these are readiness gates. |
| **R10 Freeze** | **Accept** | Version numbers and pre-registration prose are not approval. B.10 specifies: immutable source provenance (commit SHA), freeze manifest (file hashes, environment manifest, model ID, seeds, budget, mapping-file hash), an authorization record that must exist as a human-authored artifact before execution, append-only amendments, an outcome-exposure audit, and a confirmatory/exploratory classification table. Public-repository hygiene rules stated. |

---

## Part B — One coherent corrected design (proposal, not frozen)

### B.1 Hypothesis (as a simulator parameter-discovery claim)

> **H1′:** In the simulator and under the budget contract defined below, the configured LLM proposer (one model ID, one prompt hash) attains a lower best-found ensemble infidelity than CMA-ES (one configuration) after B evaluations, as measured by the paired median difference in log₁₀ infidelity over 20 seeds.

Nothing in H1′ is a claim about physics, hardware, reasoning, or generality. A positive result licenses exactly the sentence above with the instance identifiers filled in.

### B.2 The one simulated system and the one joint noise model

- Two-level system, closed dynamics, rotating frame, ħ = 1, Rabi scale Ω_max = 1.
- H(t) = ½ [ (1+ε) (uₓ(t) σₓ + u_y(t) σ_y) + δ σ_z ].
- **Joint quasi-static noise model:** (ε, δ) on the fixed 5 × 5 grid ε ∈ {−0.10, −0.05, 0, 0.05, 0.10}, δ ∈ {−0.20, −0.10, 0, 0.10, 0.20}, uniform weights. This is the only noise model; it is explicit and deterministic.
- Piecewise-constant controls: **N = 12** segments, total duration **T = 6π/Ω_max**, so Δt = π/2 and a full-amplitude segment is a π/2 rotation. (Change from v0.1's N = 10, T = 4π: at T = 4π the standard robust composite π-pulses — BB1 and SK1 require total rotation 5π — were *infeasible*, which undercut v0.1's own solvability argument. At T = 6π, N = 12, BB1(π) is exactly representable in 10 segments with 2 idle segments.)
- Dimension d = 2N = **24**.

### B.3 Feasibility mapping (one rule, all methods)

Every method emits a raw vector r ∈ ℝ²⁴. It is mapped to θ by **per-segment disk projection**: for each segment k, if uₓ,ₖ² + u_y,ₖ² > 1, scale (uₓ,ₖ, u_y,ₖ) to unit norm; otherwise unchanged. No separate box clipping. Both r and θ are logged; the objective is always evaluated at θ. This is the physical amplitude constraint and is identical across arms.

### B.4 The one objective (minimize)

I(θ) = 1 − (1/25) Σ_{(ε,δ)} | Tr( U_target† U(θ; ε, δ) ) / 2 |²,  U_target = σₓ.

Range [0, 1]. Global-phase invariant (this matters: de Fouquieres & Schirmer report that traps emerge for unitary-operator objectives when the domain is restricted to SU(N) and are removed by a phase-invariant performance index; our I is phase-invariant by construction). All methods receive I to 6 significant figures and are instructed to **minimize**. For log-scale analysis, I is floored at 10⁻¹² before taking log₁₀ (see B.11 on numerical resolution).

### B.5 The one conventional optimizer: CMA-ES — and why

**Choice:** CMA-ES (pycma), default strategy parameters, population λ = 4 + ⌊3 ln d⌋ = **13** for d = 24, initial step σ₀ = **0.5** in raw coordinates (Hansen's guidance places σ₀ at roughly a quarter to a third of the search range; 0.5 on a [−1, 1] range is within that band and is fixed here before any evaluation), no restarts (the budget is too small for IPOP), no bound handling (the feasibility map in B.3 handles constraints), initial mean x₀ = the best point of the shared initial batch, RNG seeded per run.

**Why CMA-ES rather than Bayesian optimization:**
1. *Minimal configuration surface.* The CMA-ES design philosophy is that default strategy parameters are part of the algorithm, not the application; the user sets only x₀, σ₀ and termination. BO in d = 24 requires choosing a kernel, length-scale priors, noise term, acquisition function, batch strategy, and inner optimizer — each an undeclared degree of freedom.
2. *Invariance to monotone transformations of the objective.* CMA-ES behaves identically on I and log I, which makes the R2 representation question moot for the baseline.
3. *Natural batch interface.* λ proposals per generation match the LLM's batch-of-K interface exactly, so budget accounting is symmetric.
4. *Standing.* CMA-ES is the reference derivative-free method in black-box benchmarking (BBOB/COCO) for moderate-dimensional continuous problems.

**What this choice does not establish:** at B/d ≈ 11, BO is often competitive or stronger; a null result against CMA-ES does not imply a null against BO, and a positive result does not imply superiority over BO. This is stated as a limitation, not hedged around.

**Random-search baseline:** 260 points drawn i.i.d. from the same distribution used for every arm's initial batch — per segment, uniform on the unit disk (angle uniform, radius = √u). Descriptive only; no test is run against it.

### B.6 The one AI approach

**LLM batch proposer, physics-informed, stateless.**

- Each call is a single-turn request: frozen system prompt + user message containing (i) the problem description including the Hamiltonian, grid, constraint, and target; (ii) the complete history of evaluated (θ, I) pairs so far, sorted ascending by I, θ to 4 decimals, I to 6 significant figures; (iii) the number of evaluations remaining; (iv) a JSON schema requiring exactly K = 13 vectors of exactly 24 numbers in [−1, 1].
- No tool use, no code execution, no multi-turn memory, no access to baseline results.
- Model: **one** model ID, recorded verbatim at freeze (readiness gate G6; not asserted here). Sampling temperature: the provider default, recorded; chosen because it is the untuned setting — it is a fixed configuration parameter, not an experimental variable. `max_tokens` fixed and recorded.
- Prompt: one system-prompt file and one user-template file, SHA-256 hashed into every results row. Developed exclusively on development instance D (target = Hadamard, grid ε ∈ ±0.15, δ ∈ ±0.25, N = 12). Number of development iterations logged.

### B.7 Resource-budget and accounting contract

- **Evaluation:** one call I(θ) on a mapped θ. Every call consumes one of **B = 260** slots (20 batches × 13). Batch 0 is the shared random initial batch (13 points, identical across arms for a given seed). Batches 1–19 are optimizer proposals.
- **Duplicates:** a proposal bitwise-identical to a previously evaluated θ is evaluated anyway and consumes a slot (both arms may do this; counts are reported).
- **Invalid LLM output** (unparseable JSON, wrong count, wrong length, non-finite entries): one corrective retry per batch. After the retry, any still-invalid vector **forfeits its slot** — I recorded as NaN, best-so-far unchanged, slot consumed. Maximum 2 LLM calls per batch → hard cap of 38 LLM calls per run. Forfeit counts are reported per run.
- **Infrastructure failures** (HTTP 5xx/429, timeouts): exponential backoff, at most 5 attempts, not counted as invalid output. If exhausted, the run is marked `incomplete-infrastructure`, preserved, excluded from the primary analysis, and one replacement run instance for the same seed is created and labelled as such (max 1 per seed). Counts reported.
- **Human intervention** during any run voids that run (preserved, labelled `intervened`, excluded).
- **Wall-clock cap:** per run, fixed at freeze after measuring simulator and interface latency on instance D (gate G3); exceeding it marks the run `timed-out` (preserved, excluded, replaced once).
- **Cost table (reported, not equalized):** simulator evaluations (equal by contract); LLM calls; input/output tokens; wall-clock per arm; number of prompt-development iterations on D; developer hours (self-reported). No claim of equal total compute is made.
- **Tuning:** CMA-ES has no tuning phase; σ₀ is fixed above. The LLM prompt's development on D is its tuning phase and is disclosed as such.

### B.8 Preflight engineering checks vs. evaluative outcomes

Preflight checks are analytic or measurement-only; they involve no optimizer output on P.

| Gate | Check | Type |
|---|---|---|
| G1 | Unit tests: propagator unitarity (‖U†U − 1‖ < 10⁻¹²); ideal 2-segment π pulse gives I < 10⁻¹² at ε = δ = 0; two runs of the same θ are bitwise identical; I is invariant under global phase of U_target | analytic |
| G2 | Known-pulse references evaluated on P and recorded: plain π pulse; BB1(π) in the 12-segment encoding. These are *reference points*, not thresholds — they demonstrate that structured pulses exist inside the feasible set, nothing more | analytic |
| G3 | Measured per-evaluation runtime and full-run simulator runtime on the actual environment; measured LLM interface latency on D | measurement |
| G4 | Environment manifest (Python, numpy, scipy, cma versions) captured by `pip freeze` at freeze time | measurement |
| G5 | LLM interface smoke test on D only; confirmation from the outcome-exposure log that zero LLM or CMA-ES evaluations of P exist | audit |
| G6 | Model ID string recorded | record |
| G7 | Custodian mapping file created, hashed, stored outside the repository | governance |

**Removed:** v0.1's S4 (baseline must reach I < 0.1) and step-3 redesign. If, after unmasking, the problem turns out to be too easy or too hard for any arm, that is a *result* of this instance and is reported; a new instance requires a prospective amendment and fresh seeds.

### B.9 Blinding design and residual leakage

- Runner writes raw per-arm logs and LLM transcripts to a protected directory (not the public repository).
- Custodian (not the analyst) draws a sealed random permutation assigning {A, B, C} to {LLM, CMA-ES, random}; the mapping file is hashed, and the hash — not the contents — enters the freeze manifest.
- Masking script emits the **analysis dataset**: (label, seed, eval_index, cumulative_best). Deliberately excluded: per-evaluation I (forfeit NaNs would identify the LLM arm), θ (proposal-style differences would identify it), timestamps and token counts.
- Analysis script is written against D-derived dummy data, locked by hash before any P data exists, and executed once on the masked dataset. Output is hashed. Unmasking is a separate, logged, authorized step.
- **Residual leakage (disclosed):** the run operator knows which arm is which; best-so-far curve shapes may differ characteristically between arms; the analyst can plausibly guess. The locked script removes analytic discretion; the decision categories in B.12 remove most interpretive discretion; neither removes it entirely.

### B.10 Freeze, provenance, and governance records

- **Provenance:** all protocol files, code, and prompts at a single git commit SHA in the public repository; the freeze manifest lists SHA-256 of every file, the environment manifest (G4), model ID (G6), seed lists, B, K, σ₀, and the mapping-file hash (G7).
- **Authorization record:** a human-authored artifact (signed commit or issue) by the repository owner that references the manifest hash. Execution does not begin before this exists. This document does not constitute or claim it.
- **Amendments:** `AMENDMENTS.md`, append-only, each entry dated and tagged `pre-exposure` or `post-exposure`.
- **Outcome-exposure audit:** `EXPOSURE_LOG.jsonl` listing every evaluation of I on P before freeze (expected: G1/G2 entries only) and every P-data access after the run.
- **Classification:** confirmatory = primary endpoint on seeds 0–19 and its replication on seeds 20–39 (B.12); everything else exploratory.
- **Public-repository hygiene:** no API keys, no mapping file, no local paths, no identity mapping; transcripts published only after unmasking and review.

### B.11 Corrected treatment of four v0.1 claims

1. **"Small closed-system landscapes are essentially trap-free."** Overclaimed. The literature is contested and conditional. Pechen & Tannor (PRL 2011) exhibited second-order traps in a 3-level Λ system, "contrary to recent claims in the literature"; Rabitz et al. (PRL 2012) replied that those assertions were "inaccurate and misleading". For unitary-operator objectives, de Fouquieres & Schirmer (2013) found no traps over U(N) but traps once the domain is restricted to SU(N), removable by a phase-invariant index. Most relevant to our *constrained* setting, Moore & Rabitz (J. Chem. Phys. 2012) identified isolated trapping points and saddle regions when control constraints were significant, with prevalence increasing as controls or fluence were reduced. A trap-free theorem exists for the *unconstrained* qubit (Pechen & Il'in), but our objective is a bounded, piecewise-constant, fixed-duration, *ensemble-averaged* functional — none of those theorems apply to it. Corrected statement: *the landscape topology of this instance is unknown; no claim that gradient methods reach a global optimum is made, and no reference optimum is asserted.*

2. **"Exact simulation / no numerical tolerance."** Partly overclaimed. The piecewise-constant model is propagated by closed-form SU(2) exponentials, so there is no time-discretization or ODE-solver truncation error *within the model*. Floating-point rounding remains: roughly 10⁻¹⁶ per operation, accumulating over 12 products and 25 grid points to an infidelity resolution floor of order 10⁻¹⁴. Corrected statement: *closed-form propagation; numerical error limited to floating-point rounding; infidelity differences below 10⁻¹² are not interpretable.* The |a| → 0 branch of the exponential must use a series-safe form (a G1 test).

3. **"Retrieval proves X" (and the informed/blind ablation).** Withdrawn. Performance differences between prompt conditions do not identify mechanisms. No mechanism is claimed. Exploratory description only (B.13).

4. **"Finite multi-start GRAPE as a certified optimum."** Withdrawn. A best-of-restarts value is an *upper bound on the minimum infidelity*, not a certificate. The reference optimizer is removed under R1; should a reference ever be reintroduced, it is labelled "best known value".

### B.12 Statistical analysis (frozen procedure)

- **Unit:** seed s ∈ {0, …, 19}. Seed determines the initial batch (NumPy PCG64, seed s), the random-search stream (seed s + 10 000), and the CMA-ES RNG (seed s + 20 000). The LLM has no controllable seed; this is recorded.
- **Per-run outcome:** Y_arm(s) = log₁₀ max(I_best,260, 10⁻¹²).
- **Primary estimand:** Δ = median over seeds of D_s = Y_LLM(s) − Y_CMA(s). **Sign convention: Δ < 0 favors the LLM arm.**
- **Test:** exact two-sided Wilcoxon signed-rank on {D_s}, α = 0.05. One primary comparison; no multiplicity adjustment needed.
- **Uncertainty:** 95% percentile bootstrap CI on Δ, resampling seeds (10 000 draws, fixed bootstrap seed). Effect-size summary: fraction of seeds with D_s < 0.
- **Smallest effect size of interest (SESOI):** |Δ| = 0.3 decades (a factor of 2 in infidelity at fixed budget). Rationale: a factor-2 reduction in infidelity for the same number of evaluations is the smallest gain that would change a calibration budget; smaller gains are within typical run-to-run variability of hardware calibration and would not justify the added inference cost.
- **Decision categories (mutually exclusive, declared in advance):**
  1. *Superiority (meaningful):* CI upper bound < 0 **and** point estimate Δ ≤ −0.3.
  2. *Superiority (small):* CI upper bound < 0 and Δ > −0.3.
  3. *Inferiority:* CI lower bound > 0.
  4. *Equivalence:* CI entirely within [−0.3, +0.3] and includes 0.
  5. *Inconclusive:* none of the above.
  Categories 3–5 are all reported as "H1′ not supported in this instance"; only category 5 permits the phrase "underpowered at this precision", and only category 4 permits "no meaningful difference".
- **Precision rationale:** with n = 20 paired seeds, the exact Wilcoxon test at α = 0.05 has approximately 80% power for a standardized paired effect near 0.65; the per-seed SD of D_s is unknown before the run and is deliberately not estimated from any P data. Achieved CI half-width is reported. n = 20 is a resource-driven choice, not a power calculation, and is labelled as such.
- **Replication (permitted, same procedure):** seeds 20–39 run under the identical frozen procedure **only after** the primary analysis output has been produced and hashed. Same decision categories. A combined n = 40 analysis is prespecified as secondary. "H1′ supported in this instance" requires category 1 or 2 in **both** the primary and the replication set; anything else is reported as not supported, with both results shown.
- **Non-significance is not falsification.** A category-5 result is a failure to demonstrate, not evidence of absence.

### B.13 Exploratory (descriptive, no tests, labelled)

- Best-so-far curves per arm (median and IQR over seeds).
- Random-search arm alongside.
- Held-out grid: I evaluated on a 6 × 6 grid interleaved with the training grid, at each run's final θ_best. One number per run; reported as a distribution per arm.
- Similarity of final pulses to plain-π and BB1 encodings (e.g., normalized L² distance). Descriptive only.
- Forfeit, duplicate, and retry counts.

### B.14 Raw artifacts (all preserved regardless of outcome)

`config.json` (frozen instance), `env_manifest.txt`, `prompts/*.txt` + hashes, `runs/<arm>/<seed>/evals.jsonl` (raw; protected until unmasking), `transcripts/` (protected), `masked/analysis_dataset.csv`, `analysis/locked_script.py` + hash, `analysis/output.json` + hash, `EXPOSURE_LOG.jsonl`, `AMENDMENTS.md`, `mapping.sealed` (outside repo; hash only in manifest). Null and negative results are published with the same artifact set.

---

## Part C — Explanations and boundaries

### C.1 Technical rationale
The experiment is a paired, blinded, budget-matched comparison of two batch black-box optimizers on one deterministic 24-dimensional objective. The AI arm is formally a batch acquisition rule conditioned on history; CMA-ES is a rank-based Gaussian search-distribution update. Both consume identical evaluation slots and identical initial information. The estimand is a paired median log-ratio of best-found infidelity; the decision rule distinguishes meaningful superiority, small superiority, inferiority, equivalence, and inconclusiveness using a declared margin. Because the landscape topology of the constrained ensemble objective is unknown and no reference optimum is certified, all claims are relative to CMA-ES and specific to the instance.

### C.2 Educated-layperson explanation
Two automated "guessers" are each given the same 260 tries to find control settings that flip a simulated qubit reliably even when the hardware is slightly miscalibrated. One guesser is a standard, well-tested optimization algorithm; the other is a language model that is told the physics and shown all previous tries. A third "guesser" just picks at random, as a sanity check. Everything is scored by a fixed rule decided in advance; the scorer doesn't know which guesser is which; and we repeat with 20 different starting points, then again with 20 more. We only say the language model "did better" if it beats the standard algorithm by a pre-declared margin in both rounds. If it doesn't, we say so with the same detail.

### C.3 Speculative-commercial boundary
The only commercially relevant reading of a positive result is: "for this class of calibration-like tasks, an LLM proposer reduced the number of expensive evaluations by at least a factor equivalent to halving infidelity at fixed budget, compared with CMA-ES, in simulation." That does not transfer to hardware (noise is time-dependent, objectives are stochastic, leakage exists), does not compare against Bayesian optimization, and does not account for inference cost. A negative or inconclusive result has value as a documented, pre-registered null against a claim that is frequently made informally. No product or platform inference is licensed by either outcome.

### C.4 Strongest remaining alternative explanations for a positive result
1. **Retrieval of textbook sequences.** BB1 is representable in the feasible set and is in the model's training data. This is permitted under H1′ and is not distinguished from any other mechanism; it is disclosed and described exploratorily.
2. **Budget-regime artefact.** An advantage at B = 260 may vanish at larger B where CMA-ES converges. The claim is budget-specific by construction.
3. **Comparator choice.** CMA-ES at default settings may be weaker than BO or tuned CMA-ES at this B/d. The claim is comparator-specific.
4. **Information asymmetry in initialization.** CMA-ES uses only the best initial point as x₀; the LLM sees all 13. Both receive the same evaluated data; how each uses it is part of the method, but the asymmetry is disclosed.
5. **Feasibility-map interaction.** Disk projection creates flat regions in raw coordinates that may affect CMA-ES's step-size adaptation differently from the LLM's proposals. Disclosed; the map is identical for both.
6. **Stochastic-decoding variance.** A wide LLM outcome distribution could yield a favorable median by chance in one seed set; the mandatory replication addresses this partially.

### C.5 Strongest remaining alternative explanations for a null result
1. Prompt design, not the approach, is the limiting factor (a different prompt could differ; the claim is prompt-specific).
2. History length: late-batch prompts carry ~250 rows; degraded attention over long numeric tables is a known failure mode.
3. The problem instance may be near-saturated (both arms converge to similar values) or dominated by the shared initial batch.

---

## Part D — Items requiring measurement or authorization (not asserted)

- Installed versions of Python, numpy, scipy, cma (G4).
- Per-evaluation and per-run runtime (G3).
- Model ID and provider-default temperature value (G6).
- LLM interface latency and malformed-output rate on D (G3/G5).
- Existence of the authorization record (B.10).
- Custodian identity and mapping-file storage location (G7; not to be written in the public repository).

## Part E — Reference list (primary sources relied on)

- Pechen, A. N. & Tannor, D. J. *Phys. Rev. Lett.* 106, 120402 (2011). doi:10.1103/PhysRevLett.106.120402
- Rabitz, H., Ho, T.-S., Long, R., Wu, R. & Brif, C. Comment, *Phys. Rev. Lett.* 108, 198901 (2012); Pechen & Tannor Reply, 108, 198902 (2012).
- de Fouquieres, P. & Schirmer, S. G. *Infin. Dimens. Anal. Quantum Probab. Relat. Top.* 16, 1350021 (2013). doi:10.1142/S0219025713500215
- Moore, K. W. & Rabitz, H. Exploring constrained quantum control landscapes. *J. Chem. Phys.* 137, 134113 (2012). doi:10.1063/1.4757133
- Russell, B., Rabitz, H. & Wu, R. Control landscapes are almost always trap free: a geometric assessment. *J. Phys. A* 50, 205302 (2017); Zhdanov, D. V. Comment, *J. Phys. A* 51, 508001 (2018); Reply, 51, 508002 (2018).
- Pechen, A. N. & Il'in, N. Coherent control of a qubit is trap-free. *Proc. Steklov Inst. Math.* 285, 233–240 (2014).
- Cummins, H. K., Llewellyn, G. & Jones, J. A. Tackling systematic errors in quantum logic gates with composite rotations. *Phys. Rev. A* 67, 042308 (2003). doi:10.1103/PhysRevA.67.042308
- Wimperis, S. Broadband, narrowband, and passband composite pulses for use in advanced NMR experiments. *J. Magn. Reson. A* 109, 221–231 (1994).
- Hansen, N. The CMA Evolution Strategy: A Tutorial. arXiv:1604.00772; Hansen, N. & Ostermeier, A. *Evol. Comput.* 9, 159–195 (2001).
- Khaneja, N. et al. Optimal control of coupled spin dynamics: design of NMR pulse sequences by gradient ascent algorithms (GRAPE). *J. Magn. Reson.* 172, 296–305 (2005).
