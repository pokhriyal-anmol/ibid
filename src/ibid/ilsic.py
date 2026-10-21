"""Slice 14 ticket 01: `ibid ilsic eval`, the frozen rule scored on an ILSIC split under the paper's label space and under its own vocabulary."""
import json
import re
import sqlite3
import sys
from pathlib import Path

from ibid import bench, bm25
from ibid.assoc import _rows
from ibid.parse import PARSER_VERSION

IPC_LABEL = re.compile(r"Section (\d+[A-Z]{0,2}) of The Indian Penal Code, 1860")
ASSUMPTION = ("Label space is every statute string in the Lay train and test answers. A gold label no layer can predict counts as a miss. "
              "Macro scores average over the whole space, a label with no gold and no prediction scoring 0; this is our reading, the paper does not state its own.")


def _reading(gold: list[set[str]], pred: list[set[str]], space: set[str]) -> dict:
    counts = list(bench.label_counts(gold, pred, space).values())
    prec = [tp / (tp + fp) if tp else 0.0 for tp, fp, _ in counts]
    rec = [tp / (tp + fn) if tp else 0.0 for tp, _, fn in counts]
    s = bench.score(gold, pred, space)
    return {"labels": len(space), "macro_f1": s["macro_f1"], "micro_f1": s["micro_f1"],
            "macro_precision": round(sum(prec) / len(space), 6), "macro_recall": round(sum(rec) / len(space), 6)}


def evaluate(split_path: str, train_path: str, index_path: str, frozen_path: str, out_path: str) -> int:
    """Score the frozen rule's threshold output on the raw `instruction` of every row; no model, no network (ADR 0001)."""
    try:
        frozen = json.loads(Path(frozen_path).read_text())
        k, r, rollup, knobs = frozen["k"], frozen["r"], frozen["section_score"], bench.knobs_of(frozen.get("knobs"))
        if frozen["rule"]["params_sha256"] != bench.rule_hash(k, r, rollup, frozen["stop_words"], knobs):
            raise ValueError(f"{frozen_path} does not hold the rule it names")
        rows = _rows(split_path)
        space = {a for row in _rows(train_path) + rows for a in row["answer"]}
        if not rows or not space:
            raise ValueError("empty split or empty label space")
        db = sqlite3.connect(f"file:{index_path}?mode=ro", uri=True)
        ix = bm25.Index(db, knobs["levels"], knobs["stem"])
    except (OSError, KeyError, ValueError, sqlite3.Error) as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    cite = {label: f"IPC {m[1]}" for label in space if (m := IPC_LABEL.fullmatch(label))}
    vocab = {label for label, c in cite.items() if c in ix.parent}  # what the rule can predict
    back = {cite[label]: label for label in vocab}
    pred = [{back[c] for c in bench.predict(bench.rank_sections(ix, row["instruction"], set(back), rollup, frozen["stop_words"], knobs), k, r)[1]}
            for row in rows]
    gold = [set(row["answer"]) for row in rows]
    res = {"layer": "frozen-rule", "version": frozen["rule"]["version"], "rule_params_sha256": frozen["rule"]["params_sha256"],
           "output_rule": "threshold", "parser_version": PARSER_VERSION, "split_sha256": bench.sha256(split_path),
           "train_sha256": bench.sha256(train_path), "queries": len(rows), "label_space": len(space), "assumption": ASSUMPTION,
           "primary": _reading(gold, pred, space), "secondary_vocabulary": _reading(gold, pred, vocab)}
    text = json.dumps(res, indent=2, sort_keys=True) + "\n"
    Path(out_path).write_text(text)
    print(text, end="")
    return 0
