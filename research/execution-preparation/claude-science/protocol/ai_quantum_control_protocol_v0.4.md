# AI-Guided vs Conventional Parameter Discovery on a Simulated Single-Qubit Robust-Gate Objective — Protocol Draft v0.4

**Status: NOT FROZEN. NO EXPERIMENT RUN. NO RESULT CLAIMED. NO BLINDING IMPLEMENTED.**
Revision: protocol-v0.4 draft, 2026-09-08. Codex clarification revision of reviewed protocol-v0.3; all earlier artifacts remain unchanged. This revision incorporates independent statistical and operational review; it is not a run-manifest freeze. Supersedes the operative content of v0.1, Round 1, v0.2 and v0.3, all preserved unchanged as historical evidence. Evidence IDs refer to `research_evidence_brief_v2.md` (evidence-brief-v2). Governance terms refer to `protocol_governance_v2.md` (governance-v2).
Authority: Chris delegated expert research and pre-freeze document corrections to Codex and Claude Science (governance-v2 §Authority). This draft exercises that delegation. Protocol freeze and evaluation execution are separate, not-yet-exercised gates (§13).

---

## 0. Claim under test (simulator parameter-discovery hypothesis)

> **H1″.** On the fixed simulated instance, under the declared slot and failure contract, the lower population median of the paired log ratio of floored AI/CMA-ES final process infidelities is at most −log₁₀(2).

Define J_X=max(I_X,10⁻¹²), D=log₁₀(J_AI)−log₁₀(J_CMA), F_D(x)=P(D≤x), and theta=inf{x:F_D(x)≥1/2}. This lower 0.5 quantile is the single primary estimand, including distributions with atoms or multiple medians. H1″ is theta≤−m, m=log₁₀(2). Negative D favors AI. This is a typical paired ratio of **floored** endpoints, not a ratio of marginal medians. Flooring can hide improvements below 10⁻¹²; exclusion of H1″ does not exclude benefits in the unfloored objective there.

What H1″ is **not**: not a claim about physics, hardware, reasoning, retrieval, generality across instances, fewer evaluations to reach any target, fewer hardware shots, or cost. It is a statement about the ordering of two configured procedures' final objective values on one instance at one budget.

---

## 1. Scope (exactly one of each)

| Element | Content | Excluded from this experiment |
|---|---|---|
| Simulated system | One qubit, closed dynamics, rotating frame | Multi-level, dissipation, time-dependent noise |
| Noise model | One joint quasi-static (ε, δ) ensemble on a fixed 25-node grid | Continuum/worst-case robustness, other grids, held-out grids |
| Objective | Mean process (entanglement) infidelity on that grid (§3) | Any second objective, target, or variant |
| AI approach | One stateless LLM batch proposer, one prompt pair, one model (§6) | Blind/ablation arms, tool use, prompt tuning on outcomes |
| Conventional method | CMA-ES, one configuration (§5) | BO, Nelder–Mead, GRAPE, any reference optimizer |
| Baseline | Random search, descriptive only (§5.3) | Any test against random search |
| Budget contract | 200 allotted evaluation slots per arm per block, 10 per batch (§7) | Any other budget |
| Evaluation procedure | Frozen analysis (§9) on two independent 20-block stages, both always completed before unmasking | Pooled confirmatory analysis, sensitivity variants, similarity-to-known-pulse analyses |

Engineering checks before execution use **analytic identities on component functions and synthetic fixtures only** (§11). No development instance exists. Evaluating any candidate on the study objective before freeze is an exposure event and is logged (§13.4).

---

## 2. Simulated system and noise model

Units: ħ = 1; Rabi amplitude scale Ω_max = 1; time in units of 1/Ω_max.

**Hamiltonian (rotating frame):**
H(t; ε, δ) = ½ [ (1+ε) ( uₓ(t) σₓ + u_y(t) σ_y ) + δ σ_z ]

**Controls:** piecewise-constant, **N = 10** segments, total duration **T = 4π**, Δt = T/N = 0.4π. Amplitude constraint per segment: uₓ,ₖ² + u_y,ₖ² ≤ 1 (enforced by the mapping in §4.2).

**Joint noise ensemble (fixed, deterministic):** 25 nodes (εᵢ, δⱼ) with
ε ∈ {−0.10, −0.05, 0, +0.05, +0.10}, δ ∈ {−0.20, −0.10, 0, +0.10, +0.20}, equal weights 1/25.
This is a discrete model of quasi-static amplitude and detuning error. Its mean is a property of these 25 nodes; it is neither a continuum expectation nor a worst-case bound (PHY-ZHANG-2025, PHY-KOSUT-2022).

**Propagation:** for segment k and node (ε, δ), write a = ((1+ε)uₓ,ₖ, (1+ε)u_y,ₖ, δ) so that H = ½ a·σ, and
U_k = exp(−i Δt a·σ / 2) = cos(|a|Δt/2)·𝟙 − i sin(|a|Δt/2)·(a/|a|)·σ,
with U_k = 𝟙 when |a| = 0 (implementation must use a division-safe form; verified by analytic identity in §11). Total propagator U(θ; ε, δ) = U_N ⋯ U_1.
Work per valid evaluation: 25 nodes × 10 segments = **250** segment propagations plus 25 trace evaluations.

Numerical character: closed-form propagation within the piecewise-constant model; floating-point rounding and the physical-model idealization remain (PHY-KOSUT-2022). **No numerical resolution bound is asserted.** The 10⁻¹² floor used in §9 is an analysis design choice, not a measured error bound.

---

## 3. Objective (minimize)

Target: X gate, U_target = σₓ.

Per-node process (entanglement) fidelity for a unitary error: F_e(θ; ε, δ) = | Tr( U_target† U(θ; ε, δ) ) / 2 |².
**Objective:**
I(θ) = 1 − (1/25) Σ_{(ε,δ)} F_e(θ; ε, δ),  I ∈ [0, 1], to be **minimized**.

