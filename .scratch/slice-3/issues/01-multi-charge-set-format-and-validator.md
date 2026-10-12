# Define the multi-charge test set file and refuse any file that breaks its rules

Status: needs-triage
Blocked by: none

What to build: the file format for the multi-charge test set, a validator command, and a hash pin, tested on an invented fixture set. Everything else in slice 3 reads this file, so the format and its refusals come first. No real queries are collected by this ticket. Real queries come from people (ticket 03).

One item is one query. Fields:

- `id`: string, unique in the file.
- `query`: the raw text a user would type, non-empty. It is passed to retrieval unchanged (ADR 0001).
- `author_type`: one of `lawyer`, `owner`, `judgment-excerpt`. Any other value, including `model`, is refused, so queries written by an assistant cannot enter.
- `author`: a short non-empty label for who wrote or chose it (a role or initials, not a name).
- `anonymised`: must be `true`. The collector confirms that names, places, dates and identifiers are removed.
- `charges`: a non-empty list. Each charge has `charge` (a short free-text name, for example "murder") and `sections`, a non-empty list of citations that a lawyer accepts for that charge, for example `["IPC 302"]`. A charge with several accepted sections counts as found when any one of them is.
- `reviewed_by`: a non-empty label for the second person who checked the labels.

The file also carries `version` and `created`. The pin is `<file>.sha256` beside it, as for the gold sets, and a versioned file is never edited in place.

Command: `ibid charges validate --set <file> --index <index>`. It exits non-zero and prints the item id and the field for every violation, and it also checks that every cited section exists in the index (IPC or BNS, resolved with the existing `index.lookup`). With a valid file it prints the item count, the charges per item histogram (1, 2, 3 or more) and the number of distinct sections.

User stories: 1, 2, 3.

Acceptance criteria (invented fixture files only, never real case text):
- A valid fixture of 6 items passes and prints the histogram the fixture has by construction.
- Known-bad fixtures each fail and name the item and the field: `author_type` of `model`, a missing `author_type`, `anonymised` false, an empty `charges` list, a charge with no sections, a section that is not in the index, a duplicate `id`, an empty `query`, a missing `reviewed_by`.
- A changed byte in a valid fixture makes `validate` refuse it with a pin mismatch, and a missing pin file is refused.
- A validated file is not rewritten by the command.
- `validate` works on a path outside the repository, so the owner can keep real data out of git.
- No real query text, and nothing under `data/raw/`, is added to git.
- The new tests pass in the full suite, and each known-bad case was seen failing once against code that skips that check.
