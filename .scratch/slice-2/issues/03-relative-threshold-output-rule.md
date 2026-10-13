# Report the relative score threshold alongside top-k

Status: done
Blocked by: 02

What to build: a second output rule in the run command: predict every section whose rolled-up score is at least a fraction r of that query's top section score (relative because BM25 scores are not comparable across queries). Each results file reports both rules side by side, with k and r recorded in the rule parameters and therefore in the rule hash. The roll-up score for a section (for example max over its provisions) is a declared parameter.

User stories: 5.

Acceptance criteria:
- On the fixture, r = 1.0 predicts only the top section(s) and a small r predicts every retrieved section; both match hand-computed sets.
- The results file holds scores for both top-k and threshold rules from one run.
- Changing r or the roll-up choice changes the recorded rule hash.
- Determinism still holds: two identical runs are byte-identical, including ties in score (tie-break is by citation string).
