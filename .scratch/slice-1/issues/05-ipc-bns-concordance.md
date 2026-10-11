# Concordance loader and lookup in both directions

Status: done
Blocked by: 02, 03

## What to build
The code half of the concordance. A concordance file format and a loader that validates every citation in it against the index, plus lookup in both directions. Each entry has a type: one-to-one, split, merged, removed or new (see CONTEXT.md). An IPC citation lookup returns its concordant BNS provisions with the type, and a BNS citation returns its concordant IPC provisions with the type. A citation with no verified entry answers "no verified concordance", never a guess. Only entries marked `verified: true` are served.

Test on a small hand-written fixture of about 4 entries (one of each of one-to-one, split, merged, removed, and one new). The real entries are ticket 09, not this ticket. Do not invent legal correspondences.

## User stories
11, 12, 13

## Acceptance criteria
- [ ] Through `ibid eval`, an IPC-to-BNS item and a BNS-to-IPC item each return the expected provisions and mapping type on the fixture.
- [ ] Split, merged, removed and new cases are each represented by at least one fixture entry and return correctly.
- [ ] A citation with no verified entry returns "no verified concordance".
- [ ] An entry with `verified: false` is not served.
- [ ] The loader fails the run if any entry names a citation absent from the index. Seen failing once with a bad entry.
- [ ] Correspondence items are reported as their own category in the results file.
- [ ] Results stay byte-identical across two runs.
