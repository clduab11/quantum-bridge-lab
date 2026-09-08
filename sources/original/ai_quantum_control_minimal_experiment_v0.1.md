# Minimal Experiment: Can AI-Guided Search Find Quantum-Control Strategies More Efficiently Than Conventional Optimizers?

**Status:** Design / pre-registration draft v0.1 — no data collected.
**Scope:** One simulated system, one control problem, one AI strategy, three classical baselines, fixed evaluation budget.
**Guiding rule:** Prefer falsification. Every criterion below is fixed before the first run.

---

## 1. Critical evaluation of the hypothesis

### 1.1 The hypothesis as stated

> "AI may serve as a translation layer between classical computing and quantum systems."

As stated this is not testable: "translation layer" does not name a measurable quantity, and "AI" does not name a method. Before anything can be falsified it must be reduced to an operational claim. The narrowest defensible reduction consistent with the project's stated priority is:

> **H1 (operational):** Under a fixed budget of *B* simulator evaluations, an LLM-in-the-loop optimizer proposing control parameters reaches lower gate infidelity than standard derivative-free optimizers on the same problem, and the gain is reproducible across seeds and across small changes to the problem.

Everything below tests H1. If H1 fails, the broader "translation layer" idea is not refuted, but it loses its simplest supporting evidence and should not be pursued further without a different operationalization.

### 1.2 Why H1 is *a priori* unlikely in the obvious form — and where it could still be true

- **Small closed-system quantum-control landscapes are essentially trap-free.** For unconstrained control of small systems, gradient methods (GRAPE, Krotov) reach the theoretical optimum reliably. No proposer, AI or otherwise, can beat the optimum on *final* fidelity. The only meaningful axes of comparison are therefore **(a) sample efficiency** (how many evaluations to reach a given fidelity) and **(b) performance in non-ideal settings** (constraints, robustness requirements, noise, non-differentiable objectives).
- **Sample efficiency only matters when evaluations are expensive.** In a simulator, evaluations cost microseconds; the argument for an AI proposer rests entirely on the *analogy* to hardware, where each evaluation is a real shot sequence. The experiment must therefore impose an artificial evaluation budget and treat it as the binding constraint. This is a modelling choice and should be stated as such.
- **The strong incumbent in the expensive-evaluation regime is Bayesian optimization, not random search.** An AI method that beats random search but not Bayesian optimization or CMA-ES has demonstrated nothing — Nelder–Mead also beats random search.
- **Where an LLM could genuinely help:** it carries prior knowledge of the physics (composite pulses, DRAG, robustness structure) and can reason about *why* a proposal failed. That is a real, different information source from what a GP or evolution strategy has. Whether that prior transfers into fewer evaluations is an empirical question, and it is exactly the one worth answering.

### 1.3 Weakest assumptions (ranked, most fragile first)

| # | Assumption | Why it is fragile | How the design addresses it |
|---|---|---|---|
| A1 | "AI-guided reasoning" is a distinct method rather than a black-box optimizer with a strong prior | An LLM proposing parameter vectors *is* a derivative-free optimizer. The only way to isolate "reasoning" from "prior knowledge" is an ablation. | Two LLM arms: **physics-informed** (told it is a qubit with detuning/amplitude error) and **obfuscated** (told only "maximize *f*: ℝ^d → [0,1]"). If only the informed arm wins, the mechanism is prior knowledge, not in-context reasoning. |
| A2 | The problem is hard enough that the prior matters but not so easy that gradients solve it trivially | Textbook single-qubit gates are trivial; heavy noise makes everything look equal. | Robust-control objective over an error ensemble plus an amplitude bound. GRAPE with unlimited budget defines the attainable optimum; all results reported as fraction of that optimum. |
| A3 | Literature leakage does not inflate the AI arm | Composite pulses (BB1, CORPSE, SK1) are in the LLM's training data. "Discovering" them is retrieval. | This is *permitted* under H1 (the hypothesis is about efficiency, and prior knowledge is a legitimate mechanism), but it is **labelled**: the ablation in A1 quantifies how much of the gain is retrieval. A sensitivity variant uses a non-textbook target rotation (e.g. axis tilted 23° in the x–z plane, angle 0.7π) to reduce direct recall. |
| A4 | Evaluation budget is the right cost model | Counting only simulator calls ignores LLM inference cost, which dominates in wall-clock and dollars. | Primary metric uses simulator evaluations (hardware-analogous). Secondary table reports wall-clock and token cost so the trade-off is visible, not hidden. |
| A5 | The LLM arm is reproducible | LLM sampling is stochastic; model versions change; identical prompts do not give identical outputs. | Fixed prompt template (versioned, hashed), fixed temperature, model ID recorded, *n* = 20 independent runs per arm, all transcripts saved. Reproducibility is assessed *statistically* (distribution of outcomes), not by exact replay. |
| A6 | No researcher degrees of freedom | Choosing the metric, budget, or problem variant after seeing results invalidates the comparison. | All criteria (§7–8) fixed in this document before the first run. Any change is logged as a protocol amendment. |
| A7 | Median-of-seeds is the right summary | LLM runs may be bimodal (occasional brilliant proposal, frequent failure). | Report full distributions; primary test is rank-based (Mann–Whitney); also report fraction of runs reaching a threshold. |

