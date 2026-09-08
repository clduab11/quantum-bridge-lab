# Pursuit decision review — 2026-09-08

**Type:** independent research assessment (Claude Science) of the Codex viability recommendation. **Not** a study execution, model preflight, install, freeze, or Project Context edit. No simulation, optimizer call, study-objective evaluation, or provider call was performed in producing this document. No candidate was evaluated on the study objective (an exposure event under protocol §1/§13.4).

**Reviewed inputs (verified this session)**

| Input | Location | Verification |
|---|---|---|
| Protocol v0.4 | project artifact `ai_quantum_control_protocol_v0.4.md` | SHA-256 recomputed = `0df9242fd2d0ad5d30b75ea91f498842ac68fe0df9616afd4c9c04518233eda5` (matches request) |
| Codex viability assessment | `research/VIABILITY_ASSESSMENT_2026-09-08.md`, branch `research/offline-preflight`, head `f1fb6bd7…` (2026-09-08T18:12Z) | SHA-256 `1f056acc…2814456d` |
| Codex readiness note | `research/IMPLEMENTATION_READINESS.md`, same branch | SHA-256 `faf3cdb8…dc26ac` |
| Five new source IDs | arXiv API, `export.arxiv.org` | titles, authors, dates confirmed for all five (see §8) |
| Companion document | `research_evidence_brief_v2.md` (version `dafe5cf4…`) | read for existing source IDs and evidence limits. `protocol_governance_v2.md` was **not** opened this session; its content is not relied on here |

Protocol-derived counts recomputed: 40 blocks × 19 batches = **760** scheduled proposal calls; ≤ 2 logical calls per batch → **1,520** logical-call ceiling; ≤ 3 transport attempts per logical call → **4,560** transport-attempt ceiling; 40 × 3 × 200 = **24,000** allotted slots. All four figures in the request and the Codex assessment are arithmetically correct and are ceilings/schedules, not measured usage.

---

## 1. Plain-language verdict

The repository is worth continuing **through the offline preflight**, which is already authorized, costs no provider money, and produces the one deliverable whose value does not depend on the outcome: a tested, auditable comparison harness. Whether to then pay for the two-stage study is a **separate** decision that should be taken only after the preflight has produced concrete token and cost ceilings — and it should be taken with the following understood:

- The scientific question as posed (does one stateless LLM emitting raw numbers beat one small-budget CMA-ES on one single-qubit robust-gate instance?) is **not new**. Two 2026 preprints already report that pure numeric LLM proposers are competitive-but-brittle against classical optimizers on continuous test functions (OPT-FRONTIER-BATCH-2026) and lose to CMA-ES in a fixed search space (OPT-CENTAUR-2026). This study would be a domain-specific, pre-registered replication of that question, not a first test.
- The design's decision rule gives a stage-level category only when the AI arm is strictly more than 2× better in at least 15 of 20 seed blocks (*Supports*) or in at most 5 of 20 blocks with none at the boundary (*Excludes*); a study-level statement needs the same category in **both** stages. For per-block probabilities in the middle range (roughly 0.3 to 0.7), the most likely study-level outcome is "inconclusive" (§4 below). That is a property of the design, not a prediction about the arms.
- No commercial thesis exists at this stage and no outcome of this experiment can create one (protocol §14.3; Codex agrees). Nothing in this review changes that.

So: Codex's provisional judgment — "worth a capped methods/learning study, weak standalone novelty/commercial thesis" — is **directionally right but too generous on the paid stage and too vague about where the value actually sits**. The learning value is concentrated in the offline preflight and the harness. The paid two-stage run adds a single inferential result whose most probable category is inconclusive and whose positive form would be weakly informative (weak comparator at this budget). Fund the paid run only if (a) the verified cost ceiling is small relative to the team's research budget, (b) the stationarity window is feasible, and (c) the team writes down, before exposure, what each of the three outcome categories would change about its next action. If the honest answer to (c) is "nothing differs between Excludes and Inconclusive", the paid run's expected value is low and stopping after the preflight is defensible.

