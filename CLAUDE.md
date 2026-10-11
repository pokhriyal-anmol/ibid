@AGENTS.md

## Agent skills

### Issue tracker

Issues and specs live as local markdown under `.scratch/<feature>/`. See `docs/agents/issue-tracker.md`.

### Triage labels

Default five-role vocabulary (needs-triage, needs-info, ready-for-agent, ready-for-human, wontfix), recorded as a `Status:` line in each issue file. See `docs/agents/triage-labels.md`.

### Domain docs

Single-context: one `CONTEXT.md` and `docs/adr/` at the repo root. See `docs/agents/domain.md`.

## Tests

The tests are `unittest`, not pytest, and read the source PDFs from two env vars. The PDFs are gitignored (see `data/SOURCES.md`), so a git worktree does not have them: point the vars at the root checkout's `data/raw/` by absolute path.

```bash
IBID_BNS_PDF=<root>/data/raw/bns-prs.pdf IBID_IPC_PDF=<root>/data/raw/ipc-wipo.pdf uv run python -m unittest discover -s tests
```

In the root checkout, `<root>` is `$PWD`. The run takes about 15 seconds.
