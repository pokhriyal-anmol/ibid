# Learned mode refuses a missing or wrong model, an unknown mode, and reports clamped limit and ignored adjacent

Status: done
Blocked by: 01

## What to build
Error and argument handling for `search` learned mode, as tool errors (`isError`) that leave the server running:
- model file absent or unreadable: a tool error naming the path and the fit command (`ibid assoc fit --source union ...` as used for v3);
- model header whose layer is not `assoc-nb` or whose version is not `v3`: a tool error naming both the found and the expected layer and version;
- `mode` other than `keyword` or `learned`: a tool error naming the two valid values;
- `limit` above 5 in learned mode: clamped to 5, with a note in the result saying it was clamped;
- `adjacent` in learned mode: ignored, with a note saying so.

## User stories
6, 7, 8.

## Acceptance criteria
- [ ] Over the stdio harness, `mode: "learned"` with the model path absent returns a tool error containing the path and the fit command, and the next `keyword` call on the same server returns the normal result.
- [ ] A copy of the invented fixture model with its header changed to another layer, and one with another version, are each refused with an error naming both the found and expected values.
- [ ] A model file with invalid JSON returns a tool error, not a crash.
- [ ] `mode: "other"` returns a tool error containing `keyword` and `learned`.
- [ ] `mode: "learned", limit: 50` returns 5 hits and a clamp note; `limit: 3` returns 3 hits and no note.
- [ ] `mode: "learned", adjacent: true` returns the learned payload with no neighbour fields and an ignored note.
- [ ] Known-bad runs seen failing once: a wrong-version model accepted, a clamped limit not reported, a missing model killing the server process.
