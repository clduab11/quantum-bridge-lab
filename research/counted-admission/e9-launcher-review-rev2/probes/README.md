# Independent revision 2 counterexamples

These programs record independent observations against the preserved revision
2 submission. Successful probe execution is **not** a passing safety test or
permission to dispatch experimental requests.

From the repository root, supply an existing review Python runtime:

```sh
/path/to/review/python research/counted-admission/e9-launcher-review-rev2/probes/run_probes.py \
  --python /path/to/review/python
```

The runner copies `../submission` into a temporary `e9rev2` directory and
places a neighboring `repo` link to the reviewed checkout. It verifies copied
hashes and checks that the preserved submission remains unchanged. Each probe
runs in a fresh process with bytecode writes disabled, no real credentials in
the environment, and socket connection/DNS operations blocked.

- `gate_probe.py` observes the corrected Git containment, fixed manifest,
  timestamp, and offline CLI behaviors, then records the two remaining
  counterexamples: a successful gate report for nonexistent inputs and
  dispatches after approval expiry. The expiry case explicitly replaces the
  live transport factory with a fabricated `httpx.BaseTransport` handler;
  no real HTTP transport or external request is created. Test authority and
  billing records are fabricated and confer no actual permission.
- `deadline_probe.py` uses `httpx.MockTransport` to observe a delayed response
  body exceeding the guard and resumption from an intact journal prefix after
  the original deadline. Its shortened two-second guard is a test condition,
  not a change to the committed experimental limit.

The gate probe runs `git init` only in a new temporary directory. The project
history and checkout remain untouched. Temporary records and modified fixture
copies are removed when the runner finishes. `evidence/` retains structured
JSON, exact stdout/stderr, source hashes, and actual runtime/package versions.

Adapted from `/tmp/qbridge-e9-rev2-gate-probe.py` and
`/tmp/qbridge_e9_rev2_deadline_probe.py`. Machine-specific repository paths
were replaced by the staged test support path; outputs are structured JSON.
