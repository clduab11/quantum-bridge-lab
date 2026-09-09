# Separate Count-Request Budget Implementation Plan

> **For agentic workers:** Use superpowers:executing-plans to implement this bounded task inline. Parallel Codex workers previously exhausted their quota; Claude Science is independently reviewing the prospective amendment.

**Goal:** Calculate the proposed count and generation allowances separately, without turning unknown count fees into a numeric total or authorizing spending.

**Architecture:** Keep the existing v0.4 calculator unchanged. A separate pure function reuses its generation arithmetic and validated decimal input grammar, adds a distinct count-request reservation, and emits JSON-compatible exact subtotals. It performs no network, objective evaluation, environment inspection or file writes.

**Tech Stack:** Python 3.11, existing qbridge.budget, Decimal with a local 100-digit context, pytest.

**Spec:** research/execution-preparation/CONTRACT_RESOLUTION_PROPOSAL.md and the concrete design sent to Claude Science's Counted Responses Amendment Technical Review on 2026-09-08. This resource design is prospective and not adopted; adoption is separate from implementing conditional arithmetic.

## Global Constraints

- Generation output ceiling remains 8192 tokens.
- Two stages, 20 blocks each; 19 optimizer batches/block, up to two logical calls/batch.
- Proposed count and generation classes each allow three attempts/logical call: at most 4560 of each across the study.
- The proposed four-fixture E9 has at most 12 count and 12 generation attempts. Calculator inputs keep those allowances separate.
- Count fees are not documented free; missing fees must remain null/unknown. Supplied fees and other reserves remain conditional, not verified billing.
- A monetary scenario is not provider selection, protocol adoption, spending authority, a freeze or a study result.

## Task 1: Calculate Separate Request-Class Scenarios

**Files:** Create src/qbridge/count_budget.py, tests/test_count_budget.py and research/counted-admission/BUDGET.md. Leave src/qbridge/budget.py unchanged.

**Interface:**

```python
calculate_counted_budget(
    *, input_token_ceiling: int,
    input_usd_per_million: str, output_usd_per_million: str,
    count_attempt_fee_ceiling_usd: str | None,
    extra_usd_reserve: str,
    max_e9_count_attempts: int, max_e9_generation_attempts: int,
) -> dict
```

Consumes explicit prospective limits/rates; produces separate count/generation subtotals and a nullable combined monetary ceiling. It reports both stages, all allotted objective slots, both attempt classes and total attempts. It always reports `spending_authorized`, `billing_complete` and `protocol_adopted` as false.

- [x] Add tests for unknown count fee, separately bounded E9 allowances, exact arithmetic with a hostile ambient Decimal context, and invalid count-specific inputs. The central expectations are:

```python
unknown = calculate_counted_budget(
    input_token_ceiling=200_000, input_usd_per_million="5",
    output_usd_per_million="20", count_attempt_fee_ceiling_usd=None,
    extra_usd_reserve="0", max_e9_count_attempts=12,
    max_e9_generation_attempts=12,
)
assert unknown["combined_ceiling_usd"] is None
assert unknown["count_requests"]["study_attempts"] == 4560
assert unknown["all_request_attempts"] == 9144
```

- [x] Run the new tests and observe the missing-module failure.
- [x] Implement generation subtotals via `qbridge.budget.calculate_budget`; validate the separate count allowance via its `_count` helper and a supplied count fee via `_money`. Under a fresh 100-digit Decimal context, sum exact generation cost, `(4560 + max_e9_count_attempts) * count_fee`, and extra reserve, then round upward only the final ceiling. When count fee is null, retain a null count subtotal and combined total regardless of reserve; never substitute zero.
- [x] Verify the supplied-fee example independently: L=200000, rates5/20, fee0.10, E9 counts12/generations12 gives generation5321.07648 + counting457.2 = 5778.27648, rounded upward5778.28. A zero explicitly supplied count fee remains a conditional assumption, not evidence counting is free.
- [x] Run the new tests and the existing budget tests, then Ruff and diff checks. Do not rerun unrelated physics checks for a pure arithmetic module.
- [x] Document the two-class counts, assumptions, nullable total and that 7400 seconds is a proposed monotonic E9 stop limit; overhead and longer server waits consume part of it, so the nominal fixed-backoff sum is not a completion guarantee. Commit the bounded change on research/counted-admission (commit follows the recorded checks).

Self-review: all arithmetic and uncertainty requirements map to this task. Provider transport, the prospective amendment and full execution assembly are separate deliverables and are not claimed implemented here. Inline execution is already authorized; no additional execution-choice question is needed.
