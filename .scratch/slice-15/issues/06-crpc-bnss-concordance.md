# Concordance CrPC to BNSS from the table, pinned, verified entries served

Status: done
Blocked by: 03

What to build: extend `ibid concordance from-table` so it reads the BNSS to CrPC correspondence table (`pdftotext -layout` text of `comparison_summary_BNSS_to_CrPC.pdf`, BNSS in the first column) against `data/index/procedure.sqlite`, and writes `concordance/crpc-bnss-v1.json` plus `concordance/crpc-bnss-v1.sha256`. Entries are typed one-to-one, split, merged, new and removed as in Concordance v3. Only section numbers and row references are stored, never table text (D-007). An entry is verified only when both Citations exist in the index and the table row and both Arrangement headings agree under the same skeptic rules as the BNS. A cross-check of table subjects against BNSS headings is a tripwire at 80% (D-004), every mismatch printed. The `concordance` tool in `ibid mcp` accepts a CrPC Citation (returns BNSS successors and type) and a BNSS Citation (returns CrPC predecessors), with the direction taken from the Citation's Act or a new direction value; an unverified entry is never served and answers "no verified concordance". Existing IPC and BNS concordance behaviour is unchanged.

User stories: 4, 5.

Acceptance criteria:
- Invented mini-table fixture with a one-to-one row, a split row, a merged row, a new BNSS section and a removed CrPC section, plus a row whose headings disagree.
- A `unittest` through `ibid concordance from-table` asserts the entry counts by type and by verified or not, and that the disagreeing row is unverified.
- A `unittest` through `ibid mcp` `concordance`: correct BNSS successors and type for a CrPC Citation, correct CrPC predecessor for a BNSS Citation, and "no verified concordance" for the unverified one.
- Seen to fail once: an unverified entry made servable is caught; the tripwire fails on a shifted (known-bad) table parse.
- On the real table, `concordance/crpc-bnss-v1.json` matches its pin in a test; the tripwire rate and every mismatch are printed.
- `concordance/v2.json` and `concordance/v3.json` are untouched (byte-identity test passes). `uv run python -m unittest discover -s tests` passes.
