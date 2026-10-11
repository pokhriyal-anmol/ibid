# Slice 1: reproducible citation and cross-reference baseline

## Summary

This slice builds the measurement layer for Ibid: one `ibid eval` command that parses the IPC and the BNS into section trees, resolves cross-references by rule, answers a gold set of questions from a SQLite index, and writes a results file carrying the gold-set hash and parser version. No model is called anywhere, which matches ADR 0001 (retrieval depends only on the raw query). The stack is Python, SQLite and `uv`, per ADR 0002. The point is a baseline score that later layers must beat, with no quality target set here.

Built and marked done: tickets 01 (BNS section lookup tracer), 02 (BNS subsections, provisos, explanations, exceptions and illustrations as separate provisions), 03 (IPC parser into the same tree and citation format), 04 (rule-based cross-reference resolution and chain lookup) and 06 (deterministic FTS5 keyword search with a citation tie-break).

Also changed in the review fix pass:
- `src/ibid/index.py` `search()` now returns `fetchall()` directly instead of copying the rows.
- `docs/agents/triage-labels.md` now lists `approved` and `done` as repo-extension status labels, since the tickets already used them outside the default five-role vocabulary.
- Two tests in `tests/test_eval.py` that read the schema are marked as explicit exceptions to the rule that tests go through the eval seam (the spec's single test seam).

Not built: tickets 05 (IPC-BNS concordance), 07 (frozen gold set) and 08 (baseline run and corruption check). See Known issues.

## Test plan

- [x] Full test suite run as documented in `CLAUDE.md`: 17 tests, OK.
- [x] Review found 6 confirmed issues; 3 were fixed and 3 remain open (below).
- [x] The ASCII and header regexes in the two schema-reading tests were checked against a Hindi string and a "GAZETTE" string, and both flagged them.
- [ ] The dangling-child check was not run against a bad index, so it has not been seen failing.
- [ ] Not run: two-run byte-identical comparison on a frozen gold set, and the corrupted-run check (both belong to ticket 08).

## Known issues

- Concordance missing (ticket 05). It needs a hand-checked IPC to BNS mapping from the gazette texts. The mapping will not be invented, so a human has to author the data first. Until then the concordance gold items (user stories 11, 12, 13, 22) cannot be answered.
- Gold-set hash pin not enforced (ticket 07). The ticket needs a human to draft about 50 items with gazette page citations and spot-check at least 10. Enforcing a pin on the current 21-item draft would break the tests that deliberately edit the gold file. The pin should be added once the gold set is frozen.
- Corrupted-run check for correspondence (ticket 08) is blocked by tickets 05 and 07.
- Dangling-child check unverified against a bad index (see Test plan).

Nothing here contradicts ADR 0001 or ADR 0002. The Act texts stay outside git until reuse terms are confirmed, as the spec requires.
