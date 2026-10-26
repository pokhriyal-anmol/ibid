# Ibid

[![CI](../../actions/workflows/ci.yml/badge.svg)](../../actions/workflows/ci.yml)
![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue)
![Model calls: none](https://img.shields.io/badge/model%20calls-none-brightgreen)

A local, deterministic retrieval engine for Indian criminal statute (the IPC and the BNS) that returns **verbatim text and exact citations**. The language model is replaceable. The evidence is not.

Ask for `BNS 103(1)` and you get that provision's text, byte for byte, the provisions it refers to, and the IPC provision it replaced. Ask the same question twice, or through a different model, and the evidence is identical.

## How it works

```mermaid
flowchart LR
  subgraph User["Asker"]
    Q["Raw query, exactly as typed"]
  end

  subgraph Ibid["Ibid (code only, no model)"]
    P["Parse both Acts into section trees"]
    I[("SQLite index: provisions, keyword search, cross-references")]
    C["Concordance: IPC to BNS and back"]
    E["Evidence packet: verbatim provisions plus citations"]
  end

  subgraph Model["Any language model (optional, replaceable)"]
    N["Narration around the packet"]
  end

  Q -->|"only input to retrieval"| E
  P -->|"builds"| I
  I -->|"lookup and search"| E
  C -->|"verified mappings only"| E
  E -->|"byte-identical for every model"| N
  N -.->|"a citation outside the packet is flagged"| E

  classDef code fill:#e3f5e3,stroke:#272
  classDef store fill:#eef,stroke:#446
  classDef optional fill:#fff4d6,stroke:#a60
  class P,E,C code
  class I store
  class N optional
```

Retrieval depends only on the raw query ([ADR 0001](docs/adr/0001-retrieval-independent-of-the-model.md)). No model rewrites the query, picks sections or expands references.

## Status

| Slice | What it delivers | State |
|---|---|---|
| 1 | Parse both Acts, resolve cross-references, score a frozen gold set, byte-identical results | Done |
| 2 | Public statute-identification benchmark (ILSI), frozen rule v2.11 | Done |
| 3 | Multi-charge sets and layers: cited sections, learned association, sub-queries. Concordance v3 from a published table | Done |
| 4 | `ibid mcp`, a stdio MCP server over the deterministic lookups | Done |
| 5 | MCP gaps from a real client: concordance fallback to the section, optional direction, adjacent sections in search | Done |
| 6 | Association layer v2 fitted on layperson text | Done |
| 7 | Definition-punishment links from headings, expanded after ranking | Done, result negative under the pre-registered rule (ADR 0007) |
| 8 | Real BNS section headings in the MCP server | Done |
| 9 | One association layer (`assoc-nb v3`) fitted on judgments and forum posts | Done, kept as opt-in by owner waiver (ADR 0008) |

What slice 1 measured on 2026-10-11:

| Measure | Value |
|---|---|
| BNS sections recovered | 358 of 358 |
| IPC sections recovered | 575 of 575 |
| Gold set | 45 items (version 2), pinned by SHA-256. Version 1 is kept for history |
| Concordance | 66 entries. 12 are served as verified (8 human-checked, 4 agent-checked at the owner's request). The other 54 answer "no verified concordance" |
| Baseline score | 45 of 45 |
| Two scored runs | byte-identical |

What slices 2 and 3 measured on 2026-10-13 (details in [results/layer-comparison.md](results/layer-comparison.md) and [results/multicharge-v2-report.md](results/multicharge-v2-report.md)):

| Measure | Baseline (model-free) | Learned association layer |
|---|---|---|
| ILSI test, micro-F1 over 100 labels | 9.6% | 35.4% |
| Layperson forum posts (set v2), IPC charges found | 4.8% to 6.0% of 84 | 39.3% |
| Layperson forum posts (set v2), BNS charges found | 6.2% to 9.9% of 81 | 48.1% |

These are measurements, not claims. The forum labels are extracted from lawyers' replies and are incomplete, so recall is meaningful and precision is not. The association layer is opt-in (ADR 0005), was fitted on the same corpus family, and its figures flatter it. Concordance v3 serves 348 entries from a published table, up from 12, and no lawyer has reviewed any label or mapping.

The 45 of 45 is a ceiling, not a quality claim. The gold set is small and its conventions were settled with the system in view. Its job is to prove the harness works and can fail. Later layers (embeddings, graph) must beat this baseline on a harder set to stay.

## Quickstart

You need [uv](https://docs.astral.sh/uv/) and poppler (`pdftotext`, `pdftohtml`, `pdfseparate`, `pdfunite`). The source PDFs are not in the repo. `ibid setup` downloads and checks them for you.

```bash
uv sync
uv run ibid setup --fetch bns
```

The IPC PDF comes from WIPO, whose download link is signed and expires, so a script cannot fetch it alone. Open the WIPO Lex page listed in [data/SOURCES.md](data/SOURCES.md), copy the PDF link, and pass it to setup:

```bash
uv run ibid setup --fetch ipc --url <link>
uv run ibid setup
```

The last command checks the tools and both PDFs, parses both Acts, prints the section counts and prints the `claude mcp add` line for this machine.

```bash
# Run the frozen evaluation (scored mode refuses a gold file that fails its pin)
uv run ibid eval --gold gold/v2.json --concordance concordance/v2.json --out results/run.json

# Run the test suite (about 30 seconds)
uv run python -m unittest discover -s tests
```

`results/run.json` should be byte-identical to [results/baseline-v2.json](results/baseline-v2.json).

## Learned mode (research option)

`search` has an opt-in `mode: "learned"` that uses the `assoc-nb v3` model in `data/assoc-nb-v3.json`. It is not part of the standard install and `ibid setup` only reports whether the file exists. You make it yourself with `ibid assoc fit --source union` (flags in `ibid assoc fit --help`; see [ADR 0008](docs/adr/0008-association-layer-fitted-on-both-kinds-of-text.md)). The training data, ILSI and ILSIC-Lay, are gated and licensed non-commercial, so the model is gitignored and cannot be redistributed. Keyword mode stays the default and needs none of this.

## How we know it works

- **A frozen answer key.** [gold/v2.json](gold/v2.json) carries its SHA-256 in [gold/v2.sha256](gold/v2.sha256). One changed byte and scored mode refuses to run. Edits make a new version.
- **Independent of the system.** Gold answers were drafted from the PDF page text, never from the index, and each cites its page. A second pass tried to refute every item.
- **The harness can fail.** A scrambled section lowers its category, a wrong concordance mapping lowers its category, and swapped source pages refuse to score. See [tests/test_baseline.py](tests/test_baseline.py).
- **Provenance in the data.** Every concordance entry carries a `basis`: `human-checked`, `agent-checked-for-owner`, `source-table-checked` or `refuted-by-agent`. Only the first three are served.

## Repository map

| Path | What is there |
|---|---|
| `src/ibid/` | Parsers, index, cross-references, concordance, the `ibid` command |
| `gold/`, `concordance/` | Frozen v1 and v2 data with pins and review records, plus drafts |
| `results/` | The committed baseline |
| `tests/` | Tests, all through the `ibid eval` command |
| `docs/adr/` | Decisions and why |
| `docs/ARCHITECTURE.md` | Modules and data flow |
| `CONTEXT.md` | The project vocabulary (Act, Provision, Citation, Concordance, ...) |
| `.scratch/` | Specs and tickets, as local markdown |
| `AGENTS.md` | Start here if you are an AI agent |

## Limits

- The IPC text is the WIPO Lex copy consolidated to Act 34 of 2019, not the 1860 original.
- Concordance is a legal judgement. Treat the output as a research aid, not legal advice, and have a lawyer review correspondence before relying on it or publishing a score.
- Set v2 holds forum posts from ILSIC-Lay (CC BY-NC-SA 4.0, non-commercial) with a partial scrub of personal names. It must stay in the private repository.
- The reuse terms of the source texts are not confirmed. The repository is private for that reason, and it holds provision text in its gold and concordance data.

## License

None chosen yet. All rights reserved until one is added.
