# Offline verification — 2026-09-08

**174 tests passed; E1–E8 passed; Ruff 0.16.6 lint and formatting checks passed. Protocol v0.4 is unchanged and not frozen.** These are engineering results, not evidence of LLM superiority.

The integrated pytest suite completed in 66.34 seconds, with one warning that optional matplotlib support for CMA plots is absent. Numerical ask/tell functionality passed. The exported preflight executes exact archived source and fixture bytes, verifies their hashes afterward, and records durable start/finish events before/after each check. `report.json` matches the source files in this implementation commit. It deliberately leaves all complete execution-readiness gates pending.

The standalone command passed all eight groups: propagator identities; fidelity identities and an independent state-average conversion; synthetic aggregation and component timing; overflow-safe mapping; parser/schema behavior; literal prompt rendering; runner/failure/seed contracts; and locked analysis with synthetic custody. A separate `prompt-stability.json` records identical rendered bytes from two fresh Python processes on the same fabricated history. No actual control candidate was evaluated on the study objective, and no experimental model was called.

The numerical tests include independent SciPy matrix-exponential checks. Runner tests include real installed CMA-ES continuing through 19 generations despite a stop condition on a constant stub; partial and missing usage; schema salvage; reserved-work crash recovery; initialization failures; strict finite-value validation; identity changes; confirmed-invalid duplicates; per-call descendant cancellation; abrupt guard death; and the child-startup registration race. Custody tests use temporary repositories and fabricated labels; they do not create a real study mapping.

Independent reviews found and prompted fixes for CRLF JSON fences, incomplete usage counted as zero, early initialization termination, objective-conversion overflow escaping SVF, fingerprint drift, invalid-evaluation duplicate counting, callback descendants surviving timeout, and abrupt guard/startup races. The final scoped process review independently reran four regressions successfully. The preflight review prompted execution from archived snapshots, interruption cleanup, and durable start/failure records. Integrated formatting after review changed layout only; the full test suite then passed.

## Reproduction and limits

Dependencies are resolved by `uv.lock`: Python 3.11.15, NumPy 2.4.6, SciPy 1.17.1, pycma 4.4.4, pytest 9.1.1, Ruff 0.16.6 and pip-audit 2.10.1. The dependency audit reports no known vulnerabilities among the 36 audited dependencies; this unpublished project itself was skipped by the advisory service. The earlier pytest 8.4.2 finding was corrected. An advisory audit is not a general security guarantee.

This host repeatedly delayed reads/imports from the virtual environment under Documents and intermittently terminated a native Ruff invocation. The final integrated run used a fresh temporary environment outside Documents created from the **same unchanged lockfile**. No dependency or scientific configuration was changed to obtain the passing result. The commands were equivalent to:

```sh
UV_PROJECT_ENVIRONMENT=/tmp/quantum-bridge-preflight-runtime uv sync --frozen
PYTHONPATH=src PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 /tmp/quantum-bridge-preflight-runtime/bin/python -m pytest -q --disable-warnings
/tmp/quantum-bridge-preflight-runtime/bin/ruff check --no-cache src tests analysis
/tmp/quantum-bridge-preflight-runtime/bin/ruff format --check src tests analysis
PYTHONPATH=src /tmp/quantum-bridge-preflight-runtime/bin/python -m qbridge.preflight --output-dir NEW_OUTPUT_DIRECTORY
```

The actual commands also directed bytecode to a temporary cache. Component arithmetic/parser timing was 0.006435667 seconds for 100 repetitions on this host, excluding imports. This is **not** study-objective, optimizer-performance or full-experiment timing. The complete source snapshot and raw per-group logs are retained in the delivered local output directory; this repository includes the machine-readable report, engineering event records, option/timing fixtures, supplemental prompt check, full-suite summary and dependency audit. Log digests in `report.json` identify those retained raw logs.

There is no real provider adapter or whole-study launcher. The outer supervising process must survive for local callback cleanup; callbacks must not detach, and external services may continue billing an accepted request after local cancellation. Unknown billing categories and cross-workflow exposure still require the full readiness process. Actual custody roles/storage, provider metadata/limits, concrete monetary authority and the immutable freeze manifest remain unresolved. No real-world or commercial performance is established.
