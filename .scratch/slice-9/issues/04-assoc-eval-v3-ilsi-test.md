# `ibid assoc eval` scores assoc-nb v3 once on the ILSI test split

Status: done
Blocked by: 01, 02

What to build: `ibid assoc eval` records the model's own layer version from its header in the result and in `results/test-ledger-assoc.json` (today it writes the module constant `v1`, so a v3 run would be logged as v1 and the once-only check would compare against v1's entry). Per open question Q-005's default, report micro-F1 over v3's own label space as the rule's figure and record, in the same single run, the micro-F1 over v1's label space beside it, so either reading needs no second test scoring. Then run it once on the ILSI test split, writing `results/layers/assoc-nb-v3-test.json` (or the existing naming pattern for v1).

User stories: 4, 7.

Acceptance criteria:
- A test drives `ibid assoc eval` on an invented test split with a v3 model and asserts the ledger entry names `v3` and the model hash; a second run is refused without `--rescore-test`. Run once with the version still taken from the constant (known-bad) and seen to fail.
- A test asserts the result carries both micro-F1 figures, each labelled with its label space and size.
- The ledger gains exactly one v3 entry; its existing v1 and v2 entries are unchanged byte for byte.
- v1 re-evaluated on a dev or invented split gives the same scores as before the change.

## Default taken

Q-005 (which label space the ILSI test micro-F1 floor of 33.4 is judged over) is pending with the owner. Default: the rule's figure is micro-F1 over v3's own label space, the same procedure that produced v1's 35.4. The micro-F1 over v1's label space is computed in the same single test run and recorded beside it, labelled with each space's size, so a different owner answer changes only the verdict line in ADR 0008 and the ticket 6 report and needs no second test scoring.
