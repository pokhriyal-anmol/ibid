# `results/layer-comparison.md` shows baseline, v1, v2 and v3 side by side

Status: done
Blocked by: 03, 04

What to build: regenerate `results/layer-comparison.md` with `ibid charges compare`, passing the baseline, assoc-nb v1, v2 and v3 results for sets v1 and v2 and the ILSI test results for v1 and v3. Change `src/ibid/compare.py` only if it cannot already show a v3 row. Keep the set v2 label-incompleteness caveat.

User stories: 5, 7.

Acceptance criteria:
- A test drives `ibid charges compare` with invented results files for four layers and asserts one row per layer per set and Act, and the set v2 caveat line.
- The regenerated report's baseline, v1 and v2 rows match the previous version of the file exactly; only v3 rows (and any v3 ILSI line) are added.
- No other results file changes.
