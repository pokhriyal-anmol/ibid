# concordance infers direction from the Citation prefix

Status: done
Blocked by: none

What to build: make `direction` optional on the `concordance` tool. Drop it from `required` in the tool schema in `src/ibid/mcp.py`. When absent, infer it from the Citation prefix: `IPC` gives `ipc_to_bns`, `BNS` gives `bns_to_ipc`. When present and contradicting the prefix (e.g. `BNS 318` with `ipc_to_bns`), return a tool error naming both the prefix and the given direction. Never silently correct it. An invalid direction value keeps the existing -32602 error.

User stories: 4, 5, 8 (direction half), 9.

Acceptance criteria (through the stdio harness):
- `concordance` with only `citation: 'BNS 318'` returns the same payload as with `direction: 'bns_to_ipc'`; same for an IPC Citation and `ipc_to_bns`.
- `concordance BNS 318` with `direction: 'ipc_to_bns'` returns a tool error whose message names the conflict.
- `tools/list` shows `concordance` with `required: ['citation']` and `direction` still an enum of the two values.
- Known-bad run: a server that silently corrects a contradicting direction makes the conflict test fail; observe it once.
- All slice 4 tests pass unchanged.
