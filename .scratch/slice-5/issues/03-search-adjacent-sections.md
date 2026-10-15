# search gains an optional adjacent flag listing previous and next sections

Status: done
Blocked by: none

What to build: add an optional boolean `adjacent` (default false) to the `search` tool schema in `src/ibid/mcp.py`. When true, each hit gains `previous` and `next`: the Citation and heading line of the neighbouring section of the same Act in document order, read from the existing index (`src/ibid/index.py`). The first section of an Act has `previous: null`, the last has `next: null`. Ranking and the hit list are untouched: `index.search` is called exactly as before and the adjacency is attached afterwards. When false or absent, output is byte-identical to slice 4. No change to the frozen rule, tokenisation (ADR 0004) or any model (ADR 0001).

User stories: 6, 7, 8 (adjacent half), 9.

Acceptance criteria (through the stdio harness):
- For a fixed query, hits with `adjacent: true` have the same Citations in the same order as `index.search` on the same index and as the call without the flag.
- `search 'criminal breach of trust'` with `adjacent: true` shows IPC 405 as `previous` of the IPC 406 hit.
- A hit on the first section of an Act has `previous: null`; a hit on the last has `next: null`. Expected neighbours derive from the index, not a hand-written list.
- `tools/list` shows `adjacent` as `{type: boolean}` and not required.
- Known-bad run: a server whose `adjacent` path reorders or drops hits makes the order test fail; observe it once.
- All slice 4 tests pass unchanged.
