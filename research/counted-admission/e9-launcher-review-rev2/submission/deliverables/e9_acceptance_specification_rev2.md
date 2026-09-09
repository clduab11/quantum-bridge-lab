# E9 acceptance specification — revision 2

Generated from the code that enforces it (`qbridge_e9.acceptance`, `qbridge_e9.gate`, `qbridge_e9.fixtures`, `qbridge_e9.money`) so the tables cannot drift from the implementation. Requirements source: amendment A1 section A1.11 (**proposed**, revision 2) and protocol v0.4 sections 6.1/6.7.

**E9 has not been run. No condition below has been evaluated against a provider.** The status column is the result of the offline dry run against fabricated responses, which shows each condition is decidable — not that any of them holds in reality.

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

Dry run: **12 of 12 passed, `e9_accepted: true`** against fabricated responses.

## 2. Explicit non-claims

- **A provisional identity observation is not an accepted baseline.** E9 writes `identity_observation` events with `provisional: true, accepted: false`. The launcher never calls `seed_identity_baseline`; entering a baseline into the manifest is a separately recorded acceptance decision. Asserted by `test_no_study_baseline_is_ever_seeded_by_the_launcher`.
- **No cache-window coverage is claimed.** The F2→F3 gap is recorded as a number and nothing is inferred from it. A zero-cache E9 pass demonstrates no cache lifetime — only that no cache activity occurred within that particular gap.
- **An over-limit count is a finding, not a reason to retune.** A count above L\* = 272,000 is recorded and the fixture is rejected; the admission limit is never adjusted to fit an observation.
- **Count/usage equality is necessary, not sufficient**, for the confirmatory claim.
- **The identity vector is weaker than a serving fingerprint.** The Responses route exposes no serving fingerprint, so weight or serving changes that leave the echo unchanged remain undetectable.
- **The attempt wall clock bounds a socket, not arbitrary code.** A synchronous in-process handler cannot be preempted; its late result is refused and recorded, but its worker thread runs to completion. Recorded in the report as `attempt_wall_clock_enforced_at_transport: true` with the limitation stated alongside.
- **A hash match is not verification of a charge or of an approval.** It shows a retained file is the one that was recorded.

## 3. Live-dispatch gate

Every requirement is evaluated independently. An unresolved requirement is a **failure**, never a default. There is no third status.

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
| the ceiling covers the conservative worst case for every allowed attempt | `authority.conservative_ceiling` | pass |
| Amendment A1 adoption is recorded | `adoption.record` | fail |
| the operative protocol file matches its hash | `adoption.operative_protocol` | fail |
| the model rate source is retained and hashed | `billing.rate_source` | fail |
| count-request charging evidence is retained and hashed | `billing.count_fee_source` | fail |
| account billing terms are recorded | `billing.account_terms` | fail |
| an explicit numeric E9-only authority exists | `authorization.explicit_e9` | fail |
| the approval is a valid, non-expired UTC record bound to this authority | `authorization.bound_and_timed` | fail |
| installed openai==3.9.0 and httpx==0.28.1 | `environment.sdk_versions` | pass |
| the authority pins the installed SDK versions | `environment.authority_pins` | pass |
| OPENAI_API_KEY is present in the supplied environment | `credential.present` | fail |
| raw records are stored privately outside any Git worktree | `records.private` | pass |

Dry-run gate: **9 of 20 passed, 11 failed, `may_dispatch_live: false`** — the correct outcome, since the dry run supplies a synthetic authority and no evidence. With no evidence at all, 19 of 20 fail and only `environment.sdk_versions` passes.

New in revision 2: `authority.conservative_ceiling` (the ceiling must fund every allowed attempt at the worst applicable input category) and `authorization.bound_and_timed` (the approval must parse as a UTC instant, not be future or expired, and carry the digest of the authority it authorizes). `billing.account_terms` additionally requires month-to-date spend and concurrent project traffic, because a project hard limit is monthly and covers all traffic in the project.

The gate is demonstrably satisfiable: `test_a_complete_consistent_non_synthetic_evidence_set_passes` builds a complete, consistent, non-synthetic evidence set inside a temporary directory and asserts all 20 pass, and a companion removes each element in turn to assert the gate closes again. Without that pair, an always-refusing gate would be indistinguishable from a correct one.

## 4. Fixture binding

`verify-fixtures` records **96 checks, 0 failed** (88 without a provider; the extra 8 are the provider's own `prepare` reproductions of the committed bytes). Each check raises on failure rather than warning.

The reviewed digests are **pinned in `qbridge_e9.fixtures`**, not taken from the manifest: the manifest is checked against the pin, the eight payloads are checked directly against the pin, and the five reviewed source files plus the builder are verified at a **required** `repo_root`. A self-consistent replacement fixture is refused.

| Check family | Count |
|---|---|
| committed bytes are canonical | 8 |
| developer/user text identical between count and generation | 8 |
| manifest payload digests agree with the pin | 8 |
| manifest payload paths are the reviewed ones | 8 |
| manifest text hashes bound | 8 |
| pinned reviewed payload digests | 8 |
| provider.prepare reproduces the committed bytes | 8 |
| A1.11 frozen request profile | 7 |
| prospective state preserved | 7 |
| reviewed source digests agree with the pin | 5 |
| reviewed source files verified at repo_root | 5 |
| count-to-send identity (contract.verify_pair) | 4 |
| developer text is the reviewed system prompt | 4 |
| A1.11 F3 is a byte-identical repeat of F2 | 2 |
| A1.11 exactly four fixed fixtures in the reviewed order | 1 |
| complete reviewed source set declared | 1 |
| declared order is the execution order | 1 |
| no unreviewed payload files present | 1 |
| pinned reviewed manifest digest | 1 |
| reviewed builder verified at repo_root | 1 |

Execution order is the manifest's declared order, asserted to be exactly `F1_short → F2_maximal_renderer → F3_repeat_of_F2 → F4_correction_no_valid_vectors`.