---

## 2. Answers to the four requested questions

### (1) Strongest reason to stop now

Not novelty, and not the risk of losing. The strongest reason is **low decision reach per unit of cost and calendar time**:

1. *Prior evidence already points where this study can go.* OPT-FRONTIER-BATCH-2026 (posted 2026-09-02) and OPT-CENTAUR-2026 both report that pure numeric LLM proposers do not reliably beat classical optimizers. A replicated "Excludes" result would be consistent with the direction those papers report (it rules out only the prespecified lower-median 2× benefit for this configured pair, not benefit in general); a "Supports" result would be discounted by reviewers because the comparator is CMA-ES at 190 post-initialization evaluations in 20 dimensions with popsize 10 and no restarts — far below the evaluation counts at which CMA-ES is normally assessed (OPT-CMA-TUTORIAL is method documentation; no run was performed here, and protocol §14.4 already lists this alternative explanation). A positive result therefore risks the reading "LLM beat an under-budgeted optimizer", which does not move the field or the team.
2. *The design most likely returns "inconclusive" unless one arm dominates* (§4). An inconclusive result on a question the literature already leans on is the lowest-value outcome, and it is the modal one across a wide range of true effect sizes.
3. *External validity threats the team cannot control.* The LLM arm's per-block worst-case wait allowance is 35,150 s (protocol §7.2); across 40 blocks the deadline ceiling is 400 h. Actual latency is unknown until G-MODEL, but a multi-day execution window is plausible, and the stationarity assumption (§8.3) can be breached by a provider model or fingerprint change during that window, setting IVF and voiding confirmatory interpretation of the paid run. This risk is disclosed in the protocol but under-weighted in the Codex assessment's stop/continue reasoning.
4. *Opportunity cost.* The same engineering effort could build a harness that tests a question the literature has not already answered (e.g., the structure-plus-numerics or hybrid arms both 2026 quantum-control papers use). That is a new protocol, not an amendment — noted here only as the alternative use of effort, not as a proposal to change the current experiment.

### (2) Narrow contribution still worth funding

Two things survive the skeptical case, and they are different in kind:

