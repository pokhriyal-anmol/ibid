# Refuse to score data whose bytes differ from the pinned hashes

Status: needs-triage
Blocked by: 02

What to build: a committed manifest (no data, only names, byte counts and SHA-256 for `train.jsonl`, `dev.jsonl`, `test.jsonl`, `secs.jsonl`, `label_vocab.json`) and a check in the run command that refuses to score a file whose hash does not match its pinned entry, naming the file and both hashes. Fixtures use their own manifest.

User stories: 2, 1.

Acceptance criteria:
- Changing one byte of a fixture split makes the run command exit non-zero with a message naming the file (known-bad), and writes no results file.
- With unchanged data the run proceeds and the results file hashes equal the manifest's.
- The manifest for the real data is computed once from the files verified against the Zenodo MD5s on 2026-10-11, and the hashes are re-derived when committed, not copied from notes.