Name: **mean process (entanglement) infidelity on the fixed 25-node joint ensemble**. By PHY-NIELSEN-2002, the Haar-average gate fidelity of a qubit unitary error is F_avg = (2F_e + 1)/3, so the corresponding mean average-gate infidelity is 2I/3; this is an algebraic conversion reported for interpretation only and is not the estimand. F_e is invariant to a global phase of U.

I is deterministic given θ (no stochastic noise in the objective). All stochasticity resides in the procedures that choose θ.

---

## 4. Common action and observation contract (identical for every method)

### 4.1 Coordinate ordering
θ ∈ ℝ²⁰, segment-major interleaved: θ[2k] = uₓ,ₖ, θ[2k+1] = u_y,ₖ for k = 0, …, 9 (segment 0 is applied first in time).

### 4.2 Admissible raw action domain and mapping
- **Raw domain (all methods):** any vector r of exactly 20 IEEE-754 double-precision numbers, each finite. Vectors with fewer/more entries or any non-finite entry are **invalid** (§7.4). There is no box constraint on raw actions for any method.
- **Mapping M (all methods):** for each pair (x,y), let a=max(abs(x),abs(y)). If a=0 return (0,0). If a>1, set (v,w)=(x/a,y/a), h=sqrt(v²+w²), and return (v/h,w/h). If 0<a≤1, compute h=hypot(x,y); return (x/h,y/h) when h>1, otherwise (x,y). No potentially overflowing full-magnitude norm is formed in the a>1 branch. θ=M(r). Declare the absolute dimensionless tolerance τ_map = 16×2^-52 = 3.552713678800501e-15, a numerical acceptance policy, not an empirical precision claim. Compute each mapped-pair norm with float64 hypot. A mapped component must be finite and its computed norm must be ≤1+τ_map; otherwise set SVF and treat the slot as simulator-invalid. Accept a within-tolerance overshoot unchanged and log it; do not silently apply a different map. E4 uses the same norm threshold and checks idempotence by max-coordinate absolute difference ≤τ_map. Thus the implemented disk constraint permits only this declared floating-point tolerance.
- **What is evaluated:** I(θ) with θ = M(r). Both r and θ are logged for every objective call.

### 4.3 Common observation representation
- Every method receives the exact objective value I(θ) for every point it caused to be evaluated.
- Numbers exposed to the LLM (θ coordinates and I) are the **shortest round-trip decimal representation** of the double (Python `repr(float)`); no rounding. This removes the rounding asymmetry noted in Round 2 review at the cost of prompt length (bounded in §7.6).
- The history table shown to the LLM contains **mapped θ** (the evaluated point), not the raw proposal; the LLM is told this.
- CMA-ES observes only the objective values for its own raw samples (§5.2); the mapping is part of the objective from its perspective. This is a method property, not an information-equality claim.

### 4.4 Initialization (shared per block)
Block s defines an initial batch of 10 vectors drawn from stream `init(s)` (§8.2): for each segment, angle φ ~ U[0, 2π), radius ρ = √u with u ~ U[0, 1), giving (ρ cos φ, ρ sin φ). These lie inside the unit disk, so r = M(r). All three arms in block s start from **the same 10 parameter vectors**, evaluated separately in each arm and charged to its own first 10 slots. No objective-value caching is used across arms. How each method uses them is a method choice (§5.2, §6.4); **no claim of equal prior information is made.**

### 4.5 Ordering and tie policy
- History ordering for the LLM: ascending by I, ties broken by ascending evaluation index. Stable.
- Best-so-far / endpoint: the minimum I among valid evaluations; on exact ties the earliest evaluation index is the incumbent (affects only logging, not the endpoint value).

### 4.6 No hidden cross-run state
Each LLM logical call is a single-turn request carrying the full context (§6.3); no conversation identifiers, server-side memory, or cross-block artefacts are reused. CMA-ES state is per block. Random-search state is per block. Any provider-side request caching is a transport optimization that must not alter inputs or outputs; if the provider reports cache usage it is logged.

---

## 5. Conventional method and baseline

### 5.1 CMA-ES configuration (one, fixed)
Implementation: `pycma` (`cma.CMAEvolutionStrategy`) at a **pinned release to be recorded at freeze** (§13.2). Settings declared now:
- `x0` = the best (lowest I) vector of the shared initial batch, raw coordinates (equal to mapped here). Method choice; disclosed.
- `sigma0` = **0.5** (declared design value in raw coordinate units).
- `popsize` = **10** — **non-default**, chosen to match the batch size K = 10 of the budget contract. The pycma default for d = 20 is 4 + ⌊3 ln 20⌋ = 12. This is labelled a batch-matching choice, not a tuned or recommended setting.
- No restarts. No bound handling (the mapping in §4.2 handles feasibility). Fixed `seed` from stream `cma(s)` (§8.2).
- **Termination criteria are not used for control flow:** ask/tell continues until 19 generations are complete regardless of `es.stop()`; the stop-condition dictionary is logged each generation. Whether the pinned release permits ask/tell after a stop condition is an implementation-readiness item (§12).
- All remaining option values are those of the pinned release and are dumped verbatim (`es.opts`) into the freeze manifest. None are asserted here.

**Not claimed:** that this is the strongest conventional comparator at this budget, or that it reaches any optimum (OPT-CMA-TUTORIAL is method documentation only). Conclusions are specific to this configuration.

### 5.2 CMA-ES loop and data flow
Generation g = 1 … 19: `X = es.ask()` (10 raw vectors r ∈ ℝ²⁰) → evaluate I(M(r)) for each → `es.tell(X, values)` with the **raw** vectors and the objective values of their mapped images. Raw, mapped, and I are logged for each. After each complete valid generation, the raw proposals, values and stop-condition dictionary are appended to protected logs; interrupted optimizer state is never replayed (§7.5). Before objective work, validate that ask returned exactly 10 valid raw vectors; otherwise terminate this arm and forfeit its untouched slots. If any objective invocation is simulator-invalid, retain earlier completed valid evaluations, consume the invalid/uncertain slot, set SVF, terminate the arm and forfeit untouched slots. Never invent a penalty value or call tell with an incomplete generation. Initialization in every arm follows the same simulator-validity rule; if it ends without a valid incumbent, stop that arm, preserve the undefined endpoint and set SVF.

