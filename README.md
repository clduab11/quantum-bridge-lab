# quantum-bridge-lab

**Can a language model suggest better settings for a simulated quantum system when every method gets the same trial budget?**

This repository contains the research plan, Python software and review history for answering that question. It is a small, deliberately limited experiment: one simulated qubit, one language model, one conventional optimizer and a random-search reference.

**Current status:** the first offline engineering milestone is complete: 174 tests and eight check groups passed. The experiment itself has **not run**. The final execution plan is not frozen, and no AI performance advantage has been demonstrated.

## The idea in everyday terms

Imagine tuning a radio with several connected knobs. Each set of settings gets a score, and you can use earlier scores to choose the next settings. Here, the “knobs” describe a sequence of control pulses for a simulated qubit—the basic unit of a quantum computer. The score measures how closely those pulses perform a desired operation across a fixed set of calibration errors.

The language model receives the previous settings and scores, then proposes ten new settings at a time. A conventional optimizer called CMA-ES and random search work under the same trial budget. Each method gets 200 evaluation slots per run. The plan includes two sets of 20 paired runs, both completed before the final comparison is revealed.

The test asks whether the language model delivers a prespecified improvement in the final error. Equal trial budgets do not mean equal time or cost: model calls, retries, failures and other resources must also be counted.

## Why this matters

AI is often proposed as a scientific assistant. A useful next step is to test a precise claim against an established method, with the rules written down before results are available.

This project makes that comparison inspectable. The code preserves failed attempts, enforces budgets and fixes the analysis in advance. A negative or inconclusive answer is useful too: an honest record of what the test could resolve helps guide further investment.

Our present judgment is that a bounded research effort is worth pursuing. Funding the actual model experiment is a separate decision, based on its full cost and the value of the answer. This simulation alone cannot establish savings on quantum hardware, a commercial product, or an explanation of how a model reasons. Related research already exists; we make no blanket novelty claim. See the [pursuit decision and retained reviewer disagreements](research/PURSUIT_DECISION.md).

## What is here

| Part | What it provides |
| --- | --- |
| [Research protocol](specification/ai_quantum_control_protocol_v0.4.md) | The question, fixed comparison, failure rules and analysis requirements |
| [Python components](src/qbridge/) | Numerical building blocks, proposal parsing, trial accounting and locked analysis |
| [Tests](tests/) and [verification evidence](research/preflight/VERIFICATION.md) | Analytic and fabricated-data checks, with their scope and limitations |
| [Research and reviews](research/) | Evidence, decisions, remaining work and synchronization records |
| [Original sources](sources/original/) | Earlier designs and Claude Science reviews, preserved unchanged |

Codex and Claude Science develop and challenge the work under Chris Dukes's direction. Agreement between assistants is review input; experimental evidence must come from the recorded study. The [Linear project](https://linear.app/cld-maindev/project/quantum-bridge-lab-cc3b6e3fff04) tracks progress; the repository contains the research record for readers without Linear access.

## Try the offline checks

Use macOS or Linux, Python 3.11 and [uv](https://docs.astral.sh/uv/). From a source checkout:

```sh
git clone https://github.com/clduab11/quantum-bridge-lab.git
cd quantum-bridge-lab
uv sync --frozen
PYTHONPATH=src PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 uv run --frozen pytest -q
uv run --frozen ruff check src tests analysis
PYTHONPATH=src uv run --frozen python -m qbridge.preflight --output-dir preflight-output
```

These checks need no model API key. The final command requires a new output directory and saves the exact tested inputs, logs and engineering report. It runs analytic identities and fabricated-data checks, including a constant-score optimizer fixture. It evaluates no candidate on the study objective and calls no experimental model. It provides no network sandbox.

The process executor requires a single-threaded POSIX caller, and callbacks must not detach into new sessions. Its local cancellation cannot cancel work already accepted by a remote provider. `InlineExecutor` is for synthetic timing fixtures only.

## What comes next

The next milestone is [provider feasibility and full-run cost planning](research/PROVIDER_FEASIBILITY.md). An [offline budget calculator](research/BUDGET_PLANNING.md) now shows how input limits, prices, retries and preflight calls affect a conditional cost ceiling. Its inputs still need verification before a spending decision.

A real provider adapter, complete study launcher, protected data storage, custody assignments and the final frozen run manifest remain unfinished. [Implementation readiness](research/IMPLEMENTATION_READINESS.md) tracks these requirements. There is currently no command that launches the full experiment.

Scientific changes must be recorded prospectively. Historical reviews and synchronization receipts describe their own point in time; current status is stated above and in the readiness record. Study transcripts, results and private comparison mappings must stay out of public engineering artifacts.
