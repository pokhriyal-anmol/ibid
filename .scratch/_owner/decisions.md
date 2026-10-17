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
