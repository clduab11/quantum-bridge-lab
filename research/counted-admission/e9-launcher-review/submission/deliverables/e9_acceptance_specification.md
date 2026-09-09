# E9 acceptance specification

Generated from the code that enforces it (`qbridge_e9.acceptance`, `qbridge_e9.gate`, `qbridge_e9.fixtures`) so the table cannot drift from the implementation. Source of the requirements: amendment A1 section A1.11 (**proposed**, revision 2) and protocol v0.4 section 6.1/6.7.

**E9 has not been run. No condition below has been evaluated against a provider.** The status column shows the result of the offline dry run against fabricated responses, which demonstrates that each condition is decidable — not that any of them holds in reality.

## 1. Pass conditions

E9 passes only if **every** condition holds on **every one of the four fixtures**. HTTP 200 is explicitly insufficient: a 200 carrying a `failed` or `incomplete` object, a profile echo mismatch, a usage/count inequality or any cache activity all fail E9.

| # | A1 requirement | Enforced by | Dry-run status |
|---|---|---|---|
| 1 | Exactly four fixed fixtures, each run as one logical call | `orchestrator.run / e9_logical_finished` | pass |
| 2 | Unknown usage, profile mismatch, count/usage inequality or cache activity fails E9 | `provider._persist_halt / orchestrator._halt` | pass |
| 3 | Pass condition 1: valid count on every fixture | `contract.validate_count_payload via provider.count; count_receipt event` | pass |
| 4 | Pass condition 2: required echo fields equal the frozen profile (A1 6.1) | `contract.validate_expected_profile (provider._received_object step 2)` | pass |
| 5 | Pass condition 3: usage.input_tokens == count with all mandatory categories | `contract.usage_checks + settle_response (policy='e9')` | pass |
| 6 | Pass condition 4: cached_tokens == cache_write_tokens == 0 | `contract.usage_checks cache_activity findings (IVF under e9 policy)` | pass |
| 7 | Pass condition 5: identity vector recorded for every fixture | `contract.identity_vector; provider identity_observation event` | pass |
| 8 | Pass condition 5: F2 and F3 identity vectors identical | `contract.compare_identity` | pass |
| 9 | Pass condition 6: count(F3) == count(F2) | `orchestrator count_receipt events` | pass |
| 10 | Pass condition 7: section 6.7 parse result logged | `qbridge.proposals.parse_response; e9_parse_result event` | pass |
| 11 | A provisional E9 identity observation is not an accepted baseline | `provider.identity_baseline (E9 records identity_observation, never identity_baseline)` | pass |
| 12 | Record actual F2/F3 timing; claim no cache-window coverage not demonstrated | `orchestrator LogicalOutcome.generation_started_monotonic` | pass |

## 2. Explicit non-claims

- **A provisional identity observation is not an accepted baseline.** E9 records `identity_observation` events with `provisional: true, accepted: false`. The launcher never calls `seed_identity_baseline`; entering a baseline into the manifest is a separately recorded acceptance decision. Asserted by `test_no_study_baseline_is_ever_seeded_by_the_launcher`.
- **No cache-window coverage is claimed.** The F2→F3 gap is recorded as a number and nothing is inferred from it. A zero-cache E9 pass demonstrates no cache lifetime; it demonstrates only that no cache activity occurred within that particular gap.
- **An over-limit count is a finding, not a reason to retune.** If a count exceeds `L* = 272,000`, generation is not dispatched and the finding is recorded for a revised amendment. `L*` is asserted unchanged by `test_admission_rejection_blocks_generation_and_is_only_a_finding`.
- **Equality of count and usage at E9 is necessary, not sufficient** for the confirmatory claim in the A1 adoption sequence.
- **The identity vector is weaker than a serving fingerprint.** The reviewed Responses route exposes none, so weight or serving changes that leave the echo unchanged are undetectable.
- **A failed E9 forfeits its spend and produces no baseline.** Any halt is recorded and the run stops; there is no partial acceptance.

## 3. Live-dispatch gate

Separate from acceptance. Acceptance asks whether an E9 that ran was good; the gate asks whether E9 may run at all. Every requirement is evaluated independently and **an unresolved requirement is a failure, never a default**. There is no third status.

| Requirement | Key | Dry-run status |
|---|---|---|
| A validated AuthorityRecord is supplied | `authority.present` | pass |
| authority.synthetic is False | `authority.not_synthetic` | fail |
| authority scope is the E9 halt policy | `authority.scope` | pass |
| attempt caps equal the E9 allowance | `authority.caps` | pass |
| frozen request profile matches the reviewed contract | `authority.profile` | pass |
| recorded prices are valid at dispatch time | `authority.price_validity` | pass |
| count fee is verified and covers failed/rejected calls | `authority.count_fee` | fail |
| an explicit positive USD ceiling is recorded | `authority.numeric_ceiling` | fail |
| Amendment A1 adoption is recorded | `adoption.record` | fail |
| the operative protocol file matches its hash | `adoption.operative_protocol` | fail |
| the model rate source is retained and hashed | `billing.rate_source` | fail |
| count-request charging evidence is retained and hashed | `billing.count_fee_source` | fail |
| account billing terms are recorded | `billing.account_terms` | fail |
| an explicit numeric E9-only authority exists | `authorization.explicit_e9` | fail |
| installed openai==3.9.0 and httpx==0.28.1 | `environment.sdk_versions` | pass |
| the authority pins the installed SDK versions | `environment.authority_pins` | pass |
| OPENAI_API_KEY is present in the environment | `credential.present` | fail |
| raw records are stored privately outside Git | `records.private` | pass |

Dry-run gate result: **8 of 18 passed, 10 failed, `may_dispatch_live: false`** — the correct outcome, since the dry run supplies a synthetic authority and no evidence.

The gate is demonstrably satisfiable: `test_a_complete_consistent_non_synthetic_evidence_set_passes` builds a complete, consistent, non-synthetic evidence set inside a temporary directory and asserts all 18 pass, and a companion test removes each element in turn and asserts the gate closes again. Without that pair, an always-refusing gate would be indistinguishable from a correct one.

## 4. Fixture binding

`verify-fixtures` records **76 checks, 0 failed** (68 without a provider; the extra 8 are the provider's own `prepare` reproductions of the committed bytes). Each check raises on failure rather than warning.

| Check family | Count |
|---|---|
| eight committed payload hashes bound | 8 |
| eight committed payload byte lengths bound | 8 |
| committed bytes are canonical | 8 |
| developer/user text identical between count and generation | 8 |
| manifest text hashes bound | 8 |
| provider.prepare reproduces the committed bytes | 8 |
| A1.11 frozen request profile | 7 |
| prospective state preserved | 7 |
| manifest source hashes bound | 5 |
| count-to-send identity (contract.verify_pair) | 4 |
| A1.11 F3 is a byte-identical repeat of F2 | 2 |
| A1.11 exactly four fixed fixtures | 1 |
| declared order is the execution order | 1 |
| builder hash bound | 1 |

Execution order is the manifest's declared order and is asserted to be exactly `F1_short → F2_maximal_renderer → F3_repeat_of_F2 → F4_correction_no_valid_vectors`.
