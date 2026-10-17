# Pin the missing definition-punishment edges in the Cross-reference graph, and write ADR 0007

Status: done
Blocked by: none

What to build: a test that loads the real index and the resolved Cross-reference graph (`src/ibid/xref.py`, read through the existing `ibid mcp` cross_references lookup or the index the `ibid` commands build) and asserts there is no edge, in either direction, between IPC 302 and IPC 300, IPC 406 and IPC 405, IPC 420 and IPC 415. Also assert the graph's edge count (615 total, 586 resolved) so a later change to xref that adds edges makes the test fail loudly rather than silently. Write `docs/adr/0007-definition-punishment-links-from-headings.md`: the heading-link rule (spec Decisions 1 and 2), why the Cross-reference graph was not used (the three pairs above, implicit links via defined terms), and that expansion runs after ranking so ADR 0001 holds. No production code changes.

User stories: 1. Spec Decision 6.

Acceptance criteria:
- The test passes on the real Acts and runs inside `uv run python -m unittest discover -s tests`.
- Known-bad run, observed once: injecting a fake edge IPC 302 -> IPC 300 into the graph the test reads makes it fail on the absence assertion (not on some earlier line).
- If the measured edge counts differ from 615/586, the test records the measured figures and the ADR states them with the date; the spec figure is not forced.
- ADR 0007 exists, uses CONTEXT.md terms (Cross-reference, Concordance, Citation, Frozen rule), and contains a diagram.
- `git diff` touches no file under `src/`, `gold/`, `concordance/` or `results/`.
