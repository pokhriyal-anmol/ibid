# Map the 100 benchmark labels to IPC citations and check each exists in the index

Status: ready-for-agent
Blocked by: none

What to build: a deterministic mapping from a LeSICiN label string (`Section N in The Indian Penal Code`) to an IPC citation (`IPC N`), and a command (for example `ibid bench check-labels --data data/raw/lesicin/label_vocab.json --index <index>`) that reports, for each of the 100 labels, whether its citation is a provision in Ibid's IPC section tree. Exit non-zero and list every missing or unparseable label. This is the first check the spec names under Data.

User stories: 4 (prerequisite for roll-up to section labels), 1 (reads the label vocabulary from the local, gitignored path).

Acceptance criteria:
- On the real `label_vocab.json`, the command prints 100 mapped labels and either 0 missing, or the missing list is recorded in the slice notes as a finding for the owner.
- A test on an invented fixture vocabulary containing one label whose section is absent from a tiny fixture index exits non-zero and names that label (known-bad).
- A label string in an unexpected shape is reported as unparseable, never silently dropped.
- No file under `data/raw/` is added to git.
