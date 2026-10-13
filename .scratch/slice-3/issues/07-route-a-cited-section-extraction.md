# Route A: find the sections a query cites, and map them to the other Act

Status: done
Blocked by: 06

What to build: `ibid cited extract --set <file> --index <index> --concordance <file> --out <predictions.json>`. For each item's raw query it finds explicit statute citations written in the text, resolves them to citations in the index, and writes a predictions file (ticket 06 format, layer `cited`). Code only. No model, no label, no retrieval score (ADR 0001).

Recognised forms, each with an Act attribution taken from the text: "Section 302 IPC", "Sections 302/201 of the Indian Penal Code", "u/s 307, 395 IPC", "S. 376(2)(i) IPC", "Section 420 read with Section 34 IPC", "Sec. 3 of the BNS", "Bharatiya Nyaya Sanhita". Lettered sections (304B, 498A, 354D) and sub-clauses resolve to the section-level citation. A list of numbers after a single "Section(s)" is read as that Act's sections. Sections 34, 109, 120B and 149 are returned like any other and are counted by the scorer only if the set lists them as charges.

Act attribution. A citation names its Act in the same clause or sentence. If the text names no Act near a number, the number is not returned, and it is counted as an ambiguous mention in the results file (the layer must not guess). Acts other than the IPC and the BNS (the CrPC, the POCSO Act, the NDPS Act, the Arms Act) are recognised by name and their numbers are dropped.

Mapping. A citation to one Act is returned for that Act. For the other Act, the mapping uses only entries in the concordance that are served as verified (`concordance` loader). An unmapped citation gives no prediction for the other Act. The results file counts these, so the BNS side is shown to be thin and not padded.

User stories: 4, 6, 8.

Acceptance criteria:
- On invented fixture queries each recognised form above resolves to the expected citation set, including a lettered section, a list, a "read with" and a sub-clause.
- Known-bad: a number with no Act nearby is not returned and is counted as ambiguous; a CrPC section ("Section 439 CrPC") is not returned as an IPC section; a section number that does not exist in the Act is dropped and counted.
- A section with no verified concordance entry gives no prediction for the other Act.
- Two identical runs are byte-identical.
- No label from any set, and no retrieval output, is read (stated in the module docstring and checked by a test that runs it with the labels removed).
- Run by the orchestrator after the merge: the real set v1 is extracted once, scored through ticket 06's command on both Acts, and the results report the counts of ambiguous mentions and unmapped citations. The report states that 29 of 30 queries name their sections and that some labels were drafted from those mentions.
