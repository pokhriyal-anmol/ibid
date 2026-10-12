# Define the multi-charge test set file and refuse any file that breaks its rules

Status: ready-for-agent
Blocked by: none

What to build: the file format for the multi-charge test set, a validator command, and a hash pin, tested on an invented fixture set. Everything else in slice 3 reads this file, so the format and its refusals come first. No real queries are collected by this ticket (ticket 03 does that).

One item is one query. Fields:

- `id`: string, unique in the file.
- `query`: the raw text a user would type, non-empty. It is passed to retrieval unchanged (ADR 0001).
- `author_type`: who produced the query text. One of `lawyer`, `owner`, `judgment-excerpt`. Any other value, including `model`, is refused, so queries written by an assistant cannot enter.
- `source`: where the text came from, non-empty. For a `judgment-excerpt` it names the dataset and the case id there, so the text can be traced and its licence checked.
- `anonymised`: must be `true`.
- `charges`: a non-empty list. Each charge has `charge` (a short free-text name, for example "murder") and `sections`, an object with two lists, `ipc` and `bns`, of citations the labeller accepts for that charge, for example `{"ipc": ["IPC 302"], "bns": ["BNS 103"]}`. A charge counts as found in an Act when any one accepted section of that Act is found. An empty list for an Act means the labeller found no counterpart in that Act, and that charge is left out of that Act's score and counted separately. At least one of the two lists is non-empty.
- `label_basis`: how the section labels were made. One of `lawyer`, `agent-drafted-skeptic-refuted`, `agent-checked-for-owner`. Any other value is refused.
- `reviewed_by`: a non-empty label for the reviewer (a role, initials or a skeptic pass id).

The file also carries `version`, `created`, `licence_note` and a `label_policy` sentence saying what `label_basis` values mean in this file. The pin is `<file>.sha256` beside it, as for the gold sets, and a versioned file is never edited in place.

Command: `ibid charges validate --set <file> --index <index>`. It exits non-zero and prints the item id and the field for every violation, and it checks that every cited section exists in the index (resolved with the existing `index.lookup`), that `ipc` citations are IPC and `bns` citations are BNS. With a valid file it prints the item count, the charges per item histogram (1, 2, 3 or more), the number of distinct sections per Act, and the count of items per `label_basis`.

User stories: 1, 2, 3.

Acceptance criteria (invented fixture files only, never real case text):
- A valid fixture of 6 items passes and prints the histogram and the `label_basis` counts the fixture has by construction.
- Known-bad fixtures each fail and name the item and the field: `author_type` of `model`, a missing `author_type`, `anonymised` false, an empty `charges` list, a charge with no sections in either Act, a section that is not in the index, an IPC citation in the `bns` list, a duplicate `id`, an empty `query`, a missing `source`, a `label_basis` outside the three values, a missing `reviewed_by`.
- A charge with an empty `bns` list and a non-empty `ipc` list is valid.
- A changed byte in a valid fixture makes `validate` refuse it with a pin mismatch, and a missing pin file is refused.
- A validated file is not rewritten by the command.
- `validate` works on a path outside the repository.
- No real query text, and nothing under `data/raw/`, is added to git by this ticket.
- The new tests pass in the full suite, and each known-bad case was seen failing once against code that skips that check.
