# Durable request-record implementation plan

Goal: retain the exact outgoing request bytes durably before a future provider dispatch, and retain received bytes before parsing. This is an offline storage component, not a transport or study launcher.

Create src/qbridge/request_records.py and tests/test_request_records.py. Keep the preserved Claude candidate source unchanged. The store opens an existing owner-only 0700 directory outside the public repository, pins its file descriptor, accepts only flat safe filenames and byte payloads, exclusively creates 0600 files, completes short writes, fsyncs the file and directory, and returns a digest only after success. Existing or partial files are preserved and never overwritten. A failed write/sync raises so the caller must not dispatch. Permissions protect against other accounts; shared-account access is not independent blinding and this is not a hardware durability guarantee.

First add tests for exact retention/digest/mode, invalid directory and filenames, exclusive duplicate writes, short writes, sync failure preserving the file, permission change, closed-store writes, and a child process killed after successful retention. Run red, implement the component, then targeted tests/Ruff. Inspect the diff and commit with evidence. Use only fabricated byte payloads in temporary directories; never create a real mapping or make network/objective calls.

A future adapter must call this component from its pre-send verification hook before HTTP dispatch. Integration is a separate reviewed task; adding the component does not establish that integration.
