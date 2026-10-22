# Slice 15 v1 report

## Status

Built. All 7 tickets are done, none failed or held back, and every user story (1 to 10) has at least one done ticket. The review step fixed 12 findings and left two noted items, listed under Held back.

## What v1 does

Ibid now covers two more Acts, the CrPC (November 2019 India Code revision) and the BNSS, kept in a second index (`data/index/procedure.sqlite`) so the IPC and BNS index and the baseline results are unchanged. `get_provision` returns verbatim text, heading and child citations for `CrPC 438` or `BNSS 482(1)`, and a sub-provision starts at its own label. A BNSS citation never resolves to the BNS section of the same number, and a citation in no index is an error naming IPC, BNS, CrPC and BNSS.

`ibid setup` reports the three new source files by presence, size and hash, offline, and downloads one only when its hash is recorded. Cross-references resolve within each new Act, and references to other Acts are recorded as unresolved with the target Act named. `search` takes an optional `act` (`ipc`, `bns`, `crpc`, `bnss`); with no `act` its output is unchanged.

A pinned CrPC to BNSS concordance (`concordance/crpc-bnss-v1.json`) is built from the published table and served by the `concordance` tool in both directions. Only verified entries are served. `docs/claims.md` has new CrPC and BNSS coverage rows and a check-results row, pinned by `tests/test_claims.py`. No retrieval accuracy is claimed and no lawyer reviewed the texts or the concordance.

## How to run it

```bash
uv sync
uv run ibid setup --fetch bns
uv run ibid setup --fetch ipc --url <link>
uv run ibid setup
uv run ibid eval --gold gold/v2.json --concordance concordance/v2.json --out results/run.json
uv run python -m unittest discover -s tests
```

`results/run.json` should be byte-identical to `results/baseline-v2.json`. The build and `ibid mcp` commands for the procedure index are described in `docs/adr/0010-procedure-acts-in-a-second-index.md` and `.scratch/slice-15/pr.md`.

## Tests

Green. The full suite and the pinned-result tests pass after the review fixes. Each new check was observed failing against known-bad input.

## What I assumed for you

- Q-008: default taken. BNSS headings are the margin notes, the count is checked against the published 531, and the 98% heading floor on the real PDF is met only trivially because the Gazette has no Arrangement of Sections. The spec now says so, and the 80% table-subject tripwire (89.5%, 56 of 531 mismatches counted per the report) is the indirect heading check.

## Held back

No tickets were held back. Two review items were not fixed: a second-source check of BNSS headings (spec amended instead), and the side effects of earlier fixes (tripwire moved to 89.5% and the IPC_CITE widening, both documented and tested).

## Checks made after the build (2026-10-22, by the session, not by the workflow)

- Full suite: 401 tests, OK, with `__pycache__` cleared first. `ibid eval` on gold v2 reproduces `results/baseline-v2.json` byte for byte, and `data/index/ibid.sqlite` is unchanged (hash prefix `efaf6fe8`, the one recorded in earlier results; file dated 12 Oct).
- Counts from `procedure.sqlite`: CrPC 534 top-level sections, BNSS 531. My independent count of the CrPC Arrangement (532 entries, regex on the PDF text) is fully contained in the parsed set. The two extra sections, 105I and 265I, are real: the Arrangement prints them with a hyphen (`105-I`), which my regex missed and the parser handles (`src/ibid/crpc.py`).
- Known pairs through the real concordance, all one-to-one and verified: CrPC 438 to BNSS 482, 154 to 173, 161 to 180, 164 to 183, 125 to 144, 144 to 163, 482 to 528.
- A gap: CrPC 41A is typed "removed" and unverified, but the table row for BNSS 35 reads "41 & 41A". Compound cells are left unverified (33 of the 75 unverified entries have a range, cut-off or unreadable cell; 42 have no table row citing them). Nothing wrong is served, but recall is lower and the "removed" label on such an entry is misleading. The concordance has 573 entries: 498 verified (490 one-to-one, 8 other), 40 new, 42 removed, 1 merged by the file's own types.
- Server smoke test on real data: `get_provision` for CrPC 438 returns the verbatim text with its heading; `concordance` answers in both directions; `CrPC 9999` is a tool error naming the four Acts; `search` with `act: "crpc"` and `act: "bnss"` returns hits; with no `act` it still returns BNS results. Keyword search needs every term to match (existing behaviour), and its ranking on these Acts has no gold set, so no quality is claimed.
- The BNSS heading check is weaker than the spec promised (Q-008): the Gazette has no Arrangement, the count is checked against the published 531, and the independent heading check is the 89.5% match against the table subjects.

## Your questions

3 pending, 0 blocking. That is below the batch size of 8, so none are asked yet; the work carries on without them.
