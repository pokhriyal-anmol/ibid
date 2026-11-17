# CrPC parsed into a second index, checked against its Arrangement, served by get_provision

Status: done
Blocked by: none

What to build: the first end-to-end path for one new Act. A CrPC parser (new module, e.g. `src/ibid/crpc.py`) produces a Section tree from `crpc-indiacode.pdf`: Citations of the form `CrPC 438`, `CrPC 41A`, `CrPC 438(1)`; a sub-provision's text starts at its own label with no section prefix; provisos, explanations and illustrations are part of their section's text; amendment marks and footnote numerals are dropped; Schedules and Forms are not parsed. A new `ibid` build command writes `data/index/procedure.sqlite` with the same schema as `data/index/ibid.sqlite`, recording its own parser version (do not bump `PARSER_VERSION` for the IPC and BNS). Headings come from the Arrangement of Sections (decision 7). The independent check (decision 4) parses the Arrangement and compares: the top-level section count equals the Arrangement count (532 entries in the real file; a repealed section counted the way the Arrangement counts it), and each body heading equals its Arrangement heading after lower-casing and removing punctuation, every mismatch printed, under 98% fails. `ibid mcp` opens the second index next to the first and `get_provision` returns verbatim text, heading and child Citations for a CrPC Citation. Write ADR 0010 (a second index, not a rebuilt one, and why: the first index hash is in results and BM25 statistics depend on the whole corpus). Add the byte-identity test of decision 10.

User stories: 1 (CrPC part), 3 (CrPC part), 9.

Acceptance criteria:
- Invented mini-CrPC under `tests/fixtures/` in the shape of the real PDF: an Arrangement of Sections, a lettered section (`41A`), a section with a proviso and an illustration, a repealed section, sub-sections.
- A `unittest` through the build command and `ibid mcp` over stdio: `get_provision` for `CrPC 41A` and for a sub-provision returns the expected text (sub-provision starting at its own label), heading and children.
- A `unittest` of the check passes on the fixture and fails on known-bad input: a section dropped from the parse (count differs) and a heading changed (mismatch printed, rate below 98%).
- Byte-identity test: `data/index/ibid.sqlite`, `results/baseline-v2.json`, every pinned file (`gold/v2.json`, `concordance/v2.json`, `concordance/v3.json` and their pins) and all of `results/` hash the same before and after the build; seen to fail once when the first index is altered. `ibid eval --gold gold/v2.json --concordance concordance/v2.json` still reproduces `results/baseline-v2.json` byte for byte.
- On the real PDF (read by absolute path in a worktree), the count matches the Arrangement and the heading-match rate is at least 98%; the rate and every mismatch are printed.
- `ibid mcp` with no procedure index present behaves exactly as before; existing `tests/test_mcp.py` passes unchanged.
- `docs/adr/0010-*.md` exists. `uv run python -m unittest discover -s tests` passes.
