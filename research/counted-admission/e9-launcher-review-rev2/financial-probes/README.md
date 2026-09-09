# Independent financial probes

From the repository root, use an existing review runtime with the pinned SDK dependencies:

```sh
/path/to/review/python research/counted-admission/e9-launcher-review-rev2/financial-probes/run_probes.py \
  --python /path/to/review/python
```

The runner stages the preserved revision-2 submission and two copies of the original
provider in a temporary directory. It applies the submitted patches `0001` and `0002`
only to one provider copy. Fresh child processes receive no credential environment,
disable bytecode writes, and block Python socket connection, DNS and UDP send operations.
Every provider response is fabricated through `httpx.MockTransport`; no live call occurs.

- `arithmetic_probe.py` checks 48 category allocations against exact conservative
  reservations, using short-context rates, long-context rates, and a synthetic rate
  ordering. These arithmetic inputs do not establish actual billing terms.
- `retry_headroom_probe.py` compares the original provider with both patches applied.
  It calls the orchestrator directly with a fabricated $2.60368 ceiling: the original
  provider dispatches two generations and records $2.775680, while the patched provider
  dispatches one and stops at $1.523840. **The CLI gate rejects this deliberately small
  full-allowance authority before dispatch.** This component counterexample qualifies
  the claim that per-attempt protection is independent of patch `0002`; it does not
  demonstrate an overspend through the full CLI gate or the patched candidate.

`evidence/` retains exact stdout/stderr, structured results, runtime/package versions,
patch outcomes and SHA-256 hashes of the probes and reviewed inputs. Successful probe
execution confirms these observations; it does not grant experimental spending authority.
The preserved submission and original provider are checked for unchanged hashes.

For a $32 **all-in incremental allocation**, net API allowance `A` must satisfy
`A + mandatory_extras(A) <= 32` and `18.286080 + 12*f <= A`, where `f` is an evidenced
count-attempt fee bound covering every permitted outcome. If fixed extras `E` and a tax
rate `t` on API charges alone are established, `A <= (32-E)/(1+t)`; account evidence must
determine the tax base. The count headroom `10714/9375 = $1.142826666...` applies only
when taxes and mandatory extras are zero. No probe establishes a count fee or tax term.