- **Worth funding now (already authorized, no provider cost):** the offline preflight — analytic identities for the propagator and objective, the strict parser and literal prompts, durable failure/forfeit accounting with synthetic transport, the locked all-ordered-pairs analysis, and the custody sequence. This produces a reusable, auditable comparison harness whose value is independent of which arm wins and which is reusable for any later protocol. This is where most of the "learning" value Codex cites actually lives.
- **Conditionally worth funding (after G-COST/G-MODEL are concrete):** the two-stage confirmatory run as a **pre-registered, failure-preserving, cost-accounted replication** of the "pure numeric LLM vs classical optimizer" question in a quantum-control instance. Its publishable form is a short methods/negative-or-inconclusive-results note whose distinguishing features are the pre-registration, the mandatory replication stage, the distribution-free paired inference, and the complete failure/cost accounting — not the result. That is a modest but real contribution to a literature that currently reports mostly positive, unreplicated, single-seed-or-few-seed comparisons (OPT-CENTAUR-2026 uses three seeds per Codex's reading; not independently verified here beyond the abstract).

There is **no** standalone novelty contribution in the research question and **no** commercial contribution at any outcome.

### (3) Should the next bounded decision be "complete offline preflight, then assess full two-stage cost"?

**Yes — with two sharpenings.**

- The preflight should close with a written **token/cost ceiling** in the protocol's own terms (tokenizer-derived L_in, the 114 × (L_in + 8192) per-block total-token ceiling, provider billing categories) *and* a written **stationarity feasibility estimate** (expected wall-clock for both stages given measured per-call latency from E9, once E9 is permitted). A cost number alone does not make the go/no-go decision well-posed; the IVF risk is part of the price.
- Before any paid call, the team should record a **pre-exposure decision map**: for each of the nine possible stage-pair categories (Supports/Excludes/Inconclusive × two stages) plus the SVF/IVF case, what is the team's next action? This costs nothing, prevents post hoc rationalization, and is the only way to make "is the inferential question valuable enough to fund" (Codex milestone 2) an answerable question rather than a sentiment.

The Codex sequence (preflight → cost/authority gate → frozen evaluation → close regardless of outcome) is otherwise correct and consistent with the protocol's gate order (§13.2).

### (4) What evidence would justify a later larger investment?

For a **research** investment (a second, broader protocol — a new study, not an extension of this one):

- A valid two-stage **Supports** result with zero SVF/IVF, *and* forfeit/duplicate rates low enough that the LLM arm's endpoint is not dominated by the shared initial batch (reported per §9.6).
- Evidence from the reported per-arm cost accounting (§7.6) that the LLM arm's token and wall-clock costs per unit of infidelity improvement are within an order of magnitude of a classical alternative — not the same slot count, actual resources.
- Only then: a *new* pre-registered protocol with a stronger conventional comparator (larger CMA-ES budget or restarts, or a gradient-based method since the simulator is differentiable) and, if hybrids are of interest, an explicit hybrid arm — with the present study's exposure disclosed.

For a **commercial** investment: none of the above suffices. It would require time-dependent, stochastic noise with leakage, a hardware or representative calibration workflow, incumbent production baselines, and independently evaluated reliability (protocol §14.3; Codex "Commercial boundary"). No result of this experiment moves that needle, and the review agrees with Codex that the current design is not a commercial proposition.

For a **stop** decision: a replicated **Excludes** (both stages D₍₆₎ > −m, no SVF/IVF) is local evidence against the prespecified lower-median 2× benefit of this configured LLM proposer over this configured CMA-ES, and — because the comparator is under-budgeted — it would be a comparatively favorable setting in which that benefit did not appear. It does **not** show the hypothesis "failed" in any broader sense, and non-support is not exclusion: a stage whose interval merely fails to lie below −m (including one where the AI arm is 2× better in, say, 12 of 20 blocks) is *Inconclusive*, and an exclusion says nothing about benefits smaller than the margin or below the 10⁻¹² floor (protocol §0, §9.4). The asymmetry (a positive result weakened by the comparator budget; an exclusion informative for this pair) is the study's genuine falsification content.

Whether that content is worth paying for is a judgment, not a rule. **This review's recommendation for this team** is that the paid run is more attractive the more the team's current prior favors the AI arm (because an exclusion would then change a belief), the more the pre-exposure decision map (§2.3) shows different next actions across outcome categories, and the lower the verified cost and stationarity risk turn out to be. If the team already expects the AI arm not to show the 2× benefit, the paid run mainly buys a pre-registered replication of a direction the literature already reports; that can still be worth funding when it is cheap and when a replicated exclusion would close a decision the team would otherwise keep open, but it should be funded for that reason and no other.

---

## 3. Challenge to the Codex provisional judgment — points of agreement and disagreement

| # | Codex position | This review | Basis |
|---|---|---|---|
| A1 | Weak standalone novelty; five sources already cover LLM optimization, LLM quantum control, auditable workflows | **Agree**, and add: the research question is a domain-specific instance of what OPT-FRONTIER-BATCH-2026 and OPT-CENTAUR-2026 already tested. | arXiv abstracts verified 2026-09-08 |
| A2 | No commercial evidence; no outcome creates one | **Agree** | Protocol §14.3 |
| A3 | Stop/continue milestone sequence | **Agree** with the sequence; add pre-exposure decision map and stationarity feasibility to milestone 2 | Protocol §8.3, §12 |
| D1 | "Theoretical accounting ceiling is 24,000 allotted objective slots" is listed under cost | **Disagree on emphasis.** Objective slots are not a cost driver: 24,000 slots × 250 segment propagations = 6.0 × 10⁶ 2×2 unitary products — seconds to minutes on any laptop. The cost is entirely LLM inference (input grows with history: 1,900 history-row instances per block in scheduled proposal calls, 76,000 across 40 blocks, before template and output tokens) plus human time. Codex says this in the next sentence; the slot ceiling should not be headlined as a cost figure. | Protocol §2, §6.3, §7.2 arithmetic |
| D2 | "The experiment deliberately removes many capabilities for which LLMs may be most useful" is framed as a weakness | **Partly disagree.** For falsification, isolating the pure numeric proposer is the correct *first* test: a hybrid win would not identify the LLM's contribution (OPT-CENTAUR-2026's hybrid result is exactly the confounded case). The isolation is a strength for inference and a weakness only for external impact. Codex conflates the two. | Project constraints ("prefer falsification"); OPT-CENTAUR-2026 abstract |
| D3 | "A resource-limited 20+20 design can also end inconclusively" | **Agree but quantify.** The design's operating characteristic (§4) shows that for per-block probabilities in roughly the 0.3–0.7 range, "inconclusive in at least one stage" is the modal study-level outcome; resolution in both stages becomes more likely than not only toward the tails (e.g. 0.647 at p = 0.80). This should be stated numerically in any go/no-go record. | Binomial identity, protocol §9.3–9.5 |
| D4 | Stationarity/IVF risk not discussed in stop/continue | **Disagree by omission.** A multi-day execution window under an external provider makes IVF a material risk to the paid stage's validity, outside the team's control. | Protocol §7.2 deadline arithmetic, §8.3 |
| D5 | Recommendation: "continue through a small, rigorously completed first study" | **Narrow it.** Continue through the *preflight* unconditionally; treat the paid two-stage run as a separate decision gated on cost ceiling, stationarity feasibility, and the pre-exposure decision map. "Capped methods/learning study" is accurate for the preflight; for the paid stage the honest label is "pre-registered replication with modest publishable value and a likely inconclusive outcome". | §1–§2 above |
| D6 | LLAMBO cited as the prior-art anchor for history-conditioned LLM optimization | **Incomplete, not wrong.** OPRO (Yang et al., *Large Language Models as Optimizers*, arXiv 2309.03409, 2023-09-07; existence verified via arXiv API, not read here) is earlier and closer: it feeds (solution, score) history to an LLM and asks for new numeric solutions. Neither the evidence brief nor the Codex assessment cites any pre-2024 LLM-as-optimizer work. Proposed for the team's consideration as a source ID; **not adopted here**, since the request asked for no broad literature expansion. | arXiv API record |
| D7 | Characterizations of the five papers | **Consistent with abstracts.** In-text details Codex reports (three seeds; inference overhead excluded from budget in OPT-CENTAUR-2026; GP-EI comparator in OPT-FRONTIER-BATCH-2026) were **not** independently verified here beyond the abstracts. Codex's caution about the misattributed LLAMBO reproduction abstract is appropriate. | arXiv API abstracts |

