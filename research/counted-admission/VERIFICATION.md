# Integrated offline verification

The [machine-readable result](integrated-verification.json) and [complete test log](integrated-tests.log) identify the tested source hashes, dependency environment and combined result. This verifies engineering behavior using analytic identities, fabricated data and mock provider responses. It is not evidence of optimization advantage.

## Reproduce from the repository root

Use a single-threaded POSIX environment with Python 3.11. The preserved SDK review lockfile supplies the combined dependencies; it is separate from the root environment. Dependency installation may access the network.

```sh
uv sync --frozen --project research/execution-preparation/claude-science
PYTHONPATH=src:research/execution-preparation/claude-science:research/counted-admission/claude-science:research/counted-admission/provider-candidate:research/counted-admission/provider-candidate/tests \
  PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 \
  research/execution-preparation/claude-science/.venv/bin/python -m pytest -q -p no:cacheprovider \
  tests research/execution-preparation/claude-science/qbridge_ext/tests \
  research/counted-admission/claude-science/test_counted_responses_reference.py \
  research/counted-admission/provider-candidate/tests
```

The root README's shorter command runs the core suite only. The combined command adds 53 preserved Chat-candidate cases, 152 preserved counted-reference cases and 113 single-attempt Responses-provider cases. It does not collect the provider package's duplicate copy of the original reference tests.

## Evidence boundaries

- No API key is required. All dispatched provider-test requests use `httpx.MockTransport`. Negative tests construct but never invoke a non-mock transport. The tests do not themselves provide a network sandbox.
- The author package is preserved byte for byte, including its original 112-pass/1-failure log against the older core. The local core correction resolves that strict worker-exit failure; final results are recorded separately, without rewriting historical evidence.
- A separate compatibility probe redirects the original reference tests to the operational contract: 150 pass and two old tuple-tag assertions fail because the corrected representation uses JSON-stable lists. Replacement behavior has explicit operational tests. These two assertions are not claimed to pass or included again in the combined total.
- Root changes cover precedence of durable validity halts, abrupt worker exits, cancellation of non-detached descendants and rejection of non-finite worker timeouts. See the [review follow-up](REVIEW_FOLLOWUP.md).
- The [fixed E9 inputs](e9-inputs/README.md) are prospective fabricated request bodies, not live token counts or evidence that every permitted history fits.
- Authority validation checks recorded fields and limits; it cannot independently certify external billing evidence. E9 acceptance, adoption, spending authority, a complete study launcher and the final manifest remain separate requirements.

The final record reports zero experimental count/generation requests and zero study-objective candidate evaluations. Protocol v0.4 remains unchanged and unfrozen. The historical [485-test milestone](combined-verification.json) and [488-test review follow-up](post-review-verification.json) retain their original scope.
