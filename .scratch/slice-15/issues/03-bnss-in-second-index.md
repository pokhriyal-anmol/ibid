# BNSS added to the second index, checked, and kept apart from the BNS

Status: done
Blocked by: 02

What to build: a BNSS parser for `bnss-prs.pdf` (Gazette layout) writing into `data/index/procedure.sqlite` beside the CrPC, Citations `BNSS 482` and `BNSS 482(1)`, same text conventions as ticket 2, headings from its Arrangement of Sections. The same count and heading checks run for the BNSS. `get_provision` returns BNSS provisions. A `BNSS` Citation never resolves to the `BNS` section of the same number, and a Citation in neither index (e.g. `CrPC 9999`) is a tool error naming the four covered Acts (IPC, BNS, CrPC, BNSS).

User stories: 1 (BNSS part), 3 (BNSS part), 7.

Acceptance criteria:
- Invented mini-BNSS fixture in the Gazette shape with an Arrangement, a section with sub-sections and a proviso, sharing a section number with a BNS fixture section.
- A `unittest` through the build command and `ibid mcp`: `get_provision` for `BNSS 482` and `BNSS 482(1)` returns the expected text, heading and children; sub-provision text starts at `(1)`.
- Seen to fail once: a `BNSS` Citation made to resolve to the BNS section of the same number returns the BNS text and the test catches it.
- A `unittest` through `ibid mcp`: `get_provision` for `CrPC 9999` returns `isError: true` with a message naming IPC, BNS, CrPC and BNSS.
- Count and heading checks for the BNSS pass on the fixture and fail on a dropped section and a changed heading.
- On the real PDF, the count matches its Arrangement and the heading-match rate is at least 98%, with every mismatch printed.
- The byte-identity test from ticket 2 still passes. `uv run python -m unittest discover -s tests` passes.
