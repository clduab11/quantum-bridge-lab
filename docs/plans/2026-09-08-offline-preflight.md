# Offline preflight implementation plan

**Goal:** Implement and verify protocol v0.4 engineering components without evaluating any candidate on the study objective or calling an experimental model.

**Architecture:** Small Python modules with explicit interfaces, a durable event journal, deterministic synthetic checks and a readiness report. Numerical components, locked analysis and harness work are isolated in separate Git worktrees and reviewed before integration.

**Tech stack:** Python 3.11, NumPy, SciPy, pycma; uv.lock records actual dependency versions; pytest and Ruff verify code.

**Spec:** `specification/ai_quantum_control_protocol_v0.4.md`, SHA-256 0df9242fd2d0ad5d30b75ea91f498842ac68fe0df9616afd4c9c04518233eda5.

## Authority and limits

Chris's request on 2026-09-08: “Continue the work of the repo and give me a status update as to where we stand overall (aka, is this worth pursuing?)” is the actual permitted-implementation decision for offline code and analytic/synthetic preflight, interpreted together with prior expert delegation. Codex records this interpretation honestly; it is not a fabricated user signature. Paid model preflight, monetary ceilings, frozen study execution and scientific results are not implied by this offline phase. No study objective will be called by this preflight command or test suite.

Preserve historical protocol artifacts. Any newly exposed defect is recorded prospectively. Use the fixed 20-dimensional, B=200/K=10 contract; no additional physical objective/grid/target is created for optimization. All executed values are analytic component inputs or synthetic records.

## Task 1: numerical components (independent worktree)

Files: `src/qbridge/physics.py`, `tests/test_physics.py`.
Interfaces: `map_action(raw) -> numpy.ndarray` (20-vector); `segment_unitary(a, dt) -> complex ndarray(2,2)` for H=a·σ/2; `process_fidelity(target, actual) -> float`; `mean_infidelity(fidelities) -> float` for synthetic averaging fixtures. No function evaluating the full 25-node study objective in this phase.

- [x] Write analytic tests first: zero generator identity; x π rotation; composition; global-phase invariance; identity-vs-X orthogonality; stub averaging 0.25/0.75 → 0.5; mapping near disk boundary, zero, subnormal and maximal float64; idempotence within declared tolerance; wrong dimension/nonfinite/bool rejection.
- [x] Observe failures for missing implementation, implement division-safe propagation and overflow-safe mapping, and rerun tests. Cross-check components against SciPy expm on fixed analytic vectors, never an optimizer/candidate ensemble.
- [x] Self-review and commit; root checks spec and tests before cherry-pick.

## Task 2: locked inference and custody (independent worktree)

Files: `src/qbridge/analysis.py`, `src/qbridge/custody.py`, `analysis/locked_analysis.py`, `tests/test_analysis.py`, `tests/test_custody.py`.
Interfaces: `summarize_stage(differences, *, invalid=False) -> dict`; `analyze_masked(rows, *, svf=False, ivf=False) -> dict` where each row is exactly `{label: A|B|C, block: 0..39, y: float|None}`; functions for private mapping commitment, canonical output sealing and verified pair selection. Y is already log10 floored endpoint; no model identity in masked rows.

- [x] Write tests first for exact D[5]/D[14], literal factor-two boundary, ties, missing records, missing endpoints, duplicate/extra records, two stages and invalid flags. Positive/negative fixtures must agree with hand-computed decision categories; invalidity disables both support and exclusion.
- [x] Implement all six ordered pairs per stage, strict data validation, null-safe descriptive results and no pooling. Synthetic missing RS endpoint must not erase the AI/CMA comparison but still prohibit study confirmation.
- [x] Test nonce-protected commitment and seal verification before selection, wrong hash and missing output rejection, identity field rejection, protected private permissions. Use synthetic custody files only; do not establish a real study mapping.
- [x] Self-review and commit; root checks spec and tests before cherry-pick.

## Task 3: proposer contract and preflight harness (integration worktree)

Files: `src/qbridge/proposals.py`, `src/qbridge/journal.py`, `src/qbridge/runner.py`, `src/qbridge/preflight.py`, `prompts/system_v0.3.txt`, `prompts/user_template_v0.3.txt`, corresponding tests and readiness artifacts.
Interfaces: `parse_response(text) -> ParseResult` with length-10 tuple of valid vectors or None, fixed correction reason and full-schema verdict; `render_user(history,batch) -> str` with rows `{index,theta,value}`; durable append-only journal; finite slot allocation and retry state machine with injected synthetic objective and mock transport only.

- [x] Write parser tests first: exact envelope, per-index salvage, duplicate keys rejected at all depths, json fence accepted, bare/other fences rejected, finite conversion, no packing, no surplus, bounded reason codes.
- [x] Extract literal normative prompts; render exact decimals, stable objective/index ordering and remaining-after count. Test with fabricated rows only.
- [x] Write durable-reservation tests before implementation. Slots/attempts never replay after an interrupted reservation; confirmed/unknown usage remains distinct. Protect log permissions and fail on corrupted records.
- [x] Test 3 transport attempts with fixed backoffs, HTTP rules, single zero-valid correction, timeout/deadline forfeits, partial batch salvage, SVF/IVF propagation, incumbent retention, CMA full-generation-only tell and stop-condition continuation using stub objectives.
- [x] Add offline preflight command: run analytic/synthetic checks, capture dependency/options/source hashes and component timing; append exposure/check records. There is no provider API implementation or study-run command yet.
- [x] Run dependency audit, full tests and lint; review integrated diff independently. Close only actually demonstrated readiness requirements, preserve missing real-provider/cost/freeze items.

## Task 4: decision and synchronized status

- [x] Reconcile a bounded primary-source novelty/value review with Claude Science in a fresh project conversation after Context7/Exa preflight. Ask for the strongest case against proceeding, without extending study scope.
- [x] Write a candid status with research value, no empirical advantage claim, product boundary, sunk-cost-independent continuation criteria, measured engineering progress and remaining gates.
- [ ] Push a reviewable implementation branch and update Linear ADV-36/current project status. Verify external readbacks; keep originals unchanged.
