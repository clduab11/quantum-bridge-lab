# Provider planning verification — 2026-09-08

**233 integrated tests passed, with one warning, in 63.71 seconds.** This includes 59 new budget-planning tests. Ruff 0.16.6 lint and formatting checks passed for all 20 Python files; `uv lock --check --offline` passed. These results cover offline engineering only. No study objective, experimental generation or token-counting API was called, and no provider dependency was installed.

Tested source is present at commit `65769c8f5c61c215330ec660960fc261118b8f2f`. [verification.json](verification.json) records hashes of the source, fixtures, prompts, protocol and lockfile. Later documentation and review receipts do not imply another execution of this suite.

Commands, using the existing locked temporary runtime described in the earlier verification:

```sh
PYTHONPATH=src PYTHONPYCACHEPREFIX=/tmp/qbridge-provider-pycache PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 /tmp/quantum-bridge-preflight-runtime/bin/python -m pytest -q --disable-warnings
/tmp/quantum-bridge-preflight-runtime/bin/ruff check --no-cache src tests analysis
/tmp/quantum-bridge-preflight-runtime/bin/ruff format --check src tests analysis
uv lock --check --offline
```

The implementation's test-first evidence is recorded in the [budget plan](../../docs/plans/2026-09-08-budget-planning.md). An independent reviewer additionally checked 162 boundary scenarios using exact rational arithmetic, including very small/large rates, both stages, E9 attempts and fractional-cent reserves. No discrepancy was found. Reviewed `budget.py` SHA-256: `99178132a920f46f77044fdf76fed964e30adcc48b720b04de459fb7fbd3e8b0`; the integrated file matches. A fresh CLI invocation also reproduced the documented 50,000-token hypothetical Sol scenario: $276.52 scheduled and $1,659.12 retry/correction ceilings after upward cent rounding, excluding E9 and other charges in that explicitly zero-reserve example. That input ceiling is not verified.

The new calculator requires all assumptions, rejects unknown/malformed values, isolates Decimal precision from the caller, writes JSON only to stdout and always marks token-cap verification, billing completeness and spending authorization false. It imports no provider or study-objective code. Its ceilings are arithmetic conditional on the supplied caps/rates covering every charge; it is not an account spending guard. Missing charges cannot be resolved merely by entering zero.

## Preserved history and remaining limits

The original [174-test/E1–E8 report](../preflight/VERIFICATION.md) and its source manifest remain unchanged and refer to their original implementation commit. Compared with that milestone, the current source set adds the budget module/test; `pyproject.toml` changes only the description from “preregistered” to “planned,” accurately reflecting the unfrozen protocol. Dependencies and protocol v0.4 are unchanged. The old source manifest is not represented as a manifest of this expanded source tree.

The new source manifest is verification evidence, **not a full frozen run manifest**. Actual model/decoding/identity, provider transport, tokenizer ceilings, billing/authorization, storage/custody, complete exposure accounting and final execution decisions remain unresolved. The prompt-text byte bound does not establish a token ceiling. Provider research is based on dated retrieval of mutable primary documentation; no API behavior or account-specific bill has been measured. Existing local process cancellation limitations still apply.

Repository publication is separate from scientific readiness. PRs #1 and #2 were merged using expected head SHAs and ordinary merge commits; GitHub accepted them without a protection override. The existing optional Kilo review was still running at PR #2 publication, while CodeRabbit reported success and the independent local publication review was complete. No Kilo approval is claimed.

Subsequent GitHub readback showed the Kilo check completed successfully at 2026-09-08T20:57:10Z; no inline PR #2 review comments were returned. This is an automated check result, not an independent human approval.

An invalid extra local Git ref with a space in its name blocked fetch. Its exact 41-byte contents were preserved outside Git refs before recovery; subsequent fetch and connectivity checks passed (only three dangling blobs were reported). No valid ref, commit or working file was deleted. This local recovery did not change research source bytes.
