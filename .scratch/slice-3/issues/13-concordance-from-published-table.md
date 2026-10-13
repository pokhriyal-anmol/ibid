# Verify more concordance entries against a published correspondence table

Status: ready-for-agent
Blocked by: none (downloads approved 2026-10-13, files under `data/raw/capt/` and `data/raw/uppolice/`)

What to build: concordance v3, with many more entries served as verified, so that routes A and B stop returning nothing for the BNS. Today 12 of 66 entries are served. The BNS side of every layer depends on this.

Source. "Correspondence Table and Comparison Summary of the Bharatiya Nyaya Sanhita, 2023 (BNS) to the Indian Penal Code, 1860 (IPC)", a 38 page document by the Director of CAPT Bhopal (IPS), June 2024, available from https://www.keralaprisons.gov.in/userfiles/act-and-rules/comparison_summary_BNS_to_IPC.pdf. It is a person's compilation and not an official Ministry of Home Affairs publication, and the report must call it that. The second downloaded document (`data/raw/uppolice/ipc-vis-a-vis-bns.pdf`) is Project 39A's annotated comparison of the August 2023 *Bill*, whose clause numbers differ from the enacted BNS (murder punishment is clause 101 there and 103 in the Act). It is not a source for BNS numbers. It may cross-check the IPC side of a row by subject name ("Punishment for murder" to S. 302) and nothing more.

Method, deterministic first, agents last:

1. Parse the table's text layer into rows of BNS section or subsection, subject, IPC sections and comparison note, with a parser written for this layout and tested on an invented fixture of the same shape. Rows whose IPC column says `New` are `new` entries. Rows with no IPC counterpart in the table are `removed` candidates only if the table says so.
2. Aggregate sub-sections to section level and produce candidate entries with their type (one-to-one, split, merged, new, removed) computed from the row counts.
3. For every IPC section in the ILSI 100 labels, every section cited in `gold/multicharge/v1.json` and `v2.json`, and every existing draft entry, check the candidate against the source texts the way `ibid conform` does (the cited provisions exist in the index, and the BNS text and the IPC text share the offence's distinctive words). An entry the table and the texts disagree on is not served.
4. An independent skeptic agent challenges each served candidate against the BNS and IPC page text, defaulting to refuted, as in slice 1.
5. Entries are written with `basis: source-table-checked` (a new value the loader and `ibid freeze` accept) and `evidence` naming the table row and the page. Entries from a second source that agree are marked as such.

Split of work: the builder writes the table parser, the candidate-entry command (`ibid concordance from-table --table <pdf-text-file> --index <index> --out <candidates.json>`), the loader and freeze support for the `source-table-checked` basis, and fixture tests. The real run (parsing the real table, the text check, the skeptic pass and `concordance/v3.json`) is done by the orchestrator, because worktrees have no raw data.

Nothing is taken from the agents' labels in `gold/multicharge/v1.json`, which would be circular.

User stories: 3, 6.

Acceptance criteria:
- The table parser reproduces the rows of an invented fixture, including a row with sub-sections, a `New` row and a row whose IPC cell holds two sections ("29 and ...").
- Known-bad: a fixture where the table maps a BNS section to an IPC section whose text shares no distinctive word with it is not served.
- `concordance/v3.json` has a pin, and `concordance/v2.json` and its pin are untouched.
- On the real data the report states: rows parsed, entries produced by type, entries served, entries refused with the reason counts, and how many of the ILSI 100 labels now have a verified BNS counterpart.
- With v3, `ibid cited extract` and `ibid assoc predict` are re-run on set v1 once each, and the BNS recall is reported next to the v2 figure of 0 percent, with a statement that any change is a change in coverage and not in the extractor.
- The table's licence or copyright statement is recorded in `data/SOURCES.md`, and the PDF stays under `data/raw/`, not in git.