---

## 4. Design operating characteristic (no data; binomial identity only)

This is **not** a power analysis computed from data and **not** a prediction about either arm. It restates protocol §9.3–9.5 as a function of an unknown per-block probability.

Let p = P(D < −m) for one block, m = log₁₀ 2, under the iid/stationarity model of §8.3. The protocol boundary is strict on both sides (§9.4): a stage is *Supports* iff D₍₁₅₎ < −m, i.e. at least 15 of 20 blocks have D strictly below −m; a stage is *Excludes* iff D₍₆₎ > −m, i.e. at least 15 of 20 blocks have D strictly above −m. A block with D exactly equal to −m contributes to neither count and therefore only toward *Inconclusive* (protocol §9.5: "endpoint equality with the margin is inconclusive"). The *Supports* column below is exactly P(Bin(20, p) ≥ 15). The *Excludes* column is written as P(Bin(20, p) ≤ 5), which equals P(Bin(20, q) ≥ 15) with q = P(D > −m) **only if there is no probability mass exactly at −m**; if such mass exists, q < 1 − p and the exclusion probability must be computed from q separately. Both stages are independent under the model.

| p (per-block AI ≥ 2× better) | P(stage Supports) | P(both stages Supports) | P(stage Excludes) | P(both stages Excludes) | P(stage Inconclusive) |
|---|---|---|---|---|---|
| 0.05 | 0.000 | 0.000 | 1.000 | 0.999 | 0.000 |
| 0.10 | 0.000 | 0.000 | 0.989 | 0.978 | 0.011 |
| 0.15 | 0.000 | 0.000 | 0.933 | 0.870 | 0.067 |
| 0.20 | 0.000 | 0.000 | 0.804 | 0.647 | 0.196 |
| 0.30 | 0.000 | 0.000 | 0.416 | 0.173 | 0.584 |
| 0.40 | 0.002 | 0.000 | 0.126 | 0.016 | 0.873 |
| 0.50 | 0.021 | 0.000 | 0.021 | 0.000 | 0.959 |
| 0.60 | 0.126 | 0.016 | 0.002 | 0.000 | 0.873 |
| 0.70 | 0.416 | 0.173 | 0.000 | 0.000 | 0.584 |
| 0.80 | 0.804 | 0.647 | 0.000 | 0.000 | 0.196 |
| 0.85 | 0.933 | 0.870 | 0.000 | 0.000 | 0.067 |
| 0.90 | 0.989 | 0.978 | 0.000 | 0.000 | 0.011 |

