# Gold-set versioning and hash-pin enforcement

Status: done
Blocked by: 01

## What to build
The code half of the frozen gold set. A versioned gold-set file layout and a pin file holding the SHA-256 of the frozen version. `ibid eval` in scored mode refuses to run when the gold file's hash does not match the pin. A draft or unpinned file may still run in an explicit draft mode so existing tests keep working, and the results file states which mode it was. Later edits create a new version with a new pin, never an in-place edit.

The real gold items are ticket 10, not this ticket. Do not author legal answers here.

## User stories
17

## Acceptance criteria
- [ ] Scored mode refuses the run, with a non-zero exit and no results file, when one byte of the gold file changes. Seen failing once.
- [ ] Draft mode runs without a pin and the results file records `mode: draft`.
- [ ] The results file records the gold version and hash.
- [ ] Two consecutive runs in each mode are byte-identical.
- [ ] A new version can be added beside the old one without touching it.
