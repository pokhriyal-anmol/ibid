# Slice 5: close the three gaps a real MCP client hit

## Summary

A real client session on the slice 4 `ibid mcp` server exposed three gaps. This slice closes them in `src/ibid/mcp.py` and the code it calls, with no change to ranking, the frozen rule, any Gold set or any pinned Concordance file, so ADR 0001 (no model in retrieval) and ADR 0004 (fixed tokenisation) are untouched.

- `concordance` falls back from a sub-provision Citation such as `BNS 318(4)` to its section (`BNS 318`) when the sub-provision has no verified entry. The result carries a `via` field naming the section Citation. A section Citation never falls back and never carries `via`. If the section also has no verified entry, the result is `no verified concordance`, not an error. The spec does not name the field, so `via` is a default taken by the ticket.
- `direction` is now optional on `concordance` and is inferred from the Citation prefix (`IPC` gives `ipc_to_bns`, `BNS` gives `bns_to_ipc`). A direction that contradicts the prefix is a tool error naming both, never silently corrected. An invalid direction value keeps the existing -32602 error.
- `search` has an optional boolean `adjacent` (default false). When true, each hit lists the Citation and heading line of the previous and next section of the same Act in document order, with null at the first and last section. The hit list and order are identical with or without the flag, so IPC 405 becomes visible next to IPC 406 for "criminal breach of trust".

Testing the adjacent flag exposed a real bug in `neighbours()` in `src/ibid/index.py`: nested sub-provisions (for example IPC 376(2)(a)) got their own section as `previous`. It now walks parents up to the section.

## Test plan

- [x] `uv run python -m unittest discover -s tests`: Ran 226 tests in 33.097s, OK.
- [x] Concordance fallback, direction inference and conflict error, and `adjacent` order and neighbours are covered through the stdio harness in `tests/test_mcp.py`, with expected values taken from the existing `index` and `concordance` functions.
- [x] Added `test_adjacent_sub_provision_gets_its_sections_neighbours`, which compares `previous` and `next` for sub-provision hits against the section order. Run against the old `index.py` it failed ('IPC 376' != 'IPC 375') and it passes with the fix.
- [x] Slice 4 tests in `tests/test_mcp.py` pass unchanged.
