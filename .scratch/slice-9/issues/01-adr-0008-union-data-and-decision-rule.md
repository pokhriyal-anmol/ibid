# ADR 0008: train assoc-nb v3 on both sources, with the decision rule fixed before any score

Status: done
Blocked by: none

What to build: `docs/adr/0008-association-layer-fitted-on-both-kinds-of-text.md`. It widens the data clause of ADR 0005 and ADR 0006 to the union of ILSI train (minus set v1 ids) and ILSIC-Lay train (minus set v2 ids and posts that duplicate a Layman test post), concatenated raw counts, no weighting, resampling or tuning (D-003). It states the six-comparison decision rule from spec decision 7 verbatim, per set and Act (D-002): set v1 IPC > 15.3 and BNS > 16.3; set v2 IPC >= 49.8 and BNS >= 59.2; ILSI test micro-F1 >= 33.4. It names the label space the micro-F1 comparison uses (see open question Q-005; default: v3's own label space, with the figure over v1's label space recorded beside it). Kept only if all six hold, else recorded as negative and v1 and v2 remain the options. Committed before tickets 3 and 4 produce any score.

User stories: supports 6 (the rule the report applies); spec decisions 6 and 7.

Acceptance criteria:
- The ADR file exists, links ADR 0005, 0006, D-002 and D-003, and lists the six thresholds with the numbers above.
- `git log` shows the ADR commit precedes any commit that adds a v3 results file or a v3 entry in `results/test-ledger-assoc.json`.
- No pinned file, frozen rule or existing result changes (`git diff --stat` touches only `docs/adr/`).

## Default taken

Q-005 (which label space the ILSI test micro-F1 floor of 33.4 is judged over) is pending with the owner. Default: the rule's figure is micro-F1 over v3's own label space, the same procedure that produced v1's 35.4. The micro-F1 over v1's label space is computed in the same single test run and recorded beside it, labelled with each space's size, so a different owner answer changes only the verdict line in ADR 0008 and the ticket 6 report and needs no second test scoring.
