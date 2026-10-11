# IPC parsed into the same section tree

Status: done
Blocked by: 02

## What to build
A second parser for the WIPO Lex PDF copy of the IPC (`data/raw/ipc-wipo.pdf`) that emits the same section tree shape and citation format as the BNS, including sub-provisions. Both Acts live in the same index. The IPC source is a parsing source only (not committed) until its reuse terms are read. Add IPC lookup items to the draft gold file.

## User stories
2, 3, 4, 5, 6, 9

## Acceptance criteria
- [ ] The parser reports IPC sections recovered against the known IPC total and fails the command on a shortfall. Seen failing once against a source with a section removed.
- [ ] Through `ibid eval`, IPC citations (for example `IPC 302`, and an IPC subsection or exception) return verbatim English text.
- [ ] IPC and BNS provisions use one shared tree shape and citation format; an IPC and a BNS citation never collide.
- [ ] Results stay byte-identical across two runs.
