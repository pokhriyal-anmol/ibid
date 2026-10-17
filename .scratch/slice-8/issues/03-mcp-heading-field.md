# Add `heading` to `get_provision` and `search` results in `ibid mcp`

Status: done
Blocked by: 01

What to build
`ibid mcp` (`src/ibid/mcp.py`) builds the headings sidecar for both Acts at start-up, next to the index it already builds. `get_provision` returns a `heading` field: the section's heading for a top-level BNS or IPC Citation, and null for a sub-provision or a section with no heading. Every `search` hit also carries `heading`. Ranking and the hit list do not change. Headings are for display only and are not used in retrieval (ADR 0001, spec out of scope).

User stories: 4, 5, and 7 for the server.

Acceptance criteria
- Through the stdio harness (`tests/mcp_harness.py`), `get_provision` for `BNS 83` returns heading "Marriage ceremony fraudulently gone through without lawful marriage.", an IPC section Citation returns its heading, and a sub-provision such as `BNS 85(1)` or an IPC sub-provision returns `heading: null`.
- A `search` call returns the same citations, in the same order, with the same text as the code before this ticket, and every hit has a `heading` key (null for a sub-provision hit).
- Each new assertion is run once against known-bad input and seen to fail, for example a heading taken from the next section.
- `ibid eval` still reproduces `results/baseline-v2.json` byte for byte, and the index file's hash recorded in results is unchanged.
- `uv run python -m unittest discover -s tests` passes.
