@AGENTS.md

## Agent skills

### Issue tracker

Issues and specs live as local markdown under `.scratch/<feature>/`. See `docs/agents/issue-tracker.md`.

### Triage labels

Default five-role vocabulary (needs-triage, needs-info, ready-for-agent, ready-for-human, wontfix), recorded as a `Status:` line in each issue file. See `docs/agents/triage-labels.md`.

### Domain docs

Single-context: one `CONTEXT.md` and `docs/adr/` at the repo root. See `docs/agents/domain.md`.

## Tests

The tests are `unittest`, not pytest. They read the gitignored source PDFs from `IBID_BNS_PDF` and `IBID_IPC_PDF` if set, and otherwise from the main checkout's `data/raw/` (found through `git rev-parse --git-common-dir`, so a git worktree works with no setup).

```bash
uv run python -m unittest discover -s tests
```

The run takes about 15 seconds.