Interval coverage recomputed: 1 − 2·Σ_{j≤5} C(20,j)/2²⁰ = 0.9586, matching §9.3.

Reading: for per-block probabilities in roughly the 0.3–0.7 range, the modal study-level result is "inconclusive in at least one stage"; the probability that both stages return the same non-inconclusive category rises toward the tails (0.647 at p = 0.80, 0.870 at p = 0.85, and symmetrically for exclusion under the no-mass-at-margin condition). Two kinds of tie behave differently. Exact ties at D = 0 (both arms ending at the shared initial best) satisfy D > −m and so count toward *Excludes*; a saturating or forfeit-dominated instance therefore pushes toward Excludes, which is the protocol's stated behavior, not a defect. Exact ties at D = −m (a precisely twofold floored ratio) count toward neither category and push toward Inconclusive. None of this is a statement about what p actually is, and a stage that is neither Supports nor Excludes is Inconclusive — it is not a weak exclusion.

---

## 5. Cost: what can and cannot be said

**Cannot be said:** a dollar figure. No model identifier, provider, decoding configuration, tokenizer, context limit, or price is recorded (G-MODEL and G-COST open; protocol §6.1 forbids asserting them). Any dollar estimate now would require inventing a price and a token count, which the protocol and the request both prohibit. This review invents neither.

**Can be said (protocol-derived, exact):**

- Scheduled proposal calls: 760. Logical-call ceiling: 1,520. Transport-attempt ceiling: 4,560. Every dispatched attempt may be billed even if it returns no usable text (§7.3).
- Input size grows linearly with history: batch b of a block carries 10·b history rows (b = 1…19), so 1,900 row-instances per block and 76,000 across both stages in the scheduled path alone; correction calls repeat the same history plus a bounded reason line. If a mapped history row costs t tokens under the eventual tokenizer, scheduled proposal-call history input is 76,000·t tokens plus 760 × (template tokens). t is unknown until G-MODEL.
- Output ceiling: 8,192 tokens per attempt (§6.1); whether reasoning tokens count against it or are billed separately is provider-specific and unknown.
- Protocol total-token ceiling per block: 114 × (L_in + 8192), with L_in to be frozen from a verified tokenizer (§7.2).
- Wall-clock: per-arm per-block deadline 36,000 s; LLM-arm HTTP wait allowance 35,150 s per block. Ceilings only; expected latency unmeasured.
- Objective compute is negligible (6.0 × 10⁶ segment propagations at the full slot ceiling).

**Implication for the pursuit decision:** the paid stage's cost is dominated by 760–1,520 long-context LLM calls with a growing history, and by the calendar time those calls take under a 300 s per-attempt timeout. Whether that is trivial or material depends entirely on facts that G-MODEL/G-COST must establish; the preflight should close with those facts, not with the study.

---

