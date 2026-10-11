# BNS sub-provisions as separately addressable provisions

Status: done
Blocked by: 01

## What to build
Extend the BNS parser so subsections, clauses, provisos, explanations, exceptions and illustrations are separate provisions in the section tree, each with its own canonical citation (for example `BNS 103(1)`, the first proviso to `BNS 8(2)`) and parent and child addresses. Fix the canonical citation format for each provision kind here; every later ticket uses it. Add subsection and proviso lookup items to the draft gold file.

## User stories
3, 6, 9

## Acceptance criteria
- [ ] Through `ibid eval`, a subsection-and-proviso lookup item such as `BNS 103(1)` returns exactly that provision's verbatim text, not the whole section.
- [ ] Provisos, explanations, exceptions and illustrations each resolve by their own citation.
- [ ] Looking up a section still returns the section with its child addresses.
- [ ] The 358 section-count check still passes, and the per-category score in the results file shows the new category.
- [ ] Results stay byte-identical across two runs.
