# Synchronization receipt — Codex PR #4 milestone, commit `8cb9acb9…` (2026-09-08)

**Scope of this turn:** fetch, verify and save only. No code execution, tests, provider, count or objective request, and no new technical decision were made. Protocol v0.4 (`0df9242f…3eda5`) unchanged and unfrozen; no provider choice, gate success, mapping, live call, spending authorization or freeze is inferred.

## 1. Fetched and verified (original bytes saved as project artifacts)

Source: `raw.githubusercontent.com/clduab11/quantum-bridge-lab/8cb9acb920dd1f7691e5539830d410319cb98967/…` (open draft PR #4). SHA-256 computed by Claude Science over the received bytes; all four equal the values Codex stated.

| Path at commit | Bytes | SHA-256 | Saved as |
|---|---:|---|---|
| `research/execution-preparation/STATUS.md` | 5,579 | `071c407ae5747089740061ba445c346f1822dcf3109ae7ed1d85deada4bf9e09` | `codex_pr4_8cb9acb_STATUS.md` |
| `research/execution-preparation/verification/verification.json` | 2,507 | `ebd74af831b3efa59c8ed3732cbd60077df0de3cd98fe0e5325a57f9fa9961d6` | `codex_pr4_8cb9acb_verification.json` |
| `research/execution-preparation/claude-science/IMPORT_VERIFICATION.json` | 3,526 | `283515f225729a893d44ee69365de9460d8a6fe1b0c5f17ff54384824d7178f9` | `codex_pr4_8cb9acb_IMPORT_VERIFICATION.json` |
| `research/execution-preparation/operational-setup.json` | 1,418 | `d1125a8011b362cac61c7fc88a56cb9bec946475516549df530bf4d0a07802c1` | `codex_pr4_8cb9acb_operational-setup.json` |

**Import cross-check (Claude Science's own verification):** every `source_file_sha256` entry in `IMPORT_VERIFICATION.json` equals the checksum recorded when the corresponding artifact was saved in this project — candidate source (`sol_chat_adapter.py` `f1534a10…`, `study_coordinator.py` `4e557812…`, `e9_fixtures.py` `16c89cc2…`, `tests/test_ext.py` `08f474d4…`), portable code archive `4ec36e8a…`, fixtures archive `befdc15f…`, all nine fixture files, the three documents (contract `30d6cd27…`, proposal `7a09b206…`, gate record v2 `4ffca385…`), the assessment `0cc8c335…`, and the corrected records (manifest v2 `c52d4e71…`, exposure log v2 `1f111560…`, documentation sources v2 `6d4891a5…`). `verification.json` lists the same candidate source hashes and the protocol hash.

## 2. Codex's statements (recorded as Codex's results, not rerun or independently checked here)

- 286 tests passed (233 core + 53 candidate) in both the Python 3.11.16 conda environment and a fresh Python 3.11.15 uv-locked environment (candidate lock `c952932a…`, separate from the main lock); ruff lint/format passed; dependency audit: 0 known vulnerabilities in 51 checked packages, the unpublished local project not assessed by PyPI. `provider_contract_verified: false`, `frozen: false`, `study_launcher_complete: false`, zero generation/count/objective calls.
- All 27 baseline source hashes at `b89297cf…` unchanged.
- Operational setup: owner-only (`0700`, UID 502) storage at the recorded path outside Git with four empty subdirectories; automated roles selected (launcher not implemented/running; locked analysis not run); `real_mapping_created: false`; `independent_evaluator_blinding: false`.
- Linear ADV-36, the project description and the readiness document were updated and read back by Codex with this commit, the 286-test scope, the explicitly unadopted proposal, open execution requirements and retained milestones — **Codex's verified Linear statement; no independent Linear check was made by Claude Science.**

## 3. Positions and retained disagreements (both visible)

- Claude Science's assessment (`contract_resolution_assessment_2026-09-08.md`) stands unchanged: the counted-admission Responses design is scientifically valid as an enforcement device and the only tokenizer-independent route to a per-attempt cap, with the reduced identity evidence a substantive limitation to be declared. It is **not adopted**; adoption requires a prospective pre-exposure amendment separate from v0.4 with new fixtures.
- Codex's retained qualifications (STATUS.md), accepted as fair and recorded: (i) count-request failure or input rejection adds a failure mechanism to the LLM arm only — it is not symmetric across arms; a fixed prospective rule can still define the comparison honestly if forfeits and costs are reported; (ii) exact counting supports admission enforcement only conditional on the provider honoring the count-to-generation contract, so count/usage mismatch, tokenizer drift, expiry and unknown charges need explicit handling, and an arbitrary reserve does not make unknown fees a verified bound; (iii) absence of alternatives in the retrieved documentation is not proof that no other provider or contract route exists.
- Earlier retained disagreements (provider review v2, fingerprint-evidence value, pursuit-review points) remain intact. Passing engineering tests are no evidence of optimization benefit or commercial value.

## 4. Outstanding gates — all ten OPEN

G-ENV, G-CMA, G-MODEL, G-TRANSPORT, G-CUSTODY, G-LOCK, G-EXPOSURE, G-STORAGE, G-RUNTIME, G-COST. Concretely absent: an OpenAI credential; a technically supportable billing/admission contract (the prospective amendment, reviewed); a numerical spending decision on a concrete proposal (the scenario tables are not that proposal); the launcher/custody/recovery/export/freeze assembly; any actual E9 evidence. Remaining sequence per STATUS.md §"Remaining sequence" (1–4), unchanged.
