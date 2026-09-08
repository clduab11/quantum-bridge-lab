# Independent median inference review

Reviewed 2026-09-08. Scope: the Round 2 candidate interval and its decision logic only. No simulations, experiment code, or empirical results. Numerical values below come from finite binomial arithmetic.

## Verdict

For **20 iid, finite, real-valued seed-block differences**, sorted with multiplicity as `D_(1) <= ... <= D_(20)`, the **closed interval `[D_(6), D_(15)]` is valid** for any fixed population median, with coverage **at least 0.9586105346679688 (95.8610534668%)**. The lower bound remains valid with ties and atoms. It is not generally exactly 95%, and it does not require symmetry or continuity. Calling the coverage exactly 95.861% requires the additional no-mass-at-the-target-median condition yielding equal half probabilities on both sides.

## Definition and derivation

Define a population median `theta` by `P(D <= theta) >= 1/2` and `P(D >= theta) >= 1/2`. If a single numeric estimand is required, explicitly freeze a convention, such as the lower 0.5 quantile `theta = inf{x : F_D(x) >= 1/2}`. Do not silently assume uniqueness: even a continuous distribution can have a flat CDF at 1/2 and multiple medians. The interval argument applies to any fixed median chosen independently of the sample.

Let `A = #{i: D_i <= theta}` and `C = #{i: D_i < theta}`. Then `A ~ Binomial(20,p_le)` with `p_le >= 1/2`, and `C ~ Binomial(20,p_lt)` with `p_lt <= 1/2`.

- The lower-end failure `D_(6) > theta` is `A <= 5`, whose probability is at most `q = P(Binomial(20,1/2) <= 5)` by binomial monotonicity.
- The upper-end failure `D_(15) < theta` is `C >= 15`, also of probability at most `q` by monotonicity and binomial symmetry.
- These two failure events are disjoint. Hence coverage is at least `1 - 2q`.

Exact arithmetic:

`sum(j=0..5) choose(20,j) = 1 + 20 + 190 + 1140 + 4845 + 15504 = 21700`.

`q = 21700 / 1048576 = 0.020694732666015625`.

`1 - 2q = 1005176 / 1048576 = 0.9586105346679688`.

This proof, rather than a borrowed continuous-distribution formula alone, justifies the conservative claim for atoms. Keep every planned finite difference, including zeros and ties, and sort with multiplicity. Do not jitter ties, discard zeros, interpolate endpoints, change the rank indices after results, or reduce n by dropping failed algorithm blocks. A simulator failure that prevents a finite defined endpoint must follow the separate study-validity failure rule; this interval cannot repair missing outcomes by itself.

## Margin logic in the proposed direction

For `D = log10(max(I_AI,1e-12)) - log10(max(I_CMA,1e-12))`, negative favors AI. Let `c = -log10(2)`, `L = D_(6)`, and `U = D_(15)`.

- `U < c`: support a population median below the prespecified threshold. Equivalent to at least **15 of 20 differences strictly below c**. Under a fixed-median null `theta >= c`, probability of this false directional conclusion is at most q.
- `L > c`: exclude a population median at or below this threshold. Equivalent to at least **15 of 20 differences strictly above c**. Under `theta <= c`, probability of this false directional conclusion is at most q.
- Otherwise: inconclusive. In particular, equality of either endpoint to c does not satisfy either strict decision rule.

The threshold is a declared research relevance choice. The estimand concerns the paired, floored objective ratio on the fixed instance and specified block-generating process. It is not a difference of marginal medians, a mean-ratio guarantee, an equivalence conclusion, a hardware-cost result, or a guarantee of fewer evaluations. The floor creates possible atoms and changes the estimand; its numerical justification is separate from validity of this rank interval.

## Two stages and interpretation

Always completing both prespecified n=20 stages prevents outcome-conditioned continuation. It does **not** automatically give joint 95% confidence coverage. Under independent stages from the same distribution:

- Each stage has at least 95.8610534668% coverage.
- The probability both intervals cover the common median is at least `(1-2q)^2 = 0.9189341571764089`, **not 95%**. Without independence the union-bound guarantee is only `1-4q = 0.9172210693359375`.
- If the study requires **both stages** to satisfy `U < c` for replicated support, the false replicated-support probability under the same null `theta >= c` is at most `q^2 = 0.0004282719601178542`, provided stage independence holds. The analogous bound applies to both stages excluding benefit under `theta <= c`. These are operating-characteristic bounds for the specified conjunction, not confidence levels or posterior probabilities.
- Define the complete study-level combination rule before outcomes. A coherent candidate is replicated support only when both stages support; replicated exclusion only when both exclude; all other combinations reported explicitly as inconclusive or discordant. Do not silently choose whichever stage is favorable, pool after looking, or describe a mixed outcome as replicated support.

The iid assumption concerns whole independently generated seed blocks, not the 200 adaptive objective evaluations inside a run or 25 deterministic ensemble members. Fixing a pseudorandom seed list gives reproducibility; it does not prove iid sampling. Exact probability statements are conditional on the stated seed-block sampling and stationarity model. API model drift, shared hidden run state, dependent initialization draws, or time-related changes can invalidate a common iid distribution and the q-squared replication bound. State these limits; do not claim empirical confirmation of them before runs.

N=20 determines coarse rank coverage, not a guaranteed interval width in log-infidelity units or 80% power. Width and power depend on the unknown distribution around the median/margin.

## Evidence provenance

Exa verification on 2026-09-08: `sources_reviewed: 5` (one search with `numResults: 5`, no search retries); two full source URLs fetched. Added to the prior statistical workstream's 15, the cumulative workstream search counter is **20**. Nonprimary tutorial results were not used.

- **STAT-GEYER-2007**, Charles J. Geyer, *Stat 5102 Notes: Nonparametric Tests and Confidence Intervals*, sections 1.1–1.3: https://www.stat.umn.edu/geyer/s06/5102/notes/rank.pdf . Supports sign-test inversion and discrete binomial coverage of order-statistic intervals. Source limitation: its statement that continuity alone ensures a unique median is too strong; the explicit median definition and proof above avoid that assumption. No experimental result is inferred from the lecture note.
- **STAT-IWASAKI-2005**, Manabu Iwasaki, *Less Conservative Distribution-free Confidence Intervals and Tests for the Median*: https://doi.org/10.5691/jjb.26.65 . Discusses conventional binomial/order-statistic confidence limits and ties; used as original-paper corroboration of the problem context. Its proposed interpolated/mid-P modifications are **not** adopted here. The conservative atom proof above is independently derived.

No scientific artifact was changed by this review. These findings are ready for root and Claude Science to incorporate into the protocol before design acceptance.
