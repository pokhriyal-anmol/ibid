# ADR 0006: the association layer may be fitted on the ILSIC-Lay train split

Status: done
Blocked by: none

What to build: `docs/adr/0006-association-layer-fitted-on-layperson-text.md`, in the shape of ADRs 0001 to 0005. It widens only ADR 0005's "from which data" clause: `assoc-nb v2` is fitted on the ILSIC-Lay train split (`data/raw/ilsic/FT-Layman-train.jsonl.xz`, 6,465 posts, SHA-256 `6f998e08...` as in `data/SOURCES.md`) and nothing else (no ILSI text, no Layman test split, no dev split). It records the CC BY-NC-SA 4.0 non-commercial, share-alike licence and that the fitted model file is therefore gitignored and never leaves the private repository. It states that everything else in ADR 0005 stands: opt-in, never in the baseline, no model call, tokenisation (ADR 0004), smoothing and k unchanged, scored once per set by the one scorer. Add a one-line pointer from ADR 0005 to 0006 only if ADR 0005 already has a superseded/amended convention; otherwise leave 0005 untouched.

User stories: 8 (the ADR part).

Acceptance criteria:
- The ADR file exists, names the train split by path and hash, states the licence, and lists which ADR 0005 clauses are unchanged.
- No file under `src/`, `gold/`, `concordance/` or `results/` changes in this ticket (`git diff --stat` shows docs only).
- Prose follows the repo's vocabulary (Act, Provision, Citation, Concordance, Baseline) from CONTEXT.md.
