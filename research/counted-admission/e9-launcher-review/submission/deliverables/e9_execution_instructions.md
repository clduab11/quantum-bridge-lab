# E9 launcher — execution instructions

Nothing in this file dispatches a live request. The default mode is offline.

## 0. Environment

Recorded actual versions (macOS-26.5.2-arm64, 2026-09-09):

```
python 3.11.16
openai==3.9.0        httpx==0.28.1        pydantic==2.12.0
numpy==2.4.6         scipy==1.17.1        cma==4.4.4
pytest==9.1.1        ruff==0.16.6         pip-audit==2.10.1
```

`openai==3.9.0` and `httpx==0.28.1` are pinned by `counted_responses_provider.authority` and checked by `provider._versions_ok`; any other pair refuses to dispatch. `pip-audit` is required by `qbridge.preflight` — without it two core tests fail with `PackageNotFoundError`.

```bash
conda create -n qbridge-e9 python=3.11 numpy'>=2.3,<3' scipy'>=1.16,<2' pytest'>=9.0.3,<10' ruff'>=0.12,<1'
conda activate qbridge-e9
pip install openai==3.9.0 httpx==0.28.1 pydantic==2.12.0 'cma>=4.4,<5' pip-audit==2.10.1
```

## 1. Lay out the tree

```bash
git clone https://github.com/clduab11/quantum-bridge-lab.git repo
git -C repo checkout a8c3e1e83c28db80642ab0123dd1fbf4d9ff5bc2
tar -xzf qbridge_e9_launcher.tar.gz          # creates ./e9
export REPO=$PWD/repo
export PYTHONPATH="$REPO/src:$REPO/research/counted-admission/provider-candidate:$PWD/e9"
cd e9
```

## 2. Verify the committed fixtures (no journal, no provider, no network)

```bash
python -m qbridge_e9.cli verify-fixtures \
  --fixtures "$REPO/research/counted-admission/e9-inputs" --repo-root "$REPO"
```

Expected: `"checks_passed": 68, "checks_failed": 0`. Exit 0. (76 with a provider attached, as in the dry run — the extra 8 are the `provider.prepare` byte reproductions.)

## 3. Offline dry run — the default mode

```bash
python -m qbridge_e9.cli dry-run \
  --fixtures "$REPO/research/counted-admission/e9-inputs" --repo-root "$REPO" \
  --work-dir "$HOME/.qbridge-e9/dryrun-$(date -u +%Y%m%dT%H%M%SZ)"
```

Uses `httpx.MockTransport` with fabricated responses, a fabricated key that is never a credential, and a synthetic authority. No environment variable is read. Expected: `fabricated_responses: true`, `gate_may_dispatch_live: false`, `attempts {count: 4, generation: 4}`, `e9_accepted: true`. Exit 0.

Choose a `--work-dir` **outside any Git worktree**; the gate checks this and the directory is created mode `0700`.

Re-running against the same `--work-dir` is safe and dispatches nothing new — finished fixtures are skipped from the journal.

## 4. Evaluate the live gate without running anything

```bash
python -m qbridge_e9.cli gate \
  --fixtures "$REPO/research/counted-admission/e9-inputs" \
  --work-dir "$HOME/.qbridge-e9/gate" \
  --authority          authority.json \
  --adoption-evidence  adoption.json \
  --billing-evidence   billing.json \
  --authorization      authorization.json \
  --specification      "$REPO/specification/ai_quantum_control_protocol_v0.4.md"
```

Prints all 18 requirements with pass/fail and a reason. Exit 0 only if every one passes; exit 2 otherwise. With no evidence supplied, 17 of 18 fail.

## 5. Tests

```bash
python -m pytest e9tests -q                                    # 93: 88 passed, 5 skipped
python -m ruff check --select E4,E7,E9,F --line-length 100 qbridge_e9 e9tests
```

Dependency baselines:

```bash
python -m pytest "$REPO/tests" -q                                                   # 289
python -m pytest "$REPO/research/counted-admission/provider-candidate/tests" -q     # 113
python -m pytest "$REPO/research/counted-admission/provider-candidate/reference_preserved/test_counted_responses_reference.py" -q   # 152
cd "$REPO/research/execution-preparation/claude-science" && python -m pytest qbridge_ext/tests/test_ext.py -q   # 53
```

## 6. The optional minimal patch

```bash
git -C "$REPO" apply --check patches/0001-spend-limit-not-retryable.diff   # verify only
git -C "$REPO" apply         patches/0001-spend-limit-not-retryable.diff   # apply
```

With the patch applied the launcher suite reports 89 passed / 4 skipped (same 93 tests; the two documentation tests are mutually exclusive), and the provider (113) and reference (152) suites are unchanged. The patch is **not** applied in the delivered tree.

## 7. Live run — blocked, listed for completeness

Do not run this until Codex's review is complete, the count fee is resolved, the account facts are recorded, a numeric authority is signed and a project-level spend limit is configured.

```bash
export OPENAI_API_KEY=...            # presence only is recorded; the value is never read into any artifact
python -m qbridge_e9.cli live \
  --fixtures "$REPO/research/counted-admission/e9-inputs" --repo-root "$REPO" \
  --work-dir "$HOME/.qbridge-e9/live-$(date -u +%Y%m%dT%H%M%SZ)" \
  --authority authority.json --adoption-evidence adoption.json \
  --billing-evidence billing.json --authorization authorization.json \
  --specification "$REPO/specification/ai_quantum_control_protocol_v0.5.md" \
  --confirm-live
```

Four independent refusals stand in the way, and all four must be cleared deliberately:

1. `--confirm-live` is required; without it the command exits 2 before touching anything.
2. `--authority` is required in live mode; a synthetic authority is refused at the transport boundary and cannot reach a real transport.
3. `OPENAI_API_KEY` must be present.
4. Every one of the 18 gate requirements must pass.

`e9_unapproved_authority_template.json` is supplied as the shape to fill in. **It is inert by construction** — `synthetic: true`, `approved: false`, `count_fee_verified: false`, zero placeholder hashes — and cannot be constructed into an `AuthorityRecord` at all.
