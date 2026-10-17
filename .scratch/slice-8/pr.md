## Summary

The BNS gazette prints each section's heading in a right-hand margin column. The BNS parser read only the body text, so 251 of 358 sections had no heading, and the MCP `adjacent` neighbours showed a truncated opening sentence (decision D-001) instead of a title.

This slice adds `src/ibid/headings.py`, a sidecar that reads the margin column from `pdftotext -layout` of the BNS PDF and joins wrapped lines with single spaces. IPC headings are the text of the top-level Provision before its first em dash. The sidecar is not part of the index: the `provision` table, the full-text index, `PARSER_VERSION` and every pinned file are unchanged. No ADR is contradicted. Headings are display only, so ADR 0001 (no model in retrieval, raw query only) still holds.

What shipped, by ticket:

- 01: `ibid headings list --act bns|ipc` prints `citation<TAB>heading` per top-level section, with counts of sections with and without a heading and a list of the ones without.
- 02: a test compares BNS headings with the subject column of the CAPT correspondence table, an independent source, after lowercasing and removing punctuation. It is skipped with a message when the CAPT text file is absent.
- 03: `ibid mcp` builds the sidecar at start. `get_provision` and every `search` hit carry a `heading` field, null for a sub-provision. Ranking and the hit list are unchanged.
- 04: `adjacent` neighbours use the real heading where one exists and keep the D-001 fallback only where the sidecar has null.

Follow-up changes after review:

- `MIN_RATE` in `tests/test_headings_capt.py` is restored to 0.90, matching story 3 and ticket 02. The comment that excused 0.83 is removed.
- The match rate now counts every table-listed top-level BNS section. A null or missing heading counts as a mismatch and is listed.
- The check prints the match rate and every mismatch (citation, heading, subject) on every run, not only on failure.
- The fallback test in `tests/test_mcp.py` records in a comment its exception to AGENTS.md rule 5, because the stdio server cannot start with a modified sidecar.

## Test plan

- [x] Layout-parser fixture tests run through `ibid headings list`, each seen to fail on known-bad input (wrong-section heading, wrapped heading cut short, chapter title taken as a heading).
- [x] `get_provision` and `search` heading assertions through the stdio harness, including null for a sub-provision.
- [x] Adjacent neighbours show the real heading, and the D-001 fallback appears when a heading is removed.
- [x] Full suite ran: 267 tests in 35.571s, 1 failure (see Known issues).
- [ ] CAPT cross-check at 90 percent: fails, see Known issues.

## Known issues

Tests are not green. The run ended `FAILED (failures=1)`: `test_headings_match_the_table_subjects` reports `0.836... not greater than or equal to 0.9 : match rate 83.6% is below 90%`.

- The real CAPT match rate is 83.6 percent, below the 90 percent bar in story 3 and ticket 02. Ticket 02 is marked done against a bar it does not meet. Reaching 90 percent needs parser or normalisation changes, which risks tuning to the check (AGENTS.md rule 3), or the owner amending story 3 and ticket 02. That decision is the owner's.
- The fallback test in `tests/test_mcp.py` still calls `mcp.handle` directly. Driving it over stdio needs a new `ibid mcp` option to load a modified sidecar, which is a new feature. The exception to AGENTS.md rule 5 is recorded in a comment.
