# Cross-check BNS headings against the CAPT table subjects

Status: done
Blocked by: 01

What to build
A test that compares the BNS headings from `ibid headings list --act bns` with the subject column of the CAPT correspondence table, a second source that is independent of the gazette. It reads the table's text with the existing `table.parse_rows` in `src/ibid/table.py`. Both sides are lowercased and stripped of punctuation before comparison. Test only: nothing in the shipped headings depends on the table.

User stories: 3.

Acceptance criteria
- For the BNS sections the CAPT table lists, at least 90 percent of headings match the table's subject exactly after normalisation, and the test output lists every mismatch as citation, heading and subject.
- When the CAPT text file is absent, the test is skipped with a message that names the expected path and how to produce it.
- Run once against known-bad input and seen to fail: shift every heading by one section, and the match rate falls below 90 percent with the failure message naming the rate.
- `uv run python -m unittest discover -s tests` passes.
