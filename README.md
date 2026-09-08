# quantum-bridge-lab

Research preparation for a small, falsifiable comparison of an AI proposer, one conventional optimizer and random search on a simulated qubit-control problem.

**Status: protocol v0.4 reviewed; offline components implemented; full execution readiness pending. Not frozen. No experimental result.**

- [Reviewed protocol v0.4](specification/ai_quantum_control_protocol_v0.4.md): complete design, failure contract, inference and readiness requirements.
- [Evidence and adversarial review](specification/PREIMPLEMENTATION_REVIEW.md): source IDs, supported claims, limitations and required corrections.
- [Protocol and provenance register](specification/PROTOCOL_REGISTER.md): originals, authority and phase gates as of the completed design review; current implementation status is recorded below.
- [Original Claude Science design v0.1](sources/original/ai_quantum_control_minimal_experiment_v0.1.md): unchanged historical source containing issues identified in the review.
- [Linear project](https://linear.app/cld-maindev/project/quantum-bridge-lab-cc3b6e3fff04) and [correction work ADV-35](https://linear.app/cld-maindev/issue/ADV-35/reconcile-evidence-and-close-r1-r10-before-protocol-freeze).

The first experiment is restricted to one system, joint noise model, objective and fixed budget contract. Independent seed replication uses the same procedure. Findings will be specific to the recorded simulation, configurations and budget; performance alone will not identify a reasoning mechanism or establish hardware or commercial benefits.

[Historical design-review synchronization record](research/SYNCHRONIZATION_RECEIPT.md).

## Is this worth pursuing?

[Current pursuit decision](research/PURSUIT_DECISION.md): finish the bounded offline engineering milestone; decide separately whether a fully costed two-stage experiment earns further investment. The software and learning have value. An LLM performance advantage, publication novelty and commercial value remain unproven. The decision includes Claude Science's adversarial review, retained disagreements, and prospective actions for every outcome category.

## Offline engineering checks

Use Python 3.11 and the checked-in `uv.lock`:

```sh
uv sync --frozen
PYTHONPATH=src PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 uv run --frozen pytest -q
uv run --frozen ruff check src tests analysis
PYTHONPATH=src uv run --frozen python -m qbridge.preflight --output-dir preflight-output
```

The last command requires a new directory and preserves exact source/fixture bytes, test logs, component timings, package versions, effective CMA options and a durable engineering exposure log. It executes the archived source snapshot. It runs analytic identities and synthetic contracts, including constant-stub optimizer characterization; it evaluates no control candidate on the study objective and calls no experimental model. It requires this source checkout and the development dependencies. The command provides no network sandbox; the inspected tests use fabricated inputs and injected mock transports.

[Recorded verification](research/preflight/VERIFICATION.md): 174 integrated tests and all eight offline check groups passed. Runtime limitations and the distinction from full study readiness are documented alongside the evidence.

The Python modules cover numerical components, strict JSON proposals and literal prompts, deterministic seeds, durable reservations and failure accounting, killable POSIX execution, locked all-pairs inference and temporary custody fixtures. The process executor requires a single-threaded POSIX caller; callbacks must not detach into new sessions. `InlineExecutor` is solely for synthetic clocks and does not enforce hard cancellation.

There is no provider adapter or full-study command. [Implementation readiness](research/IMPLEMENTATION_READINESS.md) records what remains before the model/cost decisions, complete manifest and protocol freeze. Study logs and mappings belong in protected private storage, never in public preflight artifacts.
