# Execution preparation — 2026-09-08

Chris instructed Codex to perform the provider-contract, budget/preflight and gated study steps in the Claude Science project. This is new proceed authority, superseding the earlier phase's offline-only scope. It does not supply a numerical spending ceiling or turn unmeasured provider behavior into evidence. Claude Science is working in **Sol Chat Request Contract & Budget Proposal** from the published source commit `b89297cfbbca1a922110ef22c9c157e3f63f7fa7`.

This package contains work actually performed by Codex: four fixed fabricated E9 request payloads, their history inputs and hashes, three conditional budget calculations, all 40 deterministic seed records, and the existing candidate Python environment's version capture. The accompanying [contract check](CURRENT_CONTRACT_CHECK.md) and [gate audit](GATE_AUDIT.md) record independent source and protocol checks. No provider SDK or dispatch function is added here. No real mapping, model request, token-count request or study-objective evaluation was performed by this preparation script. The candidate environment is not automatically the study environment.

## Fixed E9 proposal

The four logical fixtures are a short 10-row history, a legal long-spelling 190-row history, an exact repeat of the latter, and its exact fixed synthetic correction suffix. The long history is a boundary-oriented example, not proof of the maximum possible provider token count. Every score is fabricated. No returned proposal will be evaluated during E9.

The proposed cap is **four logical fixtures and 12 transport attempts total**, using at most three identical-request attempts per fixture and 5/20-second waits. Retry only connection failures, timeouts, HTTP 429 or 5xx. A malformed 2xx response ends that fixture after logging and parsing; it does not introduce an extra correction request beyond fixed F4. Unsupported configuration, materially missing required identity, or an unresolved admission/billing contract prevents further dispatch. A prospective configuration change requires a new version and recorded allowance.

The proposed overall E9 deadline is 3,700 seconds including overhead. That is a stop limit, not a guarantee that all attempts finish; unfinished work is forfeited without replacement. A live runner still needs durable reservation before each dispatch, retained maximum reservations for unknown usage, exact metadata/usage capture, and monetary-cap enforcement. These payloads alone implement none of those execution controls.

## Conditional cost scenarios

All figures below reserve 4,560 study attempts plus 12 E9 attempts, with an inclusive 8,192-token output cap. They exclude unresolved account/region/tax and other unpriced charges; the zero additional reserve is an explicitly incomplete scenario. They are neither expected bills nor spending authorization.

| Assumed input tokens per attempt | Input/output USD per million | Study + E9 maximum token-charge scenario |
| --- | --- | --- |
| 50,000, hypothetical | 4 / 20 | 1,663.48 USD |
| 108,835, arbitrary token hypothesis numerically equal to a text-byte bound | 4 / 20 | 2,739.46 USD |
| 922,000, documented model input maximum used only as a conditional reserve | 8 / 30 | 34,846.69 USD |

The final scenario does not prove how rejected oversized attempts are billed, that any legal prompt fits, or that account adjustments are absent. Public rates are date-sensitive; see the primary sources and limitations in the contract check. A firm proposal still requires endpoint-specific input accounting, complete applicable charges and price validity, actual account access, and a numerical authority record. An arbitrary token margin cannot supply those facts.

## Reproduction and verification

From the repository root with the existing Python 3.11 dependencies installed:

```sh
PYTHONPATH=src python research/execution-preparation/build_offline_inputs.py
```

The script regenerates this directory's JSON inputs. It checks the 27 previously tested source hashes, exact prompt bytes, all fabricated history indexes and geometric/score constraints, renderer acceptance, exact F2/F3 identity and F4 suffix, independent Decimal budget arithmetic, and repeatable seed records for blocks 0–39. It uses no network or objective function. The 233-test result remains the earlier source verification; this preparation is a separate set of recorded checks, not a claim to have rerun that suite.

`manifest.json` keeps execution, billing, tokenizer and freeze flags false. A failed or unknown requirement must not be replaced with a guessed value. The provider adapter, admission counter, full-run coordinator, actual storage/custody and complete freeze manifest remain separate work until implemented and verified in the selected runtime.
