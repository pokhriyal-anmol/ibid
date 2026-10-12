# One comparison report across layers and sets

Status: needs-triage
Blocked by: 07, 08, 09

What to build: `ibid charges compare --results <file> ... --out results/layer-comparison.md`, which reads the results files of ticket 06's scorer for several layers and sets and writes one report. It is a table, and a short list of what each number is and is not, generated from the files and not typed.

Contents:

- One row per layer and set and Act: layer, layer version, set, set hash, Act, output, charges found of total, per-charge recall, all-charges-hit rate, mean predictions per item.
- The baseline (v2.11, top-k and threshold) is always the first rows. Every other layer's rows show the difference from the baseline's in points.
- Caveats generated from fields in the files, shown once per layer, not editable by hand: the label basis counts, whether the set's queries name their sections (the count is computed from the set by the same section-number pattern as `intake`), whether the layer used learned weights, whether a model produced an input, and how many scorings of that layer version exist.
- The ILSI results from slice 2 are included as a separate table for layer B, labelled as a different task.

User stories: 6, 7, 8.

Acceptance criteria:
- On fixture results for three layers and two sets the table values equal the files' values and the differences equal the hand-computed differences.
- Each caveat appears for exactly the layers it applies to (a layer with no learned weights has no learned-weights caveat), and a fixture with two scorings of one layer version shows both.
- Two runs on the same inputs are byte-identical.
- The report carries the set hashes, layer versions and input hashes of every row.
