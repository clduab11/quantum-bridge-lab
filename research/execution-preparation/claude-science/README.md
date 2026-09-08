# Preserved Claude Science candidate and reproducible review

The authored documents, qbridge_ext sources, protocol copy, fixtures, archives and records are original bytes from **Sol Chat Request Contract & Budget Proposal** in the Claude Science project. Codex added this README, the isolated pyproject/uv.lock and the two import/snapshot verification files. The source is a candidate under review, outside the main installed package; importing it does not send a request. Live use still requires the unresolved provider and financial gates.

Reproduce the combined analytic/mocked test run from the repository root with Python 3.11.15 and uv available:

```sh
uv sync --frozen --project research/execution-preparation/claude-science --python 3.11.15
PYTHONPATH=src:research/execution-preparation/claude-science \
  research/execution-preparation/claude-science/.venv/bin/python -m pytest \
  tests research/execution-preparation/claude-science/qbridge_ext/tests -q
```

Expected for the preserved source: 286 passed (233 core + 53 candidate), with one harmless pycma warning about optional plotting. No provider key is required. The mocked credentials in tests are fabricated. This is not a command to launch E9 or a study.

The dependency audit and actual test logs are in [../verification](../verification/). Source imports were checked against the corrected Claude manifest and code archive. Third-party documentation pages remain in the Claude project; the Git copy retains their links and hashes rather than duplicating the full pages. Bundle hashes appearing in earlier exposure-log entries describe those earlier packaging events; the corrected manifest and import verification identify the copied final artifacts.

Read [../STATUS.md](../STATUS.md) for the current reconciliation and retained qualifications before interpreting the original gate record or budget scenarios.
