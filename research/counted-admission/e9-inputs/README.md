# Fixed synthetic Responses preflight inputs

These are the prospective four E9 requests selected before any provider observation. The histories contain fabricated numbers. No qubit objective, optimizer, provider token counter or generation endpoint was invoked to create them. They do not adopt amendment A1, authorize spending or freeze a study.

Each fixture has a canonical count body and generation body, with byte lengths, SHA-256 hashes and source hashes in [manifest.json](manifest.json). The eventual adapter must retain the actual serialized outgoing bytes separately and verify their JSON identity against these bound bodies before dispatch.

| Order | Fixture | Purpose |
| --- | --- | --- |
| 1 | F1_short | Batch 1 with ten fabricated rows |
| 2 | F2_maximal_renderer | Batch 19 with 190 fabricated rows using long legal floating-point representations |
| 3 | F3_repeat_of_F2 | Byte-identical repeat of F2 for both request classes |
| 4 | F4_correction_no_valid_vectors | F2 with the fixed correction suffix and reason `no_valid_vectors` |

The long fixture exercises the renderer's maximum row count. Byte length is not a token count, and these fixtures do not establish a universal context-fit bound. Their model, reasoning effort, admission ceiling and output cap are fixed prospectively; no E9 observation may select those values. F2/F3 elapsed time must be measured during an authorized E9 before making any claim about cache-lifetime coverage.

The builder uses the preserved earlier fixture code and reviewed counted reference. It checks literal developer/user strings, count/generation projection, and exact F2/F3 repetition. All eight payload hashes were independently read back; rebuilding after a formatting-only builder change produced identical payload bytes. The manifest records the final builder hash.

Rebuild into a new directory from the repository root, with the repository's Python dependencies available:

```sh
PYTHONPATH=src python research/counted-admission/build_e9_inputs.py /tmp/qbridge-e9-inputs-new
```

Live execution still needs a reviewed bounded entry point, adopted request contract, API access, verified billing evidence and a numeric E9 spending authority. The proposed allowance is at most 12 count and 12 generation attempts under one 7,400-second monotonic stopping limit. Server waits and overhead consume that time; the allowance is not a promise that every attempt will fit.
