# Verified concordance entries (about 60)

Status: done
Blocked by: 05

## What to build
The real concordance data: about 60 IPC sections chosen to cover every mapping type (one-to-one, split, merged, removed) plus BNS sections with no IPC ancestor (new), and every section the gold items in ticket 10 need. Each entry cites the PDF page of the pinned IPC and BNS files (see `data/SOURCES.md`) and records its type.

Process: candidates come from comparing the two Acts' page text, not from the index. Web conversion tables may suggest candidates and never decide. A second agent tries to refute each entry from the same pages, defaulting to refuted if unsure. Entries that survive are put on a review sheet. An entry is `verified: true` only after that, and contested entries stay `verified: false`.

Every IPC section not in the file answers "no verified concordance". Do not fill the file out to look complete.

## User stories
11, 12, 13, 22

## Acceptance criteria
- [ ] About 60 entries, each with both PDF page citations and a type; every type represented.
- [ ] Each served entry survived refutation; contested entries are `verified: false` and listed.
- [ ] A review sheet lists each entry with the side-by-side source text and both page numbers.
- [ ] The loader from ticket 05 accepts the file.
- [ ] Your spot-check is recorded (at least 8 entries) with the outcome.