### 5.3 Random search (descriptive baseline)
Slots 1–10: the shared initial batch. Slots 11–200: 190 further draws from the same per-segment disk distribution using stream `rs(s)`. No test is performed against random search; its endpoints are reported descriptively and enter the all-pairs nuisance summaries of §10 only as a blinding requirement.

---

## 6. AI approach: stateless physics-informed LLM batch proposer

### 6.1 Model and decoding
- Exactly one model. Its identifier is **recorded from API response metadata at freeze and at every call**; no identifier is asserted in this document.
- Decoding parameters: before freeze select one supported explicit configuration and record the exact request parameters, provider/API version and model fingerprint. A documented fixed default may be used only when its versioned semantics are recorded. If effective decoding settings or stable model identity cannot be established, G-MODEL remains open; no confirmatory run is licensed by substituting an unknown value. No numeric provider default is invented here.
- `max_tokens` (output): declared design value **8192** (a cap, not a guarantee that every permissible output fits; tokenizer/provider-limit compatibility is checked with synthetic boundary fixtures at readiness).
- No tools, no system-side code execution, no multi-turn memory, no retrieval augmentation.

### 6.2 Prompt artefacts
Two frozen text files, `prompts/system_v0.3.txt` and `prompts/user_template_v0.3.txt`, whose SHA-256 enter the manifest and every log row. Normative text follows; the frozen files must be byte-identical to §6.5–§6.6 (modulo the placeholder substitutions defined there). **No performance-driven prompt tuning occurs in this experiment.** The prompt is checked only for format compliance using synthetic fixtures (§11).

### 6.3 Call structure
For each batch b = 1 … 19 of block s, one **logical call** is issued consisting of the system prompt and the user message rendered from the template with: the instance description, the full valid-evaluation history so far (mapped θ, I; §4.3, §4.5), the remaining-after-batch count (200 − 10(b+1)), as defined in §6.6, and the required output format. A logical call may consume up to 3 transport attempts (§7.3). At most one **correction call** per batch may follow (§7.4).

### 6.4 Use of initial information
The LLM history includes all 10 shared initial points. This is a method choice (§4.4).

### 6.5 System prompt (complete normative text)
```
You are a proposal generator inside a fixed-budget black-box optimization study.
You will be given: (1) a precise description of a deterministic objective function
defined on 20 real parameters; (2) a table of every parameter vector evaluated so far
together with its objective value; (3) the number of evaluation slots remaining.

Your task is to propose exactly 10 new parameter vectors that you expect to have
LOWER objective values than those already observed. Lower is better. The objective
is to be minimized.

Output rules:
- Respond with a single JSON object and nothing else: no prose, no explanation,
  no markdown other than an optional single ```json code fence around the object.
- The object has exactly one key, "proposals", whose value is a JSON array of
  exactly 10 arrays, each containing exactly 20 JSON numbers.
- Every entry must be a JSON number that converts to a finite IEEE-754 float64.
  No NaN, Infinity, booleans, strings or nulls are allowed. There is no extra
  magnitude bound beyond finite float64, identical to every method's raw domain.
- Do not repeat a vector that already appears in the table; repeated vectors waste
  evaluation slots.
Any vector that violates these rules is discarded and its evaluation slot is lost.
```

### 6.6 User message template (complete normative text; `{…}` are substituted fields)
```
OBJECTIVE DESCRIPTION
A single qubit evolves under the rotating-frame Hamiltonian
  H(t) = 0.5 * [ (1+eps) * ( ux(t)*sigma_x + uy(t)*sigma_y ) + delta * sigma_z ]
with units hbar = 1 and Rabi scale Omega_max = 1. The controls ux(t), uy(t) are
piecewise constant over N = 10 equal segments of duration dt = 0.4*pi (total T = 4*pi).
The 20 parameters are ordered segment-major: p[2k] = ux of segment k, p[2k+1] = uy of
segment k, for k = 0..9; segment 0 acts first.

Feasibility mapping applied before evaluation: for each segment, if
sqrt(ux^2 + uy^2) > 1 the pair (ux, uy) is rescaled to unit length; otherwise it is
unchanged. The table below lists the MAPPED vectors that were actually evaluated.

Error ensemble: 25 equally weighted nodes (eps, delta) with
  eps   in {-0.10, -0.05, 0.00, 0.05, 0.10}   (relative amplitude error)
  delta in {-0.20, -0.10, 0.00, 0.10, 0.20}   (detuning, units of Omega_max).
For each node, the total propagator U is the ordered product of the 10 segment
propagators exp(-i * H_k * dt). Target gate: sigma_x (an X gate).

Objective to MINIMIZE:
  I(p) = 1 - (1/25) * sum over nodes of | Tr( sigma_x^dagger * U ) / 2 |^2
This is the mean process infidelity over the 25 nodes. It lies in [0, 1]. A value of
0 would mean a perfect X gate at every node. The objective is deterministic.

HISTORY (all valid evaluations so far, sorted by objective ascending;
         columns: index, I, then p[0] ... p[19]; numbers are exact)
{history_table}

Best objective so far: {best_I} at index {best_index}.
Evaluation slots remaining after this batch is evaluated: {remaining_after}.
Number of vectors requested now: 10.

