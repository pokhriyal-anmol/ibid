# search gains an optional act, with no-act output unchanged

Status: done
Blocked by: 03

What to build: the `search` tool in `src/ibid/mcp.py` takes an optional `act` (`ipc`, `bns`, `crpc`, `bnss`). `crpc` and `bnss` search the second index and return sections of that Act only, with their Arrangement headings; `ipc` and `bns` restrict to that Act within the first index. With no `act`, search runs over the first index only and returns exactly what it returned before this slice, in the same order. An unknown `act` value is an invalid-params error. The Raw query reaches retrieval unchanged (ADR 0001, ADR 0004); no ranking change.

User stories: 6.

Acceptance criteria:
- Before any code change, record the no-`act` output of a fixed list of queries (including those in the existing MCP tests) as a fixture; a `unittest` through `ibid mcp` asserts the same output after the change, byte for byte.
- A `unittest` through `ibid mcp`: `search` with `act: "crpc"` on a fixture keyword returns only CrPC Citations with headings; `act: "bnss"` only BNSS ones.
- Seen to fail once: no-`act` search made to include second-index sections changes the recorded output and the test catches it.
- An invalid `act` returns an error. `uv run python -m unittest discover -s tests` passes.
