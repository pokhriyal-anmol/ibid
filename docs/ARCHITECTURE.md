# Architecture

Ibid is a Python library with one command, `ibid`, over one SQLite file ([ADR 0002](adr/0002-python-and-sqlite.md)). Everything is deterministic: the same sources and the same query give the same bytes.

## Data flow

```mermaid
flowchart TB
  subgraph Sources["Sources, outside git"]
    BNS[("BNS gazette PDF, 102 pages")]
    IPC[("IPC WIPO PDF, 119 pages")]
  end

  subgraph Parse["Parsing"]
    PB["parse.py: layout-aware BNS parser"]
    PI["ipc.py: IPC parser"]
    ST["Section trees: Provision(citation, text, parent, children)"]
  end

  subgraph Store["One rebuildable SQLite file"]
    PR[("provision")]
    FT[("fts: keyword search")]
    XR[("xref: resolved and unresolved references")]
  end

  subgraph Serve["Answering"]
    LK["index.lookup: text, children, reference chain"]
    SE["index.search: ranked, ties broken by citation"]
    CO["concordance.lookup: verified entries only"]
  end

  subgraph Measure["Measuring"]
    GO[("gold/v1.json plus pin")]
    EV["ibid eval: score by category"]
    RS[("results file: gold hash, parser version, outcomes")]
  end

  BNS -->|"pdftotext bounding boxes"| PB
  IPC -->|"pdftohtml xml"| PI
  PB --> ST
  PI --> ST
  ST -->|"xref.extract resolves references by rule"| XR
  ST --> PR
  ST --> FT
  PR --> LK
  XR --> LK
  FT --> SE
  CO -->|"validated against the index"| EV
  LK --> EV
  SE --> EV
  GO -->|"hash must match the pin"| EV
  EV --> RS

  classDef src fill:#eef,stroke:#446
  classDef code fill:#e3f5e3,stroke:#272
  classDef data fill:#fff4d6,stroke:#a60
  class BNS,IPC src
  class PB,PI,ST,LK,SE,CO,EV code
  class PR,FT,XR,GO,RS data
```

## Modules

| Module | Responsibility |
|---|---|
| `parse.py` | BNS parser, the `Provision` shape, `BNS_TOTAL`, `PARSER_VERSION` |
| `ipc.py` | IPC parser, `IPC_TOTAL`, strips amendment marks and footnote numerals |
| `xref.py` | Finds cross-references by regex, resolves them within one Act, builds per-provision chains |
| `index.py` | Builds the SQLite file, `lookup`, `search`, reference counts |
| `concordance.py` | Loads a concordance file, validates every citation against the index, two-way lookup |
| `cli.py` | `ibid eval`, plus `conform` and `freeze` entry points |
| `conform.py` | Applies the text conventions to drafted gold, with guards |
| `freeze.py` | Applies the review sheet, writes the pinned gold and the concordance |

## Invariants

- **Section counts are exact.** `eval` stops if either Act does not recover its known total.
- **Order is total.** Search ties break by citation, so a result is a fixed sequence.
- **Frozen means frozen.** Scored mode compares the gold file to its pin before parsing anything.
- **Unverified is not served.** A concordance entry with `verified: false` answers "no verified concordance".

## Decisions

See [docs/adr/](adr/) and the vocabulary in [CONTEXT.md](../CONTEXT.md).