Respond with the JSON object described in your instructions.
```
`{history_table}`: one line per valid evaluation, fields separated by single spaces, numbers as shortest round-trip decimals. `{best_I}`, `{best_index}`: from §4.5. `{remaining_after}` = 200 − 10(b+1) for batch b (so 180 for b = 1, …, 0 for b = 19).

### 6.7 Strict output schema (JSON Schema draft 2020-12)
```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "type": "object",
  "properties": {
    "proposals": {
      "type": "array", "minItems": 10, "maxItems": 10,
      "items": { "type": "array", "minItems": 20, "maxItems": 20,
                 "items": { "type": "number" } }
    }
  },
  "required": ["proposals"],
  "additionalProperties": false
}
```
**Parsing rule (declared, non-selective):** strip surrounding whitespace and at most one surrounding code fence whose opening line is exactly ```json and closing line is exactly ```. A bare fence or any other fence tag is `invalid_json`. Reject nonstandard JSON constants, duplicate object keys at any object depth, and trailing content. Use a duplicate-detecting parser hook or equivalent parser that rejects duplicate keys before object construction or slot salvage; last-key-wins parsing is noncompliant. The response-level envelope must have exactly the key `proposals`, with exactly 10 elements. Extra keys or a wrong element count make the entire response invalid and trigger the zero-valid correction path. With a valid envelope, proposal j owns slot j: it is valid only if it is an array of exactly 20 JSON numbers, excluding booleans, strings and nulls, that all convert to finite float64. An invalid proposal forfeits its own slot; never pack later proposals into it or accept surplus candidates. Log the full schema verdict and per-slot validity separately. If zero proposals are valid, the sole correction response replaces the first response for those same 10 allotted slots; no slot is counted twice. If one or more are valid, evaluate them once and forfeit the others, with no correction. This is explicit per-slot salvage after envelope validation, not a claim that a partially accepted response passed the full schema. Correction reason is the first applicable fixed code: `invalid_json`, `invalid_envelope`, `no_valid_vectors`; no response content or evaluator feedback is appended as a reason.

---

## 7. Budget, resource, and failure contract

### 7.1 Vocabulary
- **Allotted slot:** one of the 200 evaluation opportunities per block per arm (batch 0 = 10 shared initial; batches 1–19 = 10 each).
- **Objective call:** an actual invocation of I(M(r)) on a valid raw vector. Includes calls that end in simulator failure.
- **Valid evaluation:** an objective call returning a finite I ∈ [0, 1].
- **Unresolved reservation:** a durably reserved objective slot with no durable completion record. It is consumed, never replayed, and sets SVF; whether the objective actually began is unknown. Report confirmed objective invocations and unresolved reservations separately, with the latter defining uncertainty in the actual-call total.
- **Forfeit:** an allotted slot for which no objective call was made (invalid vector, failed logical call, algorithm exception, or forfeited remainder). Forfeits are counted per block and reported.
- **Logical call:** one LLM request-response for a batch proposal or for the single permitted correction.
- **Transport attempt:** one HTTP request made in service of a logical call.
Equal allotted slots across arms do **not** imply equal objective calls or equal valid evaluations; all quantities, including unresolved reservations and unknown usage, are reported per block and arm.

### 7.2 Per-block caps (LLM arm)
- Logical calls ≤ 2 per batch (1 proposal + ≤ 1 correction) → **≤ 38 per block**.
- Transport attempts ≤ 3 per logical call → **≤ 114 per block**.
- Per-attempt timeout: declared design value **300 s** (verified at readiness).
- Backoff between attempts of the same logical call: 5 s, then 20 s (fixed).
- Output tokens ≤ 8192 per attempt (§6.1). Input length is bounded by construction (≤200 mapped-history rows plus fixed template and bounded correction reason). Freeze a verified tokenizer-derived input-token ceiling L_in and a total-token ceiling 114×(L_in+8192), with context/reserved-reasoning-token requirements included. A request exceeding its ceiling is not sent and follows the failed-call forfeit path. Record provider-reported token categories separately; unavailable billing quantities remain unknown. G-MODEL blocks freeze until these ceilings are concrete.
- HTTP timeout/backoff allowance alone is at most 114×300 + 38×25 = 35,150 s; it is not a bound on total runtime. Enforce an independent monotonic **36,000 s (10 h) deadline per arm per block**, including initialization, local computation, waits and calls. At expiry stop new work, cancel in-flight work, keep completed valid evaluations, and forfeit remaining slots without replacement. A timed-out objective invocation is simulator-invalid/SVF because a valid result was not obtained. Apply the same deadline to CMA-ES and random search. Record actual elapsed time and scheduling/cleanup overruns. Process execution must support enforceable timeouts before readiness can close.

### 7.3 Ordering of transport retry and malformed-output correction
For each batch: **logical call 1** → up to 3 transport attempts (retry the identical request only on connection failure, timeout, HTTP 429 or HTTP 5xx; only HTTP 2xx is a received model response for parsing. Other HTTP errors terminate the logical call immediately and forfeit the batch without correction. Every dispatched request consumes an attempt, regardless of whether it was billed or returned text). If no response is received after 3 attempts → all 10 slots of the batch **forfeited**; **no correction call**; proceed to the next batch (statelessness makes this well-defined). If a response is received → apply §6.7. If it yields ≥ 1 valid vector → evaluate them, forfeit the remainder, proceed. If it yields 0 valid vectors → **logical call 2 (correction)**: same system prompt; the user message is the original message with the appended line `PREVIOUS RESPONSE REJECTED: {reason}. Respond again following the output rules exactly.` → up to 3 transport attempts → apply §6.7 → evaluate valid, forfeit the rest. No further calls for that batch.

### 7.4 Failure paths (every path predetermined; none selective)
| Path | Handling | Endpoint effect |
|---|---|---|
| LLM invalid vector(s) | Slot(s) forfeited; counted | Incumbent unchanged for those slots |
| LLM zero-valid response | One correction call (§7.3) | As above if still zero |
| LLM transport exhaustion | Batch forfeited (10 slots) | Incumbent unchanged |
| LLM output truncated at `max_tokens` | Treated as the received response (usually parse failure → correction path) | As above |
| CMA-ES exception, wrong ask count or invalid raw sample | Terminate arm; forfeit untouched slots; retain completed valid evaluations; no incomplete tell or invented penalties (§5.2) | Block **remains in analysis**; SVF/IVF blocks confirmatory interpretation |
| Random-search exception or invalid raw sample | Terminate arm; retain completed valid evaluations and forfeit untouched slots | Block remains in report |
| Simulator exception, non-finite I, finite I outside [0,1], or timed-out objective invocation | Objective call recorded as `simulator_invalid`; slot consumed; **study validity failure (SVF) flag set** (§7.7) | Block remains; neither confirmatory support nor exclusion is permitted |
| Zero valid evaluations for an arm (simulator failure, interruption or deadline before a valid incumbent) | Endpoint undefined; SVF | If AI or CMA lacks an endpoint, primary D is undefined. An RS-only missing endpoint leaves primary D computable descriptively, but SVF still blocks confirmatory conclusions. Report every missing endpoint. |
| Process crash / interruption | Apply the no-replay rule in §7.5; keep completed evaluations and forfeit the active arm's remaining slots | None beyond any forfeits already incurred |
| Human intervention altering any input, state, or log | Recorded as `intervention`; SVF | Neither confirmatory support nor exclusion is permitted |
| Provider model/fingerprint or effective decoding change; evidence of shared state or nonstationarity | Inferential validity failure (IVF), preserve metadata and outcomes (§8.3) | Neither confirmatory support nor exclusion is permitted |

After initialization has yielded a valid incumbent, an isolated simulator-invalid evaluation in the LLM or random-search arm consumes its slot and sets SVF, but the arm continues to later scheduled slots using only completed valid observations. CMA-ES instead terminates as specified in §5.2 because its generation cannot receive a complete tell. Deadline, crash, algorithm exception and zero-valid-initialization rules still terminate the affected arm as specified above.

**No run replacements. No excluded blocks.** Every planned seed block (§8) enters the endpoint analysis with whatever valid evaluations it obtained. A block whose LLM arm forfeits all 190 optimizer slots has endpoint = best of the initial batch; that is the configured method's outcome under the failure contract, not an anomaly to be removed.

### 7.5 No-replay crash rule
Durably reserve the allotted slot or transport-attempt number before starting external work; append the completed response/result afterward. Never reuse a reserved number. If an arm is interrupted or the process crashes, do not resume its optimizer, partially completed batch or API request. Keep its durably completed valid evaluations and forfeit the remaining unreserved slots; retain reserved-but-unresolved attempts as uncertain resource usage. An objective reservation without a durable result is consumed/SVF with execution status unknown; it may represent a crash before invocation or during execution, so it is not counted as a confirmed call. An unresolved API reservation consumes one attempt allowance and is logged as dispatch/execution status unknown, and any missing billing/usage remains explicitly unknown rather than zero. Later arms and blocks may proceed under the frozen schedule after recovery, without rerunning the failed arm. If interruption occurs before any valid initialization value for an arm, its endpoint is undefined and SVF applies. This deliberately simple failure policy trades potential performance for auditable nonselective accounting; it removes checkpoint/serialization-dependent continuation from this experiment.

### 7.6 Costs outside the slot budget (reported, never equalized)
Per arm and block: logical calls, transport attempts, input/output tokens, wall-clock, provider errors, forfeits, duplicates (proposals bitwise-equal to an already-evaluated mapped θ — evaluated anyway, slot consumed, counted). Preparation costs: prompt authoring iterations (format-only, §6.2), engineering-check runtime, developer time (self-reported). **No claim that equal slots means equal compute, time, money, or hardware shots** (BENCH-COCO-2016).

### 7.7 Study validity failure (SVF)
Any SVF or inferential validity failure (IVF) is preserved with full provenance and prohibits **both confirmatory support and confirmatory exclusion** for the study. Computable intervals and nominal categories may still be shown only as descriptive calculations marked invalid for confirmatory interpretation. Missing endpoints are never imputed silently or dropped; report noncomputability explicitly. Neither favorable nor unfavorable results bypass this validity gate.

---

## 8. Blocks, seeds, and independence

### 8.1 Blocks
- **Stage 1:** blocks s = 0 … 19. **Stage 2 (independent replication):** blocks s = 20 … 39. Identical frozen procedure.
- **Both stages are always completed before any unmasking.** Stage 2 is never conditioned on Stage 1's outcome. There is **no pooled confirmatory analysis** (a pooled n = 40 summary may appear as a descriptive figure only, labelled non-confirmatory).
- Within a block, arms are executed in the fixed order RS → CMA-ES → LLM (logging convention; shared initialization induces paired dependence, while optimizer state and outputs are not passed between arms).

### 8.2 Seed convention (fixed pseudorandom streams)
NumPy `SeedSequence(entropy=E, spawn_key=(s,))` with **E = 20260908** (declared constant), spawned into three child sequences in fixed order: child 0 → `init(s)` (initial batch), child 1 → `rs(s)` (random search), child 2 → `cma(s)` (one integer sampled uniformly by this child generator from 1 through 2**31−1 inclusive seeds pycma (zero is excluded); exact generator call and result are logged before evaluation). Generator: `numpy.random.Generator(PCG64(child))`. Protocol policy: no LLM seed parameter is sent. Whether the selected provider supports such a parameter is recorded at G-MODEL, not asserted here. Repeated requests may therefore differ, even with identical content.

### 8.3 Independence and identical-distribution assumptions
- Blocks are treated as **independent and identically distributed** draws of the frozen procedure. Disjoint pseudorandom streams and isolated state provide reproducibility and separation for RS and CMA-ES; treating blocks as iid remains a sampling-model assumption, not a mathematical consequence of a fixed seed list. For the LLM arm it is an **assumption**: the provider is a shared external service; requests from different blocks could be correlated through load, caching, or model updates.
- **Stationarity assumption:** the model behind the recorded identifier is unchanged across all calls of both stages. Mitigation: record the response metadata identifier per call; execute both stages within the shortest feasible window; report any change. A known model, fingerprint or decoding change breaches the frozen stationarity model and sets IVF; any continued computation is descriptive only. Absence of a reported change is not proof that the service is stationary.
- Each block's D is one observation; grid nodes and individual evaluations are not analysis units.

---

## 9. Frozen statistical analysis

### 9.1 Per-block outcome
For block s and arm X ∈ {AI, CMA}, I_X(s) = min I over valid evaluations of that arm in the block (including the initial batch). Define
Y_X(s) = log₁₀ max(I_X(s), 10⁻¹²),  D(s) = Y_AI(s) − Y_CMA(s).
The 10⁻¹² floor exists only to make the log transform total; it is a **design choice** whose relevance is checked by reporting how many endpoints (if any) were floored. Negative D favors the AI arm.

### 9.2 Estimand
The lower population median theta=inf{x:F_D(x)≥1/2} of the floored paired log ratio D under the frozen procedure. Each stage estimates it separately under the common iid/stationarity model. Keep every zero and tie with multiplicity; do not jitter, interpolate interval endpoints or drop observations.

### 9.3 Interval
For n = 20 i.i.d. blocks, the order-statistic interval **[D₍₆₎, D₍₁₅₎]** (6th and 15th smallest of the 20 values) is a distribution-free confidence interval for the population median with coverage at least
1 − 2·Σ_{j=0}^{5} C(20, j) / 2²⁰ = 1 − 2·(21700 / 1048576) = **0.95861…**
(derived here from the binomial identity; the sum Σ_{j≤5} C(20,j) = 1+20+190+1140+4845+15504 = 21700). No symmetry, continuity, or distributional shape is assumed; with ties or exact zeros (plausible if both arms end at the shared initial best) the coverage remains **at least** this value under the standard definition of a population median. Adjacent attainable two-sided levels are 88.5% ([D₍₇₎, D₍₁₄₎]) and 98.8% ([D₍₅₎, D₍₁₆₎]); confidence-level/rank resolution is therefore discrete. Interval width on the log-ratio scale and power depend on the unknown outcome distribution; neither is guaranteed by n=20. No Wilcoxon test, permutation test, or bootstrap is used (DOC-SCIPY-PAIRED explains why Wilcoxon's symmetry condition and tie/zero behavior are not established here).

### 9.4 Margin and decision rule (per stage, mutually exclusive)
Margin **m = log₁₀ 2 ≈ 0.30103** (a factor of 2 in the paired **floored** final infidelity ratio). This is a **transparent research design choice**, not a hardware-economic fact, and it is not converted into evaluations, shots, or cost.
- **Supports meaningful benefit:** D₍₁₅₎ < −m (the whole interval lies below −m).
- **Excludes the prespecified median benefit:** D₍₆₎ > −m (the whole interval lies above −m).
- **Inconclusive:** otherwise.

The interval's position relative to 0 (e.g., wholly below 0 but not below −m) is **reported as a descriptive fact** and carries no decision weight. Sample median (mean of D₍₁₀₎ and D₍₁₁₎) is reported descriptively. None of these outcomes is an equivalence claim or a universal no-benefit claim (STAT-ASA-2016).

### 9.5 Study-level statement
The study statement "supports meaningful benefit in this instance" requires **both** stages to fall in *Supports* **and** no SVF or IVF (§7.7). Replicated exclusion requires both stages to fall in *Excludes* with no SVF/IVF. Endpoint equality with the margin is inconclusive. These are separate per-stage intervals, not a joint 95% confidence region. Every other combination is reported verbatim (e.g., "Stage 1 supports; Stage 2 inconclusive — not replicated at this precision"). Limitations always stated: n = 20 per stage is resource-limited (STAT-LAKENS-2022 — no a-priori power is claimed and none was computed from data); attainable confidence levels are discrete; the LLM independence/stationarity assumptions of §8.3; model drift across time or provider updates makes the configured method non-reproducible in the strict sense — the archived transcripts, not re-execution, are the reproducibility record.

### 9.6 Reported quantities (all, regardless of outcome)
Per stage: all 20 D values; the interval; decision category; sample median; number of floored endpoints; number of exact ties; per-block forfeits, objective calls, valid evaluations, duplicates for each arm; SVF and IVF events; best-so-far curves per arm (descriptive figure; label-revealing, see §10.4). Random-search endpoints alongside (descriptive).

---

## 10. Blinding and analysis lock

### 10.1 Purpose and honest limit
Controller-input content (the physics description) is unrelated to evaluator blinding. Blinding here aims to remove **analyst discretion**, not operator knowledge: whoever runs the LLM arm knows which arm it is, and best-so-far curves may be recognizably different. This protocol does not claim that outcomes are unrecognizable.

### 10.2 Executable procedure (chosen): all-ordered-pairs locked summary, sealed, then custodian selection
1. Before any real data, the analysis script `analysis/locked_analysis.py` is finalized, tested on synthetic fixtures (§11), and its SHA-256 is committed to the manifest.
2. Labels {A, B, C} are assigned to {AI, CMA, RS} by a random permutation drawn from a **sealed permutation seed** held by the custodian role (§10.3). The mapping file is stored **outside the public repository**; only a commitment enters the manifest. The committed private file contains the mapping plus a fresh cryptographically random 256-bit nonce; hash the entire file. Keep the nonce private until unmasking, since hashing one of only six mappings without a nonce would allow enumeration.
3. The masked analysis dataset contains, per (label, block): the endpoint Y, and per (label, block, slot index): cumulative best (for the descriptive figure). It contains **no** arm identifiers, timestamps, token counts, forfeit markers, raw or mapped vectors, or transcripts.
4. The locked script computes the **identical summary** (all 20 D values, order-statistic interval, decision category, descriptive statistics) for **every ordered label pair** (A−B, A−C, B−A, B−C, C−A, C−B), for each stage separately. These six summaries are **nuisance summaries required by the blinding design; they are not additional hypotheses** and none is interpreted except the precommitted pair.
5. The complete output is written, hashed, and the hash committed (**sealed**).
6. The custodian role then selects the precommitted pair (AI-label minus CMA-label) using the mapping and records the unmasking event (who, when, sealed-output hash referenced).
7. Raw logs and transcripts are released after unmasking and a privacy/credential review.

### 10.3 Custody roles — chosen automated sequence, setup remains a readiness gate
Codex and Claude Science share context and **are not independent custodians**. Under Chris's delegation of expert decisions and preference for autonomous work, **option (b) is selected for this first experiment**. It provides analysis locking and auditable sequencing, not independent evaluator blinding. Actual storage/roles/implementation remain G-CUSTODY/G-STORAGE gates. Option (a) is documented as a future pre-exposure amendment option, not a pending routine question for Chris:
- **(a) Human custodian:** Chris holds the sealed permutation seed and mapping, does not participate in analysis, and performs step 6. Separates custody from analysis if roles are actually observed; curve-based leakage remains, so complete blindness is not guaranteed.
- **(b) Locked automated alternative:** the runner draws the permutation from a seed stored in a protected location; an unmasking script refuses to run until the sealed-output hash exists in the committed manifest. **Limitation:** any agent or person with filesystem access can read the mapping at any time; this alternative provides an auditable *sequence* (analysis sealed before mapping consulted), not blindness. If chosen, the report must say so.
For the selected automated sequence, actual roles (operator, analyst, custody process owner) are named in the public register; the mapping and identity-bearing transcripts never enter public Git.

### 10.4 Residual leakage (disclosed)
Operator knowledge; recognizable curve shapes; forfeits inferable from curve plateaus; the precommitted pair is nevertheless selected by the custodian after sealing, so analyst selection is removed. The public report states these limits in the same section as the result.

---

## 11. Engineering checks (pre-execution; analytic identities and synthetic fixtures only)

None of these evaluates any candidate on the study objective. All are logged as engineering-check events with their inputs.
- **E1 Propagator identities:** unitarity ‖U†U − 𝟙‖ small for random finite a; U(a=0) = 𝟙; composition U(a, t₁+t₂) = U(a, t₂)·U(a, t₁); rotation angle check exp(−i π σₓ/2) ∝ σₓ up to phase; division-safe |a| → 0 limit.
- **E2 Fidelity identities:** F_e(U, U) = 1; F_e(U, e^{iφ}U) = 1; F_e(𝟙, σₓ) = 0; F_avg = (2F_e+1)/3 conversion on random unitaries (PHY-NIELSEN-2002).
- **E3 Aggregation/timing fixtures:** validate averaging with stubbed propagator/fidelity values of known arithmetic outcome, without introducing another Hamiltonian/noise-grid objective. Time repetitions of E1 component identities and parser/serialization work; these are component timings, not measured runtime of the study objective or a full optimizer run. Preserve all engineering logs. No alternate target, noise grid or physical development instance is constructed.
- **E4 Mapping:** idempotence and mapped norm satisfy the explicit τ_map tests in §4.2; include near-boundary rounding cases and log within-tolerance overshoots; behavior at large finite magnitudes (e.g., 1e300) without overflow; rejection of non-finite input.
- **E5 Parser/schema:** synthetic responses covering: valid; exactly json-fenced; bare-fenced and other-tag fences (invalid_json); duplicate object keys at every object depth (reject before salvage, including duplicate proposals keys); extra keys; 9/11/30 vectors; wrong length; non-finite literals; truncated JSON; prose-wrapped. Verifies §6.7 rules exactly, including the duplicate-detecting parser hook.
- **E6 Prompt rendering:** template renders from a synthetic history table (fabricated numbers, not objective outputs) to byte-stable text; hash stable across runs.
- **E7 Runner/failures:** use a stub objective and mocked API to inject interruption before and after reservation/completion, partial batches, deadlines, malformed responses and model changes. Verify no replay, no reused slots/attempt numbers, retained incumbents, explicit unknown usage and SVF/IVF propagation. Check seed-stream reproducibility. These are synthetic contract checks, not optimizer outcomes.
- **E8 Locked analysis:** all-pairs computation, order-statistic interval, tie handling, floored values, undefined-D handling, on synthetic D fixtures including ties and zeros.
- **E9 LLM interface:** format-compliance smoke test with a **synthetic** history (fabricated numbers). Its purpose is to confirm transport and parsing, not performance; the number of such calls and their content are logged. This is the only permitted pre-freeze model call and it is an implementation-readiness activity, not authorized by this document.

---

## 12. Execution-readiness gates (facts that require measurement or decision; each blocks freeze while open)

| Gate | Requirement | How satisfied |
|---|---|---|
| G-ENV | Python, numpy, scipy, pycma versions pinned; documentation matched to the pinned versions (the evidence brief notes header mismatches across SciPy documentation snapshots — the installed version is what must be pinned) | `pip freeze` output in manifest |
| G-CMA | pycma option dump at pinned release; confirmation of ask/tell behavior after stop conditions; `seed` handling and no-replay failure accounting (E7) | Recorded engineering-check log |
| G-MODEL | Model identifier from response metadata; supported explicit decoding configuration or versioned documented defaults recorded; stable model identity established; `max_tokens` 8192 accepted; worst-case input (200 history rows, shortest-repr) fits the context limit with margin | Metadata capture + E9 log |
| G-TRANSPORT | Enforced attempt limits, 300 s timeout, backoffs, 36,000 s per-arm deadline, context/input-token ceiling and provider usage accounting validated with mocks and E9 | Engineering and E9 log |
| G-CUSTODY | Selected option (b) implemented; operator, analyst and custody process owner named | Governance record |
| G-LOCK | `locked_analysis.py` finalized and hashed; E8 passed | Manifest entry |
| G-EXPOSURE | Exposure log shows zero evaluations of any optimizer candidate on the study objective before freeze | `EXPOSURE_LOG.jsonl` |
| G-STORAGE | Protected (non-public) location for mapping, raw logs, transcripts identified | Governance record |
| G-RUNTIME | Component timing and enforceable deadlines checked using E1/E3/E7; actual study-objective and full-run runtime remain unmeasured until authorized evaluation | Engineering log |
| G-COST | Concrete input/total token ceilings, provider billing categories, monetary spending ceiling and authorization for both stages recorded; no unknown billing quantity silently treated as zero | Budget and authority record before any paid preflight or evaluation |

---

## 13. Governance, freeze, and provenance

### 13.1 Authority (actual)
Chris delegated expert research, document implementation, and pre-freeze corrections to Codex and Claude Science (governance-v2). This draft was produced under that delegation. **Freeze and execution are distinct gates that have not been exercised**; each requires its own recorded decision referencing the immutable manifest, authored truthfully by whoever actually decides. No human-authored artefact is fabricated or required to be fabricated.

### 13.2 Gate sequence (non-circular)
1. **Design review** (this phase): protocol text reviewed; required corrections closed by independent review, not self-assessment.
2. **Permitted implementation and preflight:** code, prompts, locked analysis, engineering checks E1–E9 under §11 rules. Begins only after an actual permitted-implementation decision citing existing user authority or a new top-level decision as needed; design-review closure alone is not authority invented by this document. A run manifest need not exist before component implementation.
3. **Run-manifest freeze:** all §12 gates satisfied; manifest enumerates paths and SHA-256 for protocol, code, prompts, config, seeds (E and block list), analysis script, environment manifest, model identifier and decoding metadata, mapping-file hash, failure/resource rules; Git commit recorded. Any unresolved value blocks freeze.
4. **Evaluation:** both stages, append-only logs, no interventions; then sealing, custodian selection, unmasking, report.

### 13.3 Amendments
`AMENDMENTS.md`, append-only: date, author/agent, old→new revision, reason, `pre-exposure`/`post-exposure`. Redesign after exposure requires a new evaluation instance with fresh blocks; prior attempts are never erased.

### 13.4 Outcome-exposure record
`EXPOSURE_LOG.jsonl` records every call of the study objective on any vector before freeze (expected: none), every engineering-check event, every pre-freeze model call (E9), and every access to unmasked data after evaluation.

### 13.5 Classification
Eligible for confirmatory interpretation only when no SVF/IVF applies: the Stage 1 and Stage 2 primary decisions (§9.4) for the precommitted pair. Everything else — descriptive statistics, curves, random-search results, nuisance pair summaries, cost tables — is descriptive/exploratory and labelled so.

### 13.6 Public-repository hygiene
No credentials, mapping, sealed seed, raw identity-bearing transcripts, or private filesystem paths. Transcripts published only after unmasking and review.

---

## 14. Explanations

### 14.1 Technical
A paired, budget-matched comparison of two batch black-box optimizers on one deterministic 20-dimensional objective (mean process infidelity over a fixed 25-node quasi-static error ensemble for an X gate, piecewise-constant controls, per-segment disk feasibility). The AI arm is a stateless LLM mapping the full evaluation history to the next 10 raw proposals; CMA-ES is a rank-based Gaussian search with population 10. Each block yields one paired log₁₀ difference of floored endpoints; twenty independent blocks give a distribution-free order-statistic confidence interval for the population median at ≥ 95.86% coverage, decided against a declared factor-of-2 margin in three exhaustive categories; an independent second stage of twenty blocks is always run and analyzed separately. Landscape topology of this constrained ensemble objective is unknown (PHY-RIVIELLO-2015 shows constraints can obstruct optimization; no trap-free result has been shown to apply to it, and none is claimed either way), so no certified reference optimum is available and all statements are relative to the configured comparator.

### 14.2 Educated-layperson
Two automatic "guessers" each get 200 tries to find settings that flip a simulated qubit reliably even when the simulated hardware is slightly off. One is a standard, widely used optimization algorithm; the other is a language model given the physics and shown every earlier try. A third "guesser" picks at random as a reference. We run this contest 20 times with different starting points, then another independent 20 times, score everything with a rule fixed in advance and applied by a locked program that doesn't know which guesser is which, and only say the language model "clearly did better" if both rounds support the declared factor-of-two benefit in the typical paired ratio after applying the fixed numerical floor. Benefits below that floor may be hidden; the claim applies to this floored measure. Anything short of that is reported exactly as it came out.

### 14.3 Speculative-commercial boundary
No commercial inference follows from any outcome of this experiment. A "supports" result would say only that one configured LLM proposer beat one CMA-ES configuration on one simulated objective at one budget by a declared margin; it would not show fewer evaluations to reach any target, fewer hardware shots, lower cost, or transfer to real devices, whose noise is time-dependent, stochastic, and includes leakage. An exclusion result would rule against the specified floored median-benefit threshold under the declared assumptions; an inconclusive result would leave that question unresolved. They are reported distinctly. Any commercial framing requires separate experiments designed for that purpose.

### 14.4 Strongest alternative explanations
*For a positive result:* the proposer emits pulse structures it has seen in training data (admissible under H1″; not distinguished); the comparator configuration (popsize 10, σ₀ 0.5, no restarts) is weaker than other conventional settings; the budget regime favors history-conditioned proposals over covariance adaptation; the LLM uses all 10 initial points while CMA-ES uses one (a method property, disclosed); interaction between disk projection and CMA-ES step-size adaptation; chance in one stage (mitigated by mandatory Stage 2).
*For a null or inconclusive result:* the prompt format, not the approach, limits the proposer; attention degradation over long exact-decimal histories; forfeits under the failure contract dominate the endpoint; the instance is easy enough that both arms saturate; resource-limited n = 20 may yield a wide interval, so moderate benefits can remain inconclusive.

---

## 15. Evidence and citation policy for this draft
Only evidence-brief-v2 IDs are relied on for protocol decisions. Round 1 cited several landscape papers with abstract-level quotations; the persisted retrieval record for those searches contains titles and URLs only, so the quoted text cannot be re-verified from the record. Those references are therefore **not relied on** here and appear only in `round2_disposition.md` as proposed additions to the evidence registry pending independent full-text verification. The statement that trap-free results have not been shown to apply to this constrained ensemble instance is a statement of non-establishment, not a claim that their assumptions fail.

## 16. Round 3 clarification disposition

N1–N7 from the preserved Round 3 disposition are resolved in this revision: explicit LLM/RS continuation after isolated simulator-invalid evaluation; selected automated custody gate; fixed τ_map and acceptance behavior; bare-fence rejection fixture; IVF reporting; retained-block validity wording; and duplicate-key parser/fixture requirements. These clarify the existing design; none is claimed as an implemented or passed engineering check. Statistical estimand, interval, margin, budgets, instance, methods and no-freeze status are unchanged.
