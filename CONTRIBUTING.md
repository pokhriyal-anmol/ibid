# Contributing

Thanks for helping. This is a small project with strict rules about evidence. The rules exist so a score means something.

## Set up

```bash
uv sync
```

Fetch the two source PDFs listed in [data/SOURCES.md](data/SOURCES.md) into `data/raw/` and check their hashes. They are never committed. Then follow the Quickstart in the [README](README.md).

## How work is organised

Specs and tickets are local markdown under `.scratch/<slice>/`, one ticket per file, with a `Status:` line (`needs-triage`, `ready-for-agent`, `ready-for-human`, `done`, `wontfix`). See [docs/agents/issue-tracker.md](docs/agents/issue-tracker.md). GitHub Issues are for external reports and data corrections.

## Making a change

1. Read [CONTEXT.md](CONTEXT.md) and the [ADRs](docs/adr/). Use the project's words.
2. Write the test first, through the `ibid eval` command, and watch it fail against known-bad input.
3. Keep the change small. Do not add dependencies without discussing it.
4. Run `uv run python -m unittest discover -s tests`.
5. Commit with a Conventional Commit message (`feat(parse): ...`, `fix: ...`, `docs: ...`).
6. Open a pull request using the template.

## Changing the gold set or the concordance

These are data, and the rules are stricter than for code.

- Never edit `gold/v1.json` or its pin in place. Add a new version and a new pin.
- Every item needs a PDF page citation of the pinned source file.
- Do not change an answer to make the system pass. If the system is wrong, fix the system. If the item is wrong, drop or correct it with a reason that someone can check at the source.
- A concordance entry is `verified: true` only after a person has looked at the source pages, and its `basis` says who.

## What will be declined

- Anything that puts a model in the retrieval path ([ADR 0001](docs/adr/0001-retrieval-independent-of-the-model.md)).
- Committing the source PDFs.
- Quality claims without a frozen gold set behind them.
