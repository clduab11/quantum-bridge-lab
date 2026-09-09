# Independent supplied-suite reproduction

The recorded commands ran on macOS with the runtime versions listed in the
[review](../README.md). Use an existing compatible review environment; the
repository lockfile was not changed. These are offline mock suites, not a
network sandbox. No real API key is required or supplied.

From the repository root, stage outside Git because the launcher correctly
refuses evidence storage in a worktree:

```sh
QBRIDGE_REPO="$PWD"
QBRIDGE_REVIEW=$(mktemp -d "${TMPDIR:-/tmp}/qbridge-e9rev2-review-XXXXXXXX")
QBRIDGE_PYTHON=/absolute/path/to/review/python
ln -s "$QBRIDGE_REPO" "$QBRIDGE_REVIEW/repo"
cp -R research/counted-admission/e9-launcher-review-rev2/submission "$QBRIDGE_REVIEW/e9rev2"
cd "$QBRIDGE_REVIEW/e9rev2"
env -u OPENAI_API_KEY PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 \
  PYTHONPATH=../repo/src:../repo/research/counted-admission/provider-candidate:. \
  "$QBRIDGE_PYTHON" -m pytest -q -rs -p no:cacheprovider e9tests
```

The retained result is 144 passed / 6 skipped. For the temporary patched
variant, continue in the same shell and directory:

```sh
mkdir -p "$QBRIDGE_REVIEW/patched/research/counted-admission"
cp -R "$QBRIDGE_REPO/research/counted-admission/provider-candidate" \
  "$QBRIDGE_REVIEW/patched/research/counted-admission/provider-candidate"
patch -d "$QBRIDGE_REVIEW/patched" -p1 < patches/0001-spend-limit-not-retryable.diff
patch -d "$QBRIDGE_REVIEW/patched" -p1 < patches/0002-conservative-generation-reservation.diff
env -u OPENAI_API_KEY PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 \
  PYTHONPATH=../repo/src:../patched/research/counted-admission/provider-candidate:. \
  "$QBRIDGE_PYTHON" -m pytest -q -rs -p no:cacheprovider \
  e9tests ../patched/research/counted-admission/provider-candidate/tests
```

The retained result is 258 passed / 5 skipped, including 113 provider tests.
Author CLI subprocess tests set their own import paths to the neighboring
unchanged `repo`, as disclosed in the review. The source provider and preserved
submission are not patched in place.

The independent [deadline/gate probes](../probes/README.md) and
[financial probes](../financial-probes/README.md) have separate runners with
network guards and exact structured results. Successful counterexample
execution means the defect was observed, not that a protection passed.