## 6. Publishable contribution versus useful local learning

| | Publishable (modest) | Local learning (real, outcome-independent) |
|---|---|---|
| Content | Pre-registered three-arm comparison with mandatory independent replication stage, distribution-free paired lower-median inference with fixed margin, complete failure/forfeit/duplicate/cost accounting, sealed all-pairs analysis before unmasking; reported as a replication of the pure-numeric-LLM-vs-classical question in a quantum-control instance | Tested harness (propagator identities, strict parser, durable accounting, synthetic transport, locked analysis, custody sequence); measured malformed-output/forfeit/duplicate rates; provider contract knowledge (latency, token accounting, fingerprint stability); a worked example of the team's own governance standard |
| Depends on outcome? | Framing does; acceptability of a negative/inconclusive note is lower at main venues | No |
| Depends on paid run? | Yes | Mostly no — the preflight delivers most of it; forfeit/latency rates need E9 or the run |
| Realistic venue | Workshop paper, short methods note, or archived preprint with the harness as an open-source artifact | Internal; reusable in a later protocol |
| Novelty claim permitted | Design discipline and accounting, not the question or the result | None needed |

---

## 7. What this review did **not** do

- No evaluation of any control vector on the study objective (would be an exposure event).
- No CMA-ES, random-search, or simulator run; no provider smoke call; no install; no change to protocol v0.4, the evidence brief, governance document, Project Context, or any GitHub/Linear record.
- No dollar, token-count, latency, or model-setting estimate beyond protocol-derived counts and formulas.
- No literature expansion beyond verifying the five supplied arXiv records and confirming the existence of OPRO (2309.03409) as a candidate gap; OPRO was not read and is not adopted as a source ID here.
- No claim about which arm will win, or about p in §4.

---

## 8. Sources

Existing project source IDs relied on (from `research_evidence_brief_v2.md`; not re-fetched): BENCH-COCO-2016, OPT-CMA-TUTORIAL, PHY-KOSUT-2022, PHY-NIELSEN-2002, PHY-ZHANG-2025, STAT-ASA-2016, STAT-LAKENS-2022.

New shared source IDs (arXiv metadata verified 2026-09-08 via export.arxiv.org; abstracts read; full texts not read here):

| ID | Record | Used for |
|---|---|---|
| OPT-LLAMBO-2024 | Liu, Astorga, Seedat, van der Schaar. *Large Language Models to Enhance Bayesian Optimization*. arXiv:2402.03921v2, 2024-02-06 (upd. 2024-03-08) | History-conditioned LLM proposal within BO is prior art (A1, D6) |
| QCTRL-VF-2026 | Zhao et al. (13 authors). *Toward General Quantum Control with Physics-Informed Large Language Models*. arXiv:2605.26021v1, 2026-05-25 | LLM quantum control via analytic ansatz + refinement is prior art; structure/numerics separation differs from this protocol (A1, D2) |
| QCTRL-WORKBENCH-2026 | Chen, Zhang. *LLM-Driven Cross-Paradigm Design for Quantum Optimal Control*. arXiv:2607.17498v1, 2026-07-20 | Auditable LLM quantum-control workflow exists; removes "auditable workflow" novelty (A1) |
| OPT-FRONTIER-BATCH-2026 | Hu, Chennakesavalu, Graff. *Frontier LLMs are effective batch optimizers*. arXiv:2609.03177v1, 2026-09-02 | Direct prior art: zero-shot numeric batch optimization competitive but brittle vs classical (A1, §2.1) |
| OPT-CENTAUR-2026 | Ferreira, Wobbe, Krishnakumar et al. (5 authors). *Can LLMs Beat Classical Hyperparameter Optimization Algorithms? A Study on autoresearch*. arXiv:2603.24647v5, 2026-03-25 (upd. 2026-04-17) | Pure LLM < CMA-ES in fixed space; hybrid best — the confounded case the present isolation avoids (A1, D2) |

Candidate source not adopted: Yang, Wang et al. *Large Language Models as Optimizers* (OPRO), arXiv:2309.03409, 2023-09-07 — existence verified, not read (D6).

