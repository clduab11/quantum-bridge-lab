# E9 launcher — execution instructions, revision 2

Nothing in this file dispatches a live request. The default mode is offline, and there is no implicit default subcommand.

## 0. Environment

Actual versions these results were produced with, on macOS 26.5.2 (arm64), 2026-09-09:

```
python 3.11.16
openai 3.9.0          httpx 0.28.1         pydantic 2.12.0
numpy 2.4.6           scipy 1.17.1         cma 4.4.4
pytest 9.1.1          ruff 0.16.6          pip-audit 2.10.1
```

This is a record, not a claim of matching any other environment. `openai==3.9.0` and `httpx==0.28.1` are pinned by `counted_responses_provider.authority` and checked by `provider._versions_ok`; any other pair refuses to dispatch. `pip-audit` is required by `qbridge.preflight` — without it, two core `test_preflight.py` tests fail with `PackageNotFoundError`.

```bash
conda create -n qbridge-e9 python=3.11 numpy'>=2.3,<3' scipy'>=1.16,<2' pytest'>=9.0.3,<10' ruff'>=0.12,<1'
conda activate qbridge-e9
pip install openai==3.9.0 httpx==0.28.1 pydantic==2.12.0 'cma>=4.4,<5' pip-audit==2.10.1
```

## 1. Lay out the tree

The work directory **must be outside every Git worktree** — the launcher refuses otherwise, in every mode, before creating anything.

```bash
git clone https://github.com/clduab11/quantum-bridge-lab.git repo
git -C repo checkout a8c3e1e83c28db80642ab0123dd1fbf4d9ff5bc2
tar -xzf qbridge_e9_launcher_rev2_a8c3e1e8.tar.gz      # creates ./e9rev2
export REPO=$PWD/repo
export PYTHONPATH="$REPO/src:$REPO/research/counted-admission/provider-candidate:$PWD/e9rev2"
export WORK="$HOME/.qbridge-e9"                        # outside any repository
cd e9rev2
```

## 2. Verify the committed fixtures — no journal, no provider, no network

`--repo-root` is required: there is no path that skips source verification.

```bash
python -m qbridge_e9.cli verify-fixtures \
  --fixtures "$REPO/research/counted-admission/e9-inputs" --repo-root "$REPO"
```

Expect `checks_passed: 88`, `checks_failed: 0`, `manifest_matches_reviewed_pin: true`. Exit 0. A mutated fixture — even one whose manifest is updated to match — exits 1 naming the pin that failed.

## 3. Evaluate the live gate without running anything

```bash
python -m qbridge_e9.cli gate \
  --fixtures "$REPO/research/counted-admission/e9-inputs" --repo-root "$REPO" \
  --work-dir "$WORK/gate"
```

Exit 2 with `may_dispatch_live: false` and the failing keys listed. Credential presence is **not** checked unless you add `--check-credential`; no offline path reads the variable, and its value is never printed or written.

## 4. Full offline dry run

```bash
python -m qbridge_e9.cli dry-run \
  --fixtures "$REPO/research/counted-admission/e9-inputs" --repo-root "$REPO" \
  --work-dir "$WORK/dry-$(date -u +%Y%m%dT%H%M%SZ)"
```

Expect `fixture_checks_passed: 96`, `gate_may_dispatch_live: false`, `attempts: {count: 4, generation: 4}`, `e9_accepted: true`, exit 0. Every response is fabricated and self-labelled; the transport is `httpx.MockTransport`.

Re-running in the **same** work directory reconstructs the finished fixtures from the journal, dispatches nothing, still reports `e9_accepted: true`, and writes a new timestamped report without touching the first. Reports are `e9_report_<UTC>.json` plus an append-only `e9_reports.jsonl`.

## 5. Tests

```bash
python -m pytest e9tests -q                 # 144 passed, 6 skipped (unpatched dependency)
python -m ruff check --select E4,E7,E9,F --line-length 100 qbridge_e9 e9tests
```

Against the dependency with both patches applied: 145 passed, 5 skipped. The skips are mutually exclusive skip-guarded pairs — exactly one member of each runs.

## 6. Reproduce the review findings

```bash
python deliverables/codex_findings_probe.py "$PWD" "$REPO"        # this revision
python deliverables/codex_findings_probe.py /path/to/e9 "$REPO"   # revision 1, for comparison
```

Compare against `codex_findings_after_rev2.json` and `codex_findings_before_rev1.json`. Wall-clock timings vary by tens of milliseconds between runs; the classifications do not.

## 7. Apply the dependency patches — optional, and not applied by default

```bash
git -C "$REPO" apply e9rev2/patches/0001-spend-limit-not-retryable.diff
git -C "$REPO" apply e9rev2/patches/0002-conservative-generation-reservation.diff
```

They stack in this order. The launcher behaves identically with or without them.

## 8. Live run — blocked, listed for completeness

Do not run this until Codex's review is closed, amendment A1 is adopted, the count-request charging question is resolved, the account facts are recorded, and a numeric E9-only authority is signed. **Neither USD 25 nor USD 32 is approved.**

```bash
export OPENAI_API_KEY=...    # presence only is recorded; the value is never read into any artifact
python -m qbridge_e9.cli live \
  --fixtures "$REPO/research/counted-admission/e9-inputs" --repo-root "$REPO" \
  --work-dir "$WORK/live-$(date -u +%Y%m%dT%H%M%SZ)" \
  --authority authority.json --adoption-evidence adoption.json \
  --billing-evidence billing.json --authorization authorization.json \
  --specification "$REPO/specification/<adopted protocol>.md" \
  --confirm-live
```

Five independent refusals stand in the way, and every one must be cleared deliberately:

1. `--confirm-live` is required; without it the command exits 2 before touching anything.
2. The work directory must be outside every Git worktree.
3. `--authority` is required in live mode; a synthetic authority is refused at the transport boundary and cannot reach a real transport.
4. `OPENAI_API_KEY` must be present.
5. All **20** gate requirements must pass — including `authority.conservative_ceiling` (the ceiling must fund every allowed attempt at the worst applicable input category) and `authorization.bound_and_timed` (a parsed, unexpired UTC approval carrying the digest of the authority it authorizes).

`e9_unapproved_authority_template_rev2.json` is the shape to fill in. **It is inert by construction** — `synthetic: true`, `approved: false`, `count_fee_verified: false`, a zero-placeholder authority binding, a `usd_ceiling` of `"0"` — and cannot be constructed into an `AuthorityRecord` at all. A test asserts that.
