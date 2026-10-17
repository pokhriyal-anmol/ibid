# Use real headings for `adjacent` neighbours, keep the D-001 fallback

Status: done
Blocked by: 03

What to build
In `search` with `adjacent`, each `previous` and `next` neighbour's `heading` is the real section heading from the sidecar where one exists. Where the sidecar has null for that section, it falls back to the D-001 heading: the first line of the section text, cut at the first em dash, capped at 100 characters, as `index.neighbours` produces today (spec decision 4, owner decision D-001). The fallback applies in `adjacent` only, never in `get_provision` or a hit's own `heading`.

User stories: 6, and 7 for this change.

Acceptance criteria
- Through the stdio harness, a search whose hit is `BNS 84` (or any hit next to BNS 83 or 85) shows the neighbour's real heading, for example "Marriage ceremony fraudulently gone through without lawful marriage." for BNS 83, and not its truncated opening sentence.
- For a section the sidecar has no heading for, the neighbour shows the D-001 fallback text, not null. The test forces this case by giving the server a sidecar with that section's heading removed.
- Run once against known-bad input and seen to fail: the old behaviour (fallback everywhere) fails the real-heading assertion.
- The hit list and its order are unchanged. `ibid eval` still reproduces `results/baseline-v2.json` byte for byte and every pinned file's hash is unchanged.
- `uv run python -m unittest discover -s tests` passes.
