# feat: CrPC and BNSS in a second index, with a verified CrPC to BNSS concordance

## Summary

Ibid covered two Acts, the IPC and the BNS. The Code of Criminal Procedure 1973 is the largest missing Act for the ILSIC layperson benchmark (376 of 2,005 gold labels, 18.8%, counted on 2026-10-22), and the BNSS 2023 replaced it on 1 July 2024. This slice adds both as Acts with the same guarantees as the IPC and the BNS: verbatim text, exact Citation, Cross-references, headings, and a verified Concordance between them.

They live in a second index, `data/index/procedure.sqlite` (ADR 0010). The first index, the frozen rule, every pin and every committed result stay byte-identical, because the first index hash is recorded inside results and BM25 statistics depend on the whole corpus. The MCP server opens both.

What was built, by ticket (all seven are done):

- 01: `ibid setup` checks the three new source files offline (BNSS Gazette PDF, CrPC India Code PDF, the BNSS to CrPC correspondence table), with bytes and SHA-256 recorded in `data/sources.json`. A download with a wrong hash is rejected.
- 02: CrPC parser and the `procedure.sqlite` build. Headings come from the Arrangement of Sections, and the parsed section count and heading match are checked against it. `get_provision` serves CrPC Citations.
- 03: BNSS parser in the same index. A `BNSS` Citation never resolves to the BNS section of the same number, and a Citation in neither index is a tool error naming IPC, BNS, CrPC and BNSS.
- 04: Cross-references resolved within each Act only. A reference to another Act is recorded as unresolved with its target Act named.
- 05: `search` takes an optional `act` (`ipc`, `bns`, `crpc`, `bnss`). With no `act` it behaves exactly as before, over the first index only.
- 06: `concordance/crpc-bnss-v1.json` with a SHA-256 pin, built by `ibid concordance from-table`. Only verified entries are served, and the `concordance` tool accepts CrPC and BNSS Citations.
- 07: `docs/claims.md` coverage rows and check results, pinned by `tests/test_claims.py`, and the slice report. No retrieval accuracy is claimed.

Deviation from the spec: the PRS Gazette copy of the BNSS prints no Arrangement of Sections. Spec decisions 4 and 7 were amended with a BNSS exception: the count is checked against the published 531, headings are the Gazette margin notes read by the BNS margin method, the 98% heading floor is met vacuously, and BNSS headings are checked indirectly by the 80% tripwire. ADR 0010 records this.

Fixes made during review:

- BNSS Part sub-headings are stripped from section text. The mini fixture gained a Part heading, and a real-PDF test checks BNSS 71, 83, 456 and 471.
- BNSS 246 heading and body fixed in `headings._cut`: a wrapped right-margin note whose first line starts left of the margin column is cut at its own start. BNS headings are byte-identical before and after, and a real-PDF regression test was added.
- `table._norm` removed; `table.py` imports `crpc._norm`, which now treats a hyphen as a space. The tripwire stays at 89.5% (the deletion rule dropped it to 87.8%). CrPC heading match is now 99.25% (530 of 534) and CrPC 265I is no longer a mismatch. `claims.md` and the report were updated, and `concordance/crpc-bnss-v1.json` is unchanged byte for byte.
- `ilsic.IPC_LABEL` deleted; `ilsic` uses `assoc.IPC_CITE`, widened once to `[A-Z]{0,2}`.
- `candidates()` runs one provision query instead of two. `arrangement()` returns `[tuple(x) for x in out]`.
- The removed-entries-never-verified decision is recorded in ADR 0010 and the CONTEXT.md Concordance entry. ADR 0010 text now says both Acts were built together and mentions the search `act`, error and direction values. CONTEXT.md Act, Cross-reference graph and Concordance entries cover CrPC and BNSS.

Not covered: Schedules and Forms of both Acts, Hindi text, state amendments, and CrPC amendments after the November 2019 India Code revision (taken from the Internet Archive capture). No lawyer reviewed the text or the Concordance; the count and heading checks do not confirm the body text is right.

## Test plan

- [x] `uv run python -m unittest discover -s tests`: Ran 401 tests in 57.285s, OK.
- [x] Count and heading checks per Act, with known-bad tests: a dropped section and a removed margin heading each exit 1, print the mismatch and write no index (BNSS total read from `IBID_BNSS_TOTAL`, default 531). Each mutation was observed failing.
- [x] ILSIC report test now compares each (benchmark, layer, version) micro-F1 cell to the result file; observed failing against an altered cell.
- [x] Claims test checks every figure inside its own ledger or coverage row with digit boundaries; observed failing with two altered figures.
- [x] BNS headings byte-identical before and after the `headings._cut` change; `concordance/crpc-bnss-v1.json` byte-identical after the `_norm` change.
- [x] Real-PDF regression tests for BNSS 71, 83, 456, 471 and 246.
- [x] Byte-identity test for the first index, baseline results, pinned files and `results/`.

## Known issues

- BNSS headings are not checked against a second source at the 98% floor. The spec was amended to state the BNSS exception instead of adding a second-source check (see Summary).
- Side effects of earlier fixes: the tripwire is now 89.5% (56 of 531) after the BNSS 246 fix, so `claims.md`, the report and its mismatch table were updated. Widening `IPC_CITE` could change `assoc` behaviour for two-letter suffix sections; the full suite and the pinned-result tests pass.
