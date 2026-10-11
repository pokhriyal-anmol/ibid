## Summary

What changed and why, in a few sentences. Link the ticket under `.scratch/` if there is one.

## Test plan

- [ ] `uv run python -m unittest discover -s tests` passes
- [ ] New behaviour has a test through `ibid eval`
- [ ] Each new check was seen failing against known-bad input
- [ ] Scored run still matches `results/baseline-v1.json` (or the change is meant to move it, explained below)

## Data changes (delete if none)

- [ ] No frozen file was edited in place; a new version and a new pin were added
- [ ] Every new item cites a PDF page of the pinned source
- [ ] No answer was changed to make the system pass
- [ ] `concordance` entries record their `basis`

## Boundaries

- [ ] No model call added to the retrieval path
- [ ] No source PDF or `data/raw/` file committed
- [ ] No new dependency (or it was discussed)
