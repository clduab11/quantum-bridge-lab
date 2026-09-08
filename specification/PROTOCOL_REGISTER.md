# Protocol and provenance register

Revision: governance-v2, 2026-09-08. Phase: reviewed design v0.4; implementation readiness pending. **NOT FROZEN. NO EXPERIMENT RUN OR RESULT CLAIMED.**

## Authority and ownership

Chris directs the top level and has authorized expert research, document implementation and all pre-freeze corrections by Codex and Claude Science. Routine expert choices and reversible corrections do not require repeated approval. This delegation is not a fabricated protocol freeze, run authorization or independent-custodian assignment.

Codex coordinates adversarial review, provenance and synchronization. Claude Science develops and challenges the scientific specification. Independent research agents check primary evidence. Protocol v0.4 selects locked automated analysis and unmasking sequencing, explicitly without independent evaluator blinding. Actual roles and protected storage must be established before evaluative data are used.

## Canonical surfaces

- [Repository](https://github.com/clduab11/quantum-bridge-lab): authoritative versioned artifacts, evidence register and protocol status. Working branch: `research/protocol-hardening`.
- [Linear project](https://linear.app/cld-maindev/project/quantum-bridge-lab-cc3b6e3fff04): task state, dependencies and links to the exact repository revision; team `advanced-research`.
- Claude Science project `proj_993c3d0d7ed9`, session `8b04c2b2-d8cc-4714-9c17-f91d8a9c2540`: scientific collaboration and saved versioned artifacts. Its local browser URL is accessible only on the host running the application.
- [Evidence and correction register](PREIMPLEMENTATION_REVIEW.md): common source IDs and explicit unresolved questions.

Repository and Linear are separate from `qrc-thresher` and `quantum-index`; no predecessor project was modified or canceled by this work.

## Preserved artifact manifest

| Artifact | Origin / version | Bytes | SHA-256 | Meaning |
| --- | --- | --- | --- | --- |
| [Original design v0.1](../sources/original/ai_quantum_control_minimal_experiment_v0.1.md) | Claude Science artifact `6fd55096-2b8c-45cc-81b8-0ed788780b3f`, version `55a1a8db-9e62-45e7-b4c9-32b20cff7580` | 23862 | `b80217ffd36418eb3932be6c7df96181736daa8be31023752c9743b64c11fd4b` | Exact bytes copied from saved app artifact; equal to workspace copy and repository intake copy when checked on 2026-09-08. Historical design, not approved protocol. |

The artifact manifest avoids private filesystem paths. Future originals and completed Claude responses receive separate versioned paths and observed hashes. Never overwrite an original with a correction. A file hash proves byte identity, not scientific validity or human approval.

## Gates

| Gate | Required evidence | Current state |
| --- | --- | --- |
| Evidence reconciliation | Context7 and Exa primary sources, common scope and correction IDs, synchronized Linear brief | Complete: verified v1 preflight; v2 closes the review record |
| Corrected design | Completed Claude hardening exchange, saved corrected artifact, closed fatal/required findings | Complete at the design-text level in v0.4 |
| Implementation readiness | Complete config and prompts, actual model/interface and package feasibility, bounded costs and failure rules, outcome-exposure record | Pending; no code or experiments in this phase |
| Protocol freeze | Complete version manifest referencing design, code, prompts, config, seeds, analysis, dependency versions and protected mapping commitment; all required findings closed; recorded authority | Pending |
| Evaluation and analysis | Authorized execution at frozen revision; append-only logs; all planned blocks accounted for; locked analysis; documented unmasking | Not started |

Preflight engineering checks must be specified in advance, use analytic identities or clearly synthetic interface data, and preserve all access records. Evaluating a candidate on the study objective is an exposure event even when called a sanity check. Any redesign after exposure is prospective, labeled and cannot erase the prior attempt.

## Freeze and amendment contract

At freeze, enumerate actual paths and SHA-256 values for every protocol-defining artifact and the containing Git commit. Record actual environment/model versions, decoding configuration, prompt hashes, seed lists, action mapping, exact primary estimand, uncertainty calculation, margin, decision rules, endpoint scoring, run order, retries, resource caps and all costs excluded from the primary budget. Unknown values block freeze rather than receiving plausible placeholders.

Freeze and execution are distinct events. Each requires its actual decision record referencing the immutable manifest. If existing explicit authority covers an action, cite it accurately rather than re-requesting permission; never generate a record pretending to be human-authored. Later changes append date, author/agent, old/new revision, reason and pre/post-outcome-exposure status. Preserve failed, null, inconclusive and contradictory attempts with the same provenance.

## Blinding and data contract

Define the independent analysis unit as a complete planned seed block, not grid nodes or candidate evaluations. Protect the mapping and identity-bearing transcripts outside the public repository. Masked data must omit identifiers, timestamps, token counts, pulse shapes and invalid-output markers when they reveal method identity. Do not claim this makes curves or outcomes unrecognizable.

Before any real data, lock the exact analysis and the means of selecting the prespecified comparison. One option is to compute an identical locked summary for every ordered label pair and let the custodian select the precommitted pair after the output is sealed; these nuisance summaries are not additional hypothesis claims. Another is an isolated custodian-controlled analysis job. Protocol v0.4 §10 selects the locked all-ordered-pair summaries with automated precommitted-pair selection; independent human custody remains a possible future pre-exposure amendment, not an unmade choice. The public registry records actual custody and residual exposure, not fictitious independence among agents sharing context.

## Synchronization and claim rules

Every synchronized brief carries its revision, repository commit or file hash, source IDs, phase, open correction IDs and next gate. After a change: verify Git bytes, update the Linear document/issue, save the corresponding Claude artifact or project context, then re-read both. A failed synchronization remains explicitly pending; never report uniformity from attempted writes.

Scientific propositions remain hypotheses. Simulated results apply only to the measured instance and configured methods. Engineering claims require actual runtime/reliability evidence. Hardware, quantum advantage, scale and commercial claims require further experiments and are speculative here. No method-mechanism claim follows from performance alone.


## Current reviewed design and evidence lineage

[Protocol v0.4](ai_quantum_control_protocol_v0.4.md) is the operative reviewed design. It is not a frozen run manifest. [Draft PR #1](https://github.com/clduab11/quantum-bridge-lab/pull/1) contains the implementation of the authorized documentation work. [ADV-35](https://linear.app/cld-maindev/issue/ADV-35/reconcile-evidence-and-close-r1-r10-before-protocol-freeze) tracks design correction; [ADV-36](https://linear.app/cld-maindev/issue/ADV-36/verify-implementation-readiness-and-freeze-the-complete-run-manifest) tracks the later readiness/freeze gate.

Observed artifact hashes (not approval signatures):

- `sources/original/quantum_bridge_round1_response.md` — 29304 bytes; SHA-256 `3bed166a7ff71eef434be8b0fac2c8796662e59ef01727b305d314f544a0ea81`.
- `sources/original/ai_quantum_control_protocol_v0.2.md` — 41715 bytes; SHA-256 `0e612751c7b26d1b97ce15158cb423a52112610882f2bac3f6090042e0409e1b`.
- `sources/original/round2_disposition.md` — 11075 bytes; SHA-256 `93893a0905e962ce56dddb0a0782d709a1dc7d01f6abf9782b452470aea33be6`.
- `specification/ai_quantum_control_protocol_v0.4.md` — 52526 bytes; SHA-256 `0df9242fd2d0ad5d30b75ea91f498842ac68fe0df9616afd4c9c04518233eda5`.

Evidence-brief-v1 and governance-v1 were published at Git commit `2d50535a27ec0fd137f9f8ecd1144f369ab09a81` and saved unchanged in Claude Science. Their SHA-256 values were `2f53b434ce2156b6d8324138ebaadd780aeadd517dd88ecc73bc5a1949ba74b9` and `02a29464d654941778cb478521d550cbaa5f50b0acfae9e22dca437dbe658bf8`. Linear's v1 content matched after only its Markdown link/table formatting normalization. This v2 registry records subsequent review closure while the historical v1 remains accessible in Git and the Claude artifact library.

Claude Science Project Settings were updated through the existing Edge Playwright session; the original Agent Context was retained verbatim as explicitly superseded history and verified by UI readback. Its active context narrows scope, preserves source disagreement, records the user's delegation, and distinguishes design review from freeze/execution.

The next gate is permitted implementation/preflight and concrete readiness evidence, including G-COST. No package installation, study-objective evaluation, controller implementation or experimental model call occurred during this documentation work. Algebraic/binomial arithmetic and metadata/document operations are recorded separately from experiments.

- Preserved `sources/original/ai_quantum_control_protocol_v0.3.md` — 50352 bytes; SHA-256 `784940f63b2bb1eae5355c476d505cdbfc015969bacac34a880f348d78e2e762`.

- Preserved `sources/original/round3_disposition.md` — 8460 bytes; SHA-256 `0f9857687cae78ac9c595744e939971522285f3947ed06be5a3f4200708fc6c4`.
