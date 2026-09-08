# Offline Budget Scenario Calculator Implementation Plan

> **For agentic workers:** Use Superpowers test-driven development and verification before completion. The delegated worker implements this bounded task in its isolated worktree; the coordinating agent reviews and integrates it.

**Goal:** Calculate conditional token and USD ceilings for both protocol stages without making provider calls or evaluating the study objective.

**Architecture:** A standard-library module accepts all monetary and provider-dependent assumptions explicitly, performs exact Decimal arithmetic, and returns JSON-compatible values. Its CLI prints the same result to stdout. It is a planning tool and cannot verify pricing, tokenization, billing completeness, or authorization.

**Tech Stack:** Python 3.11, `decimal`, `argparse`, `json`, pytest; no dependency changes.

**Spec:** `specification/ai_quantum_control_protocol_v0.4.md`, sections 6–8 and 12; delegated budget-planning scope recorded below. This does not amend that protocol.

## Global constraints

- Include all 40 blocks, 19 scheduled calls per block, at most one correction per scheduled call, and three transport attempts per logical call: 760 scheduled calls, 1,520 logical calls, 4,560 attempts. All three arms have 24,000 allotted objective slots altogether.
- Per-attempt input tokens are an explicitly supplied, externally verified ceiling; this tool does not derive or verify it. The 8,192 output-token cap is conditional on all billable output categories, including reasoning when applicable, being included within that cap.
- Require input USD/million, output USD/million, additional USD reserve, and maximum E9 attempts. Explicit zero is accepted where nonnegative values are appropriate; omitted or unknown values never become zero.
- Input rate must conservatively include every applicable additive input/cache cost, and output rate must include every applicable billable output category. Externally verify these assumptions; additional costs require a sufficient explicit reserve. An explicit zero reserve does not establish that other charges are absent.
- Keep E9 separate and apply the same supplied per-attempt ceilings to its attempts; no automatic multiplication of an already counted E9 attempt limit.
- Use exact Decimal arithmetic; round each combined total upwards to cents. These are conditional scenario ceilings, never expected or observed spending.
- No network, credentials, objective calls, file-output writes, provider hardcodes, execution authorization, or freeze action.
- Arithmetic limits: input ceiling 1 through 1,000,000,000 tokens, E9 attempts 0 through 1,000,000; monetary strings at most 64 characters, at most USD 1,000,000,000,000, decimal exponent between -12 and 12. These are tool limits, not provider capabilities.

## Task 1: Exact arithmetic and explicit input contract

**Files:** Create `src/qbridge/budget.py`; create `tests/test_budget.py`.

**Interface:**

```python
def calculate_budget(
    *,
    input_token_ceiling: int,
    input_usd_per_million: str,
    output_usd_per_million: str,
    extra_usd_reserve: str,
    max_e9_attempts: int,
) -> dict:
    ...
```

- [x] Write literal hand-calculation tests before implementation. At 1,000 input tokens, input rate USD 2/million, output rate USD 3/million, two E9 attempts and USD 0.001 reserve: one attempt costs USD 0.026576; 760 scheduled attempts cost USD 20.197760; 4,560 attempts cost USD 121.186560; E9 costs USD 0.053152. Rounded combined totals are USD 20.26 and USD 121.25.
- [x] Run the arithmetic tests and record failure due to the absent calculator.
- [x] Implement those results from protocol counts using `Decimal`, keeping input/output subtotals and E9 distinct. Use a local precision of 100 digits, independently of the caller's Decimal context, and `ROUND_CEILING` when quantizing combined totals to `Decimal('0.01')`.
- [x] Add failing input-contract tests: omitted/unknown keywords; booleans, floats and strings as integer counts; zero input ceiling; negative counts; NaN/infinity, numeric rather than string money, negatives, malformed decimal text and documented bounds. Verify failures, then add strict validation.
- [x] Run all API tests to verify exact totals, retained non-authorization status, explicit zeros, and resistance to a caller's low Decimal precision.

## Task 2: Stdout-only CLI

**Files:** Extend the same module and test file.

**Interface:**

```console
python -m qbridge.budget --input-token-ceiling 1000 --input-usd-per-million 2 --output-usd-per-million 3 --extra-usd-reserve 0.001 --max-e9-attempts 2
```

- [x] Write subprocess tests for valid JSON output, omission of every required option, rejection of an unknown option, and invalid money/count input; run and observe absent-CLI failures.
- [x] Implement `main(argv=None)` with all five options required and no output-path option. Validate using the API; report input errors through argparse and print sorted JSON on success.
- [x] Run the module tests and Ruff. Confirm the module path resolves to this worktree, inspect the diff for only the three scoped files, record verification below, and commit for coordinator review.

## Verification commands

```console
PYTHONPATH=src PYTHONPYCACHEPREFIX=/tmp/qbridge-budget-pycache PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 /tmp/quantum-bridge-preflight-runtime/bin/python -m pytest tests/test_budget.py
/tmp/quantum-bridge-preflight-runtime/bin/ruff check src/qbridge/budget.py tests/test_budget.py
/tmp/quantum-bridge-preflight-runtime/bin/ruff format --check src/qbridge/budget.py tests/test_budget.py
```

If an installed editable namespace shadows the isolated worktree, run Python with `-S` and place this worktree's `src` before the runtime's site-packages in `PYTHONPATH`. Do not reinstall the shared environment.

## Execution evidence

- Arithmetic/status red: four tests failed because `qbridge.budget` did not exist. Minimal arithmetic implementation made all four pass.
- Validation red: 37 failures and 11 passes before strict validation; afterwards 48 tests passed. The already-passing omitted/unknown-keyword tests characterize the explicit keyword-only API boundary.
- CLI red: 10 failures and 48 passes because the module did not yet emit JSON or reject CLI options; the implementation brought the total to 58 passes.
- Context regression red: setting caller `Emax=2` and `Emin=-2` raised `decimal.Overflow`. Using a fresh local `Context(prec=100)` fixed that case without rounding or global context mutation.
- Final targeted verification: **59 passed in 0.43 seconds**. Ruff 0.16.6 check passed; Ruff format check reported both files already formatted. No new dependencies.
- Imported source verified at `/private/tmp/quantum-bridge-budget-worktree/src/qbridge/budget.py`; no shared environment reinstall was used.
- CLI tests ran normally and with Python `-OO`, verified JSON and empty stderr, and confirmed no result files appeared in the supplied empty working directory.
- The five fixture prices/caps are arithmetic examples only. No provider prices or tokenizer limits were verified, no paid call or objective evaluation occurred, and no readiness gate or spending authority was opened by this change.
