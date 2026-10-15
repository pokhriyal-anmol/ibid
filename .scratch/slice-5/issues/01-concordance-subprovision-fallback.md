# concordance falls back from a sub-provision Citation to its section

Status: done
Blocked by: none

What to build: in the `concordance` tool path (`src/ibid/mcp.py`, calling `concordance.lookup`), when the Citation carries a sub-provision suffix (e.g. `BNS 318(4)`) and has no verified Concordance entry, retry with its section Citation (`BNS 318`). If that finds entries, return them plus a field naming the Citation they came through (default name `via`, value `BNS 318`). If the section also has none, return the existing `no verified concordance` result, not an error. A Citation that is already a section never falls back and never carries the field. No change to the pinned concordance file or to `concordance.lookup` semantics for section Citations.

User stories: 1, 2, 3, 9.

Acceptance criteria (through the stdio harness in `tests/mcp_harness.py`, new tests in `tests/test_mcp.py`):
- `concordance BNS 318(4)` returns the same entries as `concordance.lookup(entries, 'BNS 318', ...)` on the same index, plus `via: 'BNS 318'`.
- A sub-provision whose section also has no verified entry returns `no verified concordance` with isError false.
- `concordance BNS 318` returns a payload identical to slice 4 output, with no `via` field.
- Known-bad run: a server that applies the fallback to a section Citation (or adds `via` to a section result) makes the section test fail; observe it once.
- All slice 4 tests in `tests/test_mcp.py` pass unchanged.

## Default taken

The fallback field is named `via` and holds the section Citation string (e.g. `"BNS 318"`). The spec does not name it; rename later if the owner prefers another key.
