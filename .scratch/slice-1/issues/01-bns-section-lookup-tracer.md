# Tracer bullet: BNS section lookup through the evaluation command

Status: done
Blocked by: none

## What to build
The thinnest end-to-end path through the one test seam. Set up the `uv` Python project (ADR 0002) with an `ibid eval` command. It parses the BNS Gazette PDF (PRS copy) at section level into the shared section tree shape (canonical citation, verbatim English text, parent and child addresses), drops the legacy-font Hindi text, builds the SQLite index as one rebuildable file, answers section-lookup items from a gold-set file, scores exact match per category, and writes a results file that carries the gold-set hash and the parser version. The parser is layout-aware and reports recovered sections against the known total of 358. Act source texts live outside git (gitignored, path configured), since their reuse terms are unconfirmed. Use a small draft gold file (a handful of section-lookup items) here; the real gold set comes in ticket 7. No model is called.

## User stories
1, 4, 5, 6, 9, 15, 18, 19, 20

## Acceptance criteria
- [ ] `ibid eval` takes a gold-set file and the source texts and writes a results file; nothing else is needed to run it.
- [ ] The parser reports `BNS: 358/358` sections recovered. Seen failing once: with a truncated or altered source the count drops and the command exits non-zero.
- [ ] Looking up a citation such as `BNS 103` returns the verbatim English gazette text; no non-English or garbage characters appear in any indexed provision.
- [ ] Every provision has exactly one canonical citation string, and citation equality is a byte comparison.
- [ ] The results file holds per-question outcomes, per-category exact-match counts, the gold-set file hash and the parser version.
- [ ] Two consecutive runs produce byte-identical results files. Seen failing once: an injected nondeterminism (for example a timestamp) makes the comparison fail.
- [ ] Act source texts are not tracked by git.
