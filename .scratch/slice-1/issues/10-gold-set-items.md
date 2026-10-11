# Draft, refute, spot-check and freeze the gold set (about 48 items)

Status: ready-for-human
Blocked by: 07, 09

## What to build
The real gold set. Proposed mix: section lookup 8, subsection and proviso 10, cross-reference chain 8, IPC to BNS 10, BNS to IPC 8, keyword 4. The 18 concordance items are the correspondence items and are flagged.

Independence: drafting reads the PDF page text (`pdftotext` per page), never the index or any parser output. Every item records the PDF page and the pinned file's SHA-256 so it can be checked at the source. A second agent tries to refute each item. The 21 existing draft items stay as test fixtures. The 4 chain and 3 keyword draft items were derived from system output and are replaced.

You check at least 12 items, 8 correspondence and 4 others. Then the file is frozen as version 1 and its hash is pinned with the mechanism from ticket 07.

## User stories
16, 17, 22

## Acceptance criteria
- [ ] About 48 items, each with a category, a PDF page citation and the source file hash; correspondence items flagged.
- [ ] A record of the spot-checked items (at least 12, 8 correspondence) and their outcome.
- [ ] Any item you reject is fixed or dropped before freezing, and the record shows it.
- [ ] The pin file and the versioned gold file are committed together.
- [ ] Frozen before any scored baseline run (ticket 08).
