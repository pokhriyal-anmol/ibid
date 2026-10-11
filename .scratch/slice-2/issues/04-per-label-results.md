# Per-label precision, recall and F1 in the results file

Status: ready-for-agent
Blocked by: 02

What to build: the run command writes, for each of the 100 labels, its support, true positives, false positives, false negatives, precision, recall and F1, and lists labels never predicted correctly. Sorted by citation so output is stable. It also writes the same three scores for strata, so a change that helps multi-section cases can be seen not to hurt simple ones: by gold label count (1, 2, 3 or more) and by fact-paragraph length in words (up to 150, 151 to 500, over 500).

User stories: 7.

Acceptance criteria:
- On the fixture, per-label counts match hand-computed values, and macro F1 equals the mean of the per-label F1 values the file reports.
- A label with zero support and zero predictions is handled by a documented convention (stated in the results file) rather than a division error.
- On the fixture, strata scores match hand-computed values and the strata case counts sum to the split size.
- A fixture label that the rule can never retrieve (the Section 34 pattern: rarely named in facts) appears in the never-found list.
