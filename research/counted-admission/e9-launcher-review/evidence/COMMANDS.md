# Reproduce the supplied test suites

Run from the repository root with an existing Python review environment. The recorded environment is in `environment.json`; the provider requires OpenAI SDK 3.9.0 and HTTPX 0.28.1. These commands do not install dependencies or change repository source. They stage the author's expected sibling `e9`/`repo` layout outside Git.

```sh
qbridge_repo="$(pwd)"
qbridge_python=/path/to/review/python
qbridge_review="$qbridge_repo/research/counted-admission/e9-launcher-review"
qbridge_stage="$(mktemp -d)"
cp -R "$qbridge_review/submission" "$qbridge_stage/e9"
ln -s "$qbridge_repo" "$qbridge_stage/repo"
cd "$qbridge_stage/e9"

env -u OPENAI_API_KEY PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 \
  PYTHONPATH=../repo/src:../repo/research/counted-admission/provider-candidate:. \
  "$qbridge_python" -m pytest -q -rs -p no:cacheprovider e9tests
```

Recorded result: 88 passed, 5 skipped. Tests use fabricated authorities and mock responses; unlike the separate probe runner, this command does not itself install a network guard.

For the separate patch variant, copy the provider, check/apply the supplied patch in that temporary tree, and run the launcher and provider suites:

```sh
mkdir -p "$qbridge_stage/patched/research/counted-admission"
cp -R "$qbridge_repo/research/counted-admission/provider-candidate" \
  "$qbridge_stage/patched/research/counted-admission/provider-candidate"
git -C "$qbridge_stage/patched" apply --check \
  "$qbridge_stage/e9/patches/0001-spend-limit-not-retryable.diff"
git -C "$qbridge_stage/patched" apply \
  "$qbridge_stage/e9/patches/0001-spend-limit-not-retryable.diff"
qbridge_patched="$qbridge_stage/patched/research/counted-admission/provider-candidate"

env -u OPENAI_API_KEY PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 \
  PYTHONPATH="$qbridge_repo/src:$qbridge_patched:$qbridge_stage/e9" \
  "$qbridge_python" -m pytest -q -rs -p no:cacheprovider \
  "$qbridge_stage/e9/e9tests" "$qbridge_patched/tests"
```

Recorded result: 202 passed, 4 skipped. The author's child CLI tests construct their own path to the unchanged sibling repository, so they do not all exercise the patched provider. This limitation is retained in the review.

The [independent probes](../probes/README.md) have a portable runner with socket and DNS access disabled. They reproduce the missed defects; their success does not mean the implementation is safe to launch.
