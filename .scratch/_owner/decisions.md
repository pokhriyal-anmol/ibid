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
