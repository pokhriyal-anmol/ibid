# Owner decisions

Standing answers to questions the workflows could not settle. Newest last. Each entry: Decision, Applies when, Why, Source (owner-stated or proxy-inferred), Date. Only owner-stated entries are binding.

## D-001: A neighbour's heading is the opening of its text when a section has no title

Decision: Option 1. A BNS neighbour's heading in `search` with `adjacent` is the first line of the section text, cut at the first em dash, capped at 100 characters. Owner: "the default was the right pick".
Applies when: a tool must show a heading for a section whose source has no real title. Prefer showing a truncated opening over null, until real BNS headings are parsed.
Why: not stated.
Source: owner-stated
Date: 2026-10-16

## D-002: A decision rule must name its comparison level; beating the baseline is judged per set and Act

Decision: Option 2. When a layer is judged against the baseline, recall is compared per set and per Act, as `CONTEXT.md` defines it, and summed over output rules only. Pooling over Acts is not allowed.
Applies when: any pre-registered keep-or-drop rule for a layer. The spec states the level of comparison in the rule itself.
Why: the pooled reading was picked after scores existed.
Source: owner-stated
Date: 2026-10-17

## D-003: The association layer trains on both kinds of text

Decision: Option 2 of Q-002. Add court-judgment text (ILSI train) to the layperson posts (ILSIC-Lay train) for the next layer version, `assoc-nb v3`, fitted once by concatenating counts with no weighting.
Applies when: choosing training data for the association layer. A layer that must serve both layperson and judgment text is trained on both. Each new mix is a new layer version scored once.
Why: v1 suits judgments, v2 suits forum posts, and each fails on the other.
Source: owner-stated
Date: 2026-10-17

## D-004: A cross-check against a paraphrasing source is a tripwire, not a quality bar

Decision: The BNS-headings check against the CAPT table passes at 80% exact match, with every mismatch printed on each run.
Applies when: a test compares our output with an external source that paraphrases or has its own errors. The floor only has to separate correct from broken; a known-bad run (a shifted parse) must score far below it.
Why: the 90% bar was a guess made before measuring. The real rate is 83.9%, and the sampled misses are mostly CAPT's paraphrase.
Source: owner-stated
Date: 2026-10-17

## D-005: A pre-registered floor missed by 0.1 under the like-for-like reading is waived, openly

Decision: Q-005. Report the ILSI test micro-F1 over both label spaces and keep `assoc-nb v3` as an opt-in layer, although it is 0.1 below the 33.4 floor over v1's label space.
Applies when: a layer clears a pre-registered bar under one reading and misses it narrowly under the stricter one. The waiver is stated in the report and the ADR; the floor is never described as passed under the reading it failed.
Why: v3 beats the layer built for each kind of text on both multi-charge sets by wide margins.
Source: owner-stated
Date: 2026-10-18

## D-006: Slice 13 strategy signed; offline training allowed, test look spent only on a dev pass

Decision: The owner signed `.scratch/slice-13/strategy.md` ("it's sound, move ahead"). The two open choices in it were not answered separately, so they were taken at the recommended defaults: (1) the linear model may be trained offline with a throwaway `uv run --with` tool, shipping JSON weights, Ibid's runtime staying stdlib; (2) the single IL-TUR test look is spent only if the best frozen candidate clears 28.08 macro-F1 on dev, otherwise the dev result is reported and the slice stops.
Applies when: a learned-layer slice needs training that the standard library cannot do in reasonable time.
Why: pure-Python training is too slow at 42,750 documents; the runtime and ADR 0001 are unaffected.
Source: owner sign-off of the strategy, defaults mine (flag if wrong)
Date: 2026-10-22

## D-007: Slice 15 sources approved; the sources are treated as reusable, the compiled table stays out of git

Decision: The owner approved the three downloads for slice 15 and said the evidence suggests the sources are reusable. The BNSS Gazette and the BNSS to CrPC table are downloaded. The BNSS Gazette is a government publication. The table carries "© Anil Kishore Yadav, IPS, Director, CAPT Bhopal" on every page with no licence, so it is kept out of git and Ibid stores only section numbers and row references, as for the BNS table. The CrPC text is still to come.
Applies when: adding a source with an unstated licence. Keep the file out of git and store facts (numbers, references), not the compilation.
Why: it follows the owner's call without publishing a file that has an explicit copyright line.
Source: owner-stated (approval and reuse view); the handling of the table is mine (flag if wrong)
Date: 2026-10-22
