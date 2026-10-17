# Slice 7: the verdict on `links v1`

**Verdict: KEPT as an opt-in output only.** Decision 5 of the spec, applied as written. Nothing is wired into `src/ibid/mcp.py`.

## The rule applied

Kept only if per-charge recall rises on both multi-charge sets (v1 and v2) and ILSI test micro-F1 does not fall. Recall of a set is the charges found, summed over both Acts and both output rules, against the same count for the baseline.

| set | baseline found | links v1 found | recall rises |
| --- | --- | --- | --- |
| v1 | 17 | 21 | yes |
| v2 | 22 | 30 | yes |

| output rule | baseline test micro-F1 % | links v1 % | change (points) | micro-F1 |
| --- | --- | --- | --- | --- |
| top-k | 9.37 | 11.37 | +2.01 | rises |
| threshold | 9.64 | 11.81 | +2.16 | rises |

## Per set, Act and output rule

Added predictions are the sections links v1 appends that the baseline did not predict. An added prediction is correct when it is an accepted section of any charge of its item. Set v2 labels are incomplete, so the correct share there is a floor.

| set | Act | output | charges | found, baseline | found, links v1 | newly found | predictions added | added, correct | correct share % |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| v1 | IPC | top-k | 98 | 3 | 4 | 1 | 8 | 1 | 12.5 |
| v1 | IPC | threshold | 98 | 5 | 6 | 1 | 17 | 1 | 5.9 |
| v1 | BNS | top-k | 98 | 4 | 5 | 1 | 1 | 1 | 100.0 |
| v1 | BNS | threshold | 98 | 5 | 6 | 1 | 1 | 1 | 100.0 |
| v2 | IPC | top-k | 84 | 4 | 9 | 5 | 20 | 5 | 25.0 |
| v2 | IPC | threshold | 84 | 5 | 8 | 3 | 22 | 3 | 13.6 |
| v2 | BNS | top-k | 81 | 8 | 8 | 0 | 2 | 0 | 0.0 |
| v2 | BNS | threshold | 81 | 5 | 5 | 0 | 3 | 0 | 0.0 |

All eight cells together: 12 charges newly found by 74 added predictions, of which 12 (16.2 %) are correct.
Cells where links v1 finds no more charges than the baseline: 2 of 8. A stricter reading of the rule, where every cell must rise, would change the verdict if this count is above zero.