Repository documents: `research/VIABILITY_ASSESSMENT_2026-09-08.md` (SHA-256 `1f056accea18e4664932b043c0ec42288d0c0e66ca0eb1677c7bee7e2814456d`), `research/IMPLEMENTATION_READINESS.md` (SHA-256 `faf3cdb84734e4dd46f09ff97b3f0a6b5efaf84cc139d255bd46a624a2dc26ac`), branch `research/offline-preflight` at commit `f1fb6bd77dfcb9c9c6791bb9f7e84c969f927fea`. Their reported results are the papers' own; none is treated as settled, and none is this project's result.

---

## 8a. Revision log

- **v1 → v2:** provenance table corrected — `protocol_governance_v2.md` was not opened this session.
- **v2 → v3 (this version; corrections requested by Codex before adoption):** (i) removed the internally inconsistent claim that inconclusive is modal unless p ≳ 0.85; the table's own value P(both Supports) = 0.647 at p = 0.80 contradicted it. The statement is now confined to the defensible middle range (~0.3–0.7). (ii) Decision-rule boundaries stated as strict (D₍₁₅₎ < −m; D₍₆₎ > −m); exact twofold-boundary ties contribute only to Inconclusive, unlike D = 0 ties, which count toward Excludes. (iii) p defined as P(D < −m); the Excludes column's dependence on the no-mass-at-margin condition made explicit, with instruction to compute from q = P(D > −m) otherwise. (iv) Removed wording equating inability to reach 15/20 with a "failed" hypothesis; non-support is not exclusion, and exclusion concerns only the prespecified lower-median 2× benefit for this configured pair. (v) "Only worth paying for if the prior favors the AI arm" reframed as this review's recommendation, weighed against decision relevance and verified cost/stationarity risk, rather than as a necessary condition. Cost and stationarity concerns are unchanged. Protocol v0.4 and Project Context were not modified.

---

## 9. Communication-rule summary

**Technical.** The v0.4 design is a sound falsification instrument for one narrow question whose literature prior is already unfavorable to the tested arm. Its decision rule requires ≥ 15/20 blocks strictly beyond the 2× floored-infidelity margin on the same side, in each of two independent stages, with exact-margin ties contributing only to inconclusiveness; for per-block probabilities between ~0.3 and ~0.7 the modal study-level outcome is inconclusive. The comparator's 190-evaluation budget in 20-D makes a positive result weakly informative and a replicated exclusion informative for this configured pair only; non-support is not exclusion. Cost is dominated by 760–1,520 growing-context LLM calls and cannot be priced until G-MODEL/G-COST close. Stationarity over a multi-day window is a material IVF risk.

**Layperson.** The plan is a fair, carefully refereed race between an AI that guesses numbers and a standard optimizer that tunes them, on one small quantum problem. Two new papers from this year already suggest the AI usually does not win such races. The race only declares a winner if one side wins by a wide margin in almost every heat; otherwise it says "can't tell". Building the racetrack (the preflight) is cheap and useful regardless. Paying to run the race is a separate choice that should wait until we know what each lap costs and what we would do differently after each possible result.

**Commercial relevance.** None now; none from any outcome of this experiment. A later product hypothesis about reducing expert calibration time on real hardware would need a different experiment with hardware-realistic noise and production baselines.

**Potential flaws in this review.** The §4 table assumes iid blocks, and its *Excludes* column assumes no probability mass exactly at −m (otherwise it must be recomputed from q = P(D > −m)); correlated LLM blocks (shared provider state) would make the interval anti-conservative and the table optimistic about resolution. The "under-budgeted comparator" argument rests on general CMA-ES method documentation, not on a run of this instance (a run is prohibited before freeze). In-text details of the five papers were checked only against abstracts. The judgment that the literature prior is "unfavorable to the tested arm" rests on two 2026 preprints in different domains; a quantum-control instance could differ, which is exactly what the study would test — the point is that the test is a replication, not that its outcome is known.