---

## 2. Simplest possible simulation environment

**System:** one qubit (two-level system), closed dynamics (no dissipation) in the rotating frame.

**Hamiltonian** (units ħ = 1, Rabi frequency normalized so Ω_max = 1):

H(t) = ½ [ (1+ε) (u_x(t) σ_x + u_y(t) σ_y) + δ σ_z ]

- u_x(t), u_y(t): piecewise-constant controls, *N* segments, total time *T*.
- ε: quasi-static amplitude (Rabi) error, ε ∈ {−0.10, −0.05, 0, +0.05, +0.10}.
- δ: quasi-static detuning error, δ ∈ {−0.20, −0.10, 0, +0.10, +0.20} (in units of Ω_max).
- Constraint: |u_x(t)|² + |u_y(t)|² ≤ 1 at all times (enforced by clipping in the simulator, so every proposal is feasible).

**Propagator:** U = Π_k exp(−i H_k Δt), computed with exact 2×2 exponentials (closed form via Pauli algebra; no ODE solver, no numerical tolerance to tune).

**Why this and nothing more:**
- 2×2 matrices → each evaluation is ~25 matrix exponentials; the entire experiment runs on a laptop in minutes (excluding LLM calls).
- No Lindblad dissipation: it would add a time–fidelity trade-off (a second objective) and more parameters. Can be a later variant.
- No stochastic noise in the objective: the ensemble is a fixed grid, so *f* is deterministic. Reproducibility of the *problem* is exact; all stochasticity is in the *optimizers*, where it belongs.
- Robustness over a 5×5 error grid is what makes this non-trivial: a naïve π pulse has poor average fidelity here, and the known good solutions (composite pulses) are structured and non-obvious to local search.

