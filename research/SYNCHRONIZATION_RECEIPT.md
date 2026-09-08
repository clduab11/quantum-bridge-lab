# Synchronization verification

Observed 2026-09-08 by Codex after Claude Science completed its final synchronization response. Status: **design review complete; implementation readiness pending; NOT FROZEN.** This records document identity and readback, not engineering validation or experimental results.

| Repository path | Saved Claude Science artifact | Bytes | SHA-256 |
| --- | --- | --- | --- |
| `specification/ai_quantum_control_protocol_v0.4.md` | `ai_quantum_control_protocol_v0.4.md` | 52526 | `0df9242fd2d0ad5d30b75ea91f498842ac68fe0df9616afd4c9c04518233eda5` |
| `specification/PREIMPLEMENTATION_REVIEW.md` | `research_evidence_brief_v2.md` | 15680 | `cfce7428efe4e59316b598b2417c984e9ec75e3294db1bf90a60831726aa9bbe` |
| `specification/PROTOCOL_REGISTER.md` | `protocol_governance_v2.md` | 9771 | `e1839e7802c6ac2cc9703ff38ec29988c0d822ed2d3a09d2e4659a15a34e5e83` |
| `sources/original/final_sync_receipt.md` | `final_sync_receipt.md` | 3831 | `055e6798f886016204dc7250d61a79d6cb39d6190c8f5f2614a8e24ae637cc99` |

The saved project artifacts were read from their actual saved versions and compared byte for byte against these repository files. The original v0.1, Round 1, v0.2, Round 2 disposition, v0.3 and Round 3 disposition also matched their saved artifact bytes. Claude's final receipt is preserved unchanged above.

The Linear evidence-brief-v2 document was retrieved in full after update. It matched the repository brief after only Markdown formatting normalization: angle-bracket link destinations, table separator dashes, bullet markers and excess blank lines. Artifact links in that brief use GitHub URLs so they resolve in Linear. The Linear project readback confirms protocol-v0.4, its exact hash, and separate design/readiness gates. ADV-35 closes design correction and synchronization; ADV-36 remains open for actual readiness/freeze evidence.

Claude Project Settings were read after saving: current context matched the intended revision pointers and the original historical context remained verbatim. Fable's completed UI response confirms scientific notes point to v0.4 and both v2 companions. Future updates should prefer versioned artifacts and use new project conversations when useful; Project Context changes are reserved for durable policy, scope or canonical-pointer changes, per Chris's clarification.

Independent statistical review checked the estimand and binomial interval proof. Independent operational review found N1–N7 resolved without regression; its two editorial findings (title and duplicated section number) were corrected. Claude Science independently confirmed N1–N7 resolved in the final hash above. Codex reconciles R1–R10 closure at the design-text level; no reviewer agreement is represented as empirical evidence.

Documentation checks: unique numbered top-level protocol sections; parseable normative JSON schema with 10 proposals × 20 numbers; authored relative Markdown links resolve; no private host paths or obvious credential literals in the documentation set; staged `git diff --check` passes. No simulator/controller code, package installation, study-objective evaluation, experimental model call, freeze or experimental result was produced. Algebraic and binomial arithmetic were document checks.

Git commit identity is the commit containing this receipt, recorded in the PR and Linear after push. File hashes avoid a self-referential commit/hash declaration.
