# Report applying the decision rule to assoc-nb v3: kept or negative

Status: done
Blocked by: 03, 04

What to build: a short report (`.scratch/slice-9/v3-report.md`, following the slice 6 report pattern) that reads the v3 results files and the ILSI test result, and for each of the six comparisons in ADR 0008 prints the v2 or v1 reference figure, the threshold, v3's figure and pass or fail; states kept (all six hold) or negative. It reports the vocabulary size, the share of training examples from each source (from the model header), v1's and v3's label-space sizes next to the micro-F1, and both micro-F1 figures from ticket 4. If negative, it says v1 and v2 remain the two options. It makes no claim of legal accuracy.

User stories: 6, 7.

Acceptance criteria:
- Every number in the report is read from a results file or model header this session, not typed by hand; re-running the generator gives the same file.
- Known-bad check: feeding the generator a v3 result with set v1 IPC recall of 15.3 (equal to v2, not higher) yields fail on that line and verdict negative.
- The six thresholds printed match ADR 0008 exactly.
- `git diff --exit-code` passes on the baseline, the frozen rule, `gold/`, `concordance/` and all pre-slice results files.

## Default taken

Q-005 (which label space the ILSI test micro-F1 floor of 33.4 is judged over) is pending with the owner. Default: the rule's figure is micro-F1 over v3's own label space, the same procedure that produced v1's 35.4. The micro-F1 over v1's label space is computed in the same single test run and recorded beside it, labelled with each space's size, so a different owner answer changes only the verdict line in ADR 0008 and the ticket 6 report and needs no second test scoring.
