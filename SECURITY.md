# Security and data handling

## Reporting a problem

This repository is private. Report anything sensitive to the repository owner directly, not in an issue.

## What is sensitive here

- **Source texts.** The IPC and BNS PDFs are not in the repo and must not be committed. Their reuse terms are not confirmed. CI fails if a PDF or anything under `data/raw/` is tracked.
- **Provision text in data files.** `gold/` and `concordance/` hold verbatim excerpts of the Acts. This is the reason the repo is private. Do not make it public, or copy those files elsewhere, until the reuse terms are confirmed.
- **Credentials.** There are none in the project. Do not add any. Secrets belong in environment variables, never in source.

## Supply chain

The package has no runtime dependencies. Adding one needs a maintenance and license check first ([ADR 0002](docs/adr/0002-python-and-sqlite.md)).
