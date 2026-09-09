# Independent E9 counterexamples

These four programs preserve the independent review's counterexamples. Their
successful execution is **not** a passing safety test or approval to run E9.
They use fabricated responses and authority records against the original
submission and the repository's existing provider, without applying the
submission's optional provider patch.

From the repository root, supply an existing review Python runtime:

```sh
/path/to/review/python research/counted-admission/e9-launcher-review/probes/run_probes.py \
  --python /path/to/review/python
```

The runner copies `../submission` into a fresh temporary `e9` directory and
links its neighboring `repo` directory to the checked-out repository. Each
probe runs in a new process with bytecode writes disabled and no real API key
in its environment. Socket connections and DNS resolution raise immediately.
Only the CLI environment-read probe supplies a fabricated key string to its
own in-memory environment spy. Model interactions use `httpx.MockTransport`.

The gate probe initializes a new temporary Git repository to exercise the
records-location check; it does not change this repository or its history.
All private mock journals, mutated fixture copies and raw responses stay in
temporary storage and are removed after the run. Original submission hashes
are checked before staging and after all probes.

`evidence/` contains per-probe JSON observations, exact stdout/stderr, the
actual interpreter/package versions, and source hashes. Empty stderr logs
mean the probe executed without a Python error; the JSON still records the
unsafe or incorrect behavior under review.

The adapted probes originate from these review scripts:

- `/tmp/qbridge-e9-gate-probes.py`: Git-contained records, mutable fixture
  manifest, invalid approval timestamp and missing source hash set.
- `/tmp/qbridge-e9-cli-probes.py`: default-command exception and a dry-run
  read of the fabricated API-key environment value.
- `/tmp/qbridge_e9_orchestrator_probe.py`: blocking generation over a
  shortened deadline and a renewed deadline on the same journal.
- `/tmp/qbridge_e9_reopen_probe.py`: billing-stop persistence and acceptance
  preservation when a journal is reopened.

The portable versions remove machine-specific repository paths and emit
structured JSON. The deadline probe deliberately uses a two-second test
limit; it does not change the committed experimental limit or fixtures.