**Dependencies:** `numpy`, `scipy` only. No QuTiP, no PennyLane, no Qiskit. (The project's existing `qcore-quantum-env` is heavier than needed; a plain `python` environment suffices.)

---

## 3. The one measurable control problem

**Task:** implement a target unitary U_target with a robust piecewise-constant pulse.

**Primary target:** X gate (π rotation about x), U_target = σ_x. Chosen because (i) it is the canonical robust-control benchmark, (ii) known composite solutions exist so the attainable optimum is well understood, (iii) it exposes the leakage issue (A3) honestly rather than hiding it.

**Decision variables:** θ = (u_x,1 … u_x,N, u_y,1 … u_y,N) ∈ [−1, 1]^{2N}, with **N = 10** segments → d = 20 dimensions. Total time **T = 4π / Ω_max** (enough for a ~4-pulse composite sequence; forces a real trade-off rather than allowing arbitrary length).

**Objective (to minimize):** ensemble-averaged gate infidelity

I(θ) = 1 − (1/25) Σ_{ε,δ} | Tr(U_target† U(θ; ε, δ)) / 2 |²

Range [0, 1]. Deterministic. One evaluation = one call to I(θ).

**Reference optimum:** I* obtained by GRAPE (analytic gradients, 200 random restarts, unlimited evaluations). All methods reported as I(θ_best) and as excess infidelity I(θ_best) − I*.

**Sensitivity variants (pre-specified, run only after the primary result):**
- V1: N = 6 (d = 12) and N = 16 (d = 32).
- V2: target = Hadamard; target = non-textbook rotation R(n̂ = (sin 23°, 0, cos 23°), 0.7π) — reduces direct recall.
- V3: error ensemble widened to δ ∈ ±0.3, ε ∈ ±0.15.
- V4: budget B ∈ {50, 100, 200, 400}.

---

## 4. The one AI-guided strategy

**LLM-in-the-loop batch proposer (LLM-BP).**

Loop until budget B is exhausted:
1. Prompt the model with: the problem description (see arms below), the full history of (θ, I(θ)) pairs sorted by I, the remaining budget, and a request for **K = 10** new parameter vectors in a strict JSON schema.
2. Parse; reject/resample malformed vectors (count rejections; they do not consume simulator budget but are reported).
3. Evaluate the K vectors; append to history.

**Two arms (the ablation that makes this an experiment rather than a demo):**
- **LLM-BP-informed:** told it is designing a robust X-gate pulse on a qubit with quasi-static detuning and amplitude errors, with the Hamiltonian written out.
- **LLM-BP-blind:** told only "maximize a deterministic black-box function f: [−1,1]^20 → [0,1]; here is the history."

**Fixed settings:** one model ID (recorded); temperature 0.7 (recorded; sensitivity check at 0.2); identical prompt template for all runs within an arm (template versioned and SHA-256 hashed into every results row); no tool use, no code execution by the model — it proposes numbers only. This keeps the LLM strictly comparable to the baselines: same information (history), same action space (parameter vectors), same budget.

**Explicitly excluded (would confound):** letting the LLM write and run its own optimizer; giving the LLM gradient information; letting the LLM see baseline results; multi-model ensembles.

**Runs:** n = 20 independent runs per arm (different random initial batch; the first K = 10 evaluations are the same random points used to seed every method in that seed group).

---

## 5. Classical baselines (three tiers)

All baselines receive the identical budget B, identical initial K = 10 random evaluations per seed, identical box constraints, n = 20 seeds.

| Tier | Method | Role | Implementation |
|---|---|---|---|
| B0 | **Random search** (uniform in box) | Floor. Necessary for sanity; **beating it is not evidence for H1.** | `numpy` |
| B1 | **CMA-ES** (default hyperparameters, population λ = 10 to match K) | Standard strong derivative-free optimizer; the honest "conventional method" for d = 20 | `cma` package (pip) |
| B2 | **Bayesian optimization** (GP, Matérn-5/2, expected-improvement, batch of 10 via constant-liar or q-EI) | Incumbent method for expensive-evaluation regimes; the baseline the AI arm must beat for H1 to have content | `scikit-optimize` or a ~60-line `scipy` GP |
| B3 | **Nelder–Mead** (scipy, restarts on stall) | Ubiquitous "lab default" optimizer; included because it is what many experimental groups actually use | `scipy.optimize` |
| Ref | **GRAPE** (analytic gradient, unlimited budget) | Not a competitor — defines I*. Also reported at budget B with finite-difference gradients (2d+1 = 41 evaluations per step) to show what a gradient method does when starved. | `scipy.optimize.minimize(L-BFGS-B)` |

Minimum required for the experiment: B0 + B1 + B2. B3 and starved-GRAPE are cheap additions and are included.

---

## 6. Design of the comparison

- **Primary endpoint:** best-so-far infidelity at budget **B = 200**, I_200 = min over evaluated θ of I(θ), per run. Distribution over n = 20 seeds per method.
- **Secondary endpoints:** (i) area under the best-so-far curve (sample efficiency across all budgets); (ii) evaluations-to-threshold, threshold = I* + 0.01 (censored at B if not reached); (iii) fraction of runs reaching threshold; (iv) wall-clock and, for LLM arms, total tokens.
- **Seed pairing:** each seed *s* fixes the initial 10 random points for every method → paired comparison, reduces variance.
- **Statistics (pre-specified):** two-sided Mann–Whitney U on I_200 between LLM-BP-informed and the best-performing classical baseline (chosen by median I_200 — i.e., the comparison is against whichever baseline is strongest, decided by data, which is conservative). Effect size: Cliff's δ. Significance level α = 0.01 for the primary comparison; Holm correction across the sensitivity variants. Bootstrap 95% CIs (10 000 resamples) on median differences.
- **Replication:** the entire primary comparison is run twice with disjoint seed sets (seeds 0–19, then 100–119). Both must individually satisfy the success criterion.

---

## 7. Objective success criteria (all must hold)

S1. **Primary effect:** median I_200 (LLM-BP-informed) < median I_200 (best classical baseline), Mann–Whitney p < 0.01, Cliff's δ ≥ 0.33 (at least a "medium" effect).

S2. **Replication:** S1 holds independently on the second disjoint seed set.

S3. **Sensitivity:** S1 direction holds (median lower, p < 0.05 after Holm) in at least 3 of the 4 sensitivity variants V1–V4 (each variant tested at its own conditions; V1 and V4 count as satisfied if the majority of their sub-conditions hold).

S4. **Not merely a floor effect:** the best classical baseline itself must reach median I_200 < 0.1 (i.e., the problem is solvable within budget by conventional means; otherwise the comparison is between methods that all failed).

S5. **Mechanism labelled:** the report states the LLM-BP-blind result alongside the informed one. If blind ≈ informed, the gain is attributable to in-context reasoning over the history; if blind ≈ baselines and informed ≫ baselines, the gain is attributable to physics prior knowledge. Either is a valid result under H1, but the paper must say which.

**Interpretation if S1–S5 hold:** H1 is *provisionally supported* for this problem class. The claim licensed is exactly: "On a d = 20 robust single-qubit gate design task under a 200-evaluation budget, an LLM proposer reached lower infidelity than CMA-ES / BO / Nelder–Mead / random search, reproducibly." Nothing about hardware, nothing about scale, nothing about "translation layers" in general.

---

## 8. Objective failure criteria (any one suffices)

F1. Mann–Whitney p ≥ 0.01 or Cliff's δ < 0.33 on the primary comparison (no significant or only small effect vs. the strongest baseline).

F2. S1 holds on seed set 1 but not on seed set 2 (non-replication).

F3. S1 holds on the primary problem but fails in ≥ 2 of 4 sensitivity variants (fragile effect).

F4. LLM-BP-informed beats random search but not CMA-ES or BO (this is the *expected* null outcome and must be reported as failure, not as partial success).

F5. LLM-BP-informed wins only because of proposals that reproduce a textbook composite sequence verbatim **and** the non-textbook target variant (V2) shows no advantage. This is recorded as "retrieval, not efficiency" — a failure of H1 as an efficiency claim, though a documented capability.

F6. Malformed-output rate > 20% in either LLM arm (the method is not operationally reliable enough to compare fairly).

**Pre-committed reporting rule:** failures are published with the same detail as successes. Contradictory results between variants are tabulated, not averaged away.

---

## 9. Explanations

### 9.1 Technical

We frame quantum control as black-box optimization of a deterministic, bounded objective (ensemble-averaged gate infidelity) over a 20-dimensional box, under a hard evaluation budget that emulates the cost of hardware calibration shots. The AI arm is an LLM used as a batch acquisition function: it maps the observation history to the next batch of query points. This places it in the same formal class as Bayesian optimization (a GP surrogate + acquisition rule) and CMA-ES (a Gaussian search distribution updated by rank-based selection), which is why those are the correct comparators. The physics-informed / blind ablation separates two possible information advantages: a domain prior (knowledge that robust rotations are achieved by compensating sequences) and in-context inference over the observed landscape. The GRAPE optimum anchors the scale so that "improvement" is measured in excess infidelity, not raw fidelity, which prevents inflated claims from easy targets.

### 9.2 Layperson

Imagine tuning a radio knob to get the clearest signal, but the radio is slightly miscalibrated in ways you can't see, and every time you try a setting it costs you real money. We are asking: can a language model, told what the problem is and shown the results so far, suggest the next settings to try more cleverly than the standard automatic tuning algorithms engineers already use? The "quantum" part is that the knob controls a single quantum bit and the goal is to flip it reliably even when the hardware is a bit off. We simulate the qubit exactly on an ordinary computer, so there's no quantum hardware involved — the question is purely about whether the AI is a better *guesser* under a strict budget of guesses. We compare it against three standard methods and a coin-flip method, run everything twenty times with different starting points, repeat the whole thing again, and decide in advance what counts as a win.

### 9.3 Potential commercial relevance

Calibration of quantum processors is a recurring, shot-expensive, largely automated process (every qubit, every gate, re-tuned regularly). If an LLM proposer measurably reduces calibration shots relative to BO/CMA-ES, that is a direct cost lever for hardware operators and a plausible product surface for a "calibration copilot." If it does *not*, the result still has value as a documented negative for a claim that is frequently made loosely in the field. Either outcome is small but real; neither justifies the phrase "translation layer" on its own.

### 9.4 Potential flaws and alternative explanations

- **Retrieval, not reasoning** (A3/F5): the LLM may simply emit BB1/CORPSE. The V2 non-textbook target and the blind arm are the controls, but they are imperfect — the model may generalize known pulse structure to nearby targets.
- **Budget-regime artefact:** an advantage at B = 200 may vanish at B = 1000, where CMA-ES and BO have room to converge. V4 tests this; the claim must be stated as budget-specific.
- **Baseline tuning asymmetry:** default CMA-ES/BO hyperparameters vs. a hand-written prompt. Mitigation: report baseline results with one round of standard tuning (BO length-scale priors, CMA-ES σ₀) and state that the prompt was fixed before any results were seen. Perfect symmetry is not achievable; the asymmetry is disclosed.
- **Simulator-hardware gap:** quasi-static errors are the friendliest noise model; time-dependent noise, leakage to a third level, and measurement noise (stochastic objective) could all reverse the ranking. Out of scope by design; stated as the main external-validity limit.
- **Model drift:** results are tied to a model ID and date. A replication six months later with a newer model is a *different* experiment. Transcripts are archived so the original can be audited.
- **Multiple comparisons:** four baselines, two LLM arms, four variants. Handled by pre-specifying one primary comparison and Holm-correcting the rest.
- **Simplest alternative explanation of a positive result:** the LLM acts as a well-regularized random-restart heuristic that happens to suit a smooth, low-dimensional landscape. Distinguish by checking whether the blind arm shows the same gain and whether proposals cluster in structured regions (report proposal diversity).

---

## 10. Smallest implementation for Claude Science + Zed

**Repository layout (~400 lines total, plain Python):**

```
qctrl-min/
  README.md                 # this document + how to run
  PREREGISTRATION.md        # §3, §6–8 frozen; SHA-256 recorded in results
  qctrl/
    sim.py                  # Hamiltonian, closed-form 2x2 propagator, infidelity I(θ); ~80 lines
    problems.py             # primary problem + variants V1–V4 as dataclasses; ~40 lines
    baselines.py            # random, CMA-ES, BO, Nelder-Mead, GRAPE(ref); ~120 lines
    llm_proposer.py         # LLM-BP informed/blind; prompt templates; JSON parsing; ~100 lines
    runner.py               # budget loop, seed pairing, CSV logging; ~60 lines
    analyze.py              # Mann-Whitney, Cliff's δ, bootstrap CIs, best-so-far plots; ~80 lines
  prompts/
    informed_v1.txt
    blind_v1.txt
  results/                  # one CSV row per (method, seed, evaluation): θ, I, cumulative best, wall-clock, tokens
  tests/
    test_sim.py             # analytic checks: ideal π pulse → I=0 at ε=δ=0; unitarity; determinism
```

**Environment:** the default `python` env plus `pip install cma scikit-optimize` (both small). No quantum SDK.

**LLM access:** from Claude Science, `host.llm(...)` with `model=host.reasoning_model()` recorded into the results; from Zed, the same code path via the Anthropic SDK reading an API key from the environment. The proposer module should take a `call_fn(prompt) -> str` argument so both entry points share identical logic.

**Compute cost estimate:**
- Simulator: 25 exponentials × 200 evals × 20 seeds × 6 methods ≈ 6 × 10⁵ 2×2 exponentials — under a minute locally.
- GRAPE reference: 200 restarts × ~500 gradient steps — a few minutes.
- LLM: 20 calls/run × 20 seeds × 2 arms × 2 replications = 1 600 calls for the primary result; sensitivity variants at n = 10 add ~1 600 more. Each call carries ≤ 200 history rows (≈ 6–8k tokens). Total on the order of 25M input tokens — the dominant cost; run in background and checkpoint after every call.

**Order of work (each step is a stopping point with a saved artifact):**
1. `sim.py` + tests; verify ideal π pulse and that a known BB1 sequence achieves low ensemble infidelity (validates the simulator against a known result — this is a check, not a result).
2. GRAPE reference optimum I* for the primary problem; save.
3. Baselines B0–B3 at B = 200, n = 20, seed set 1. Confirm S4 (problem solvable). **If S4 fails, redesign the problem before touching the LLM arm.**
4. LLM-BP-blind, then LLM-BP-informed, seed set 1. Analyze against pre-registered criteria.
5. Replication on seed set 2.
6. Sensitivity variants V1–V4 (n = 10).
7. Report with full distributions, all failures, transcript archive.

**What not to build:** a dashboard, a plugin architecture, multi-qubit systems, hardware backends, multiple LLM providers, RL agents. Any of these can be a follow-up *if* step 5 succeeds.

---

## 11. Open decisions to confirm before freezing the pre-registration

1. Budget B = 200 and K = 10 (batch) — acceptable, or should the primary budget be smaller (B = 100) to bias toward the regime where the AI prior should matter most?
2. Temperature 0.7 as primary with 0.2 as sensitivity — or the reverse?
3. Should the informed prompt include the Hamiltonian explicitly (maximal prior) or only a verbal description (moderate prior)? Recommendation: explicit Hamiltonian; it is the strongest fair version of the hypothesis.
4. Model choice: the session's reasoning-class model, recorded by ID. A second model is out of scope for the minimal experiment.
