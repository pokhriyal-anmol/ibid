"""Slice 14 ticket 01: `ibid ilsic eval`, the frozen rule scored on an ILSIC split under the paper's label space and under its own vocabulary."""
import json
import random
import sqlite3
import sys
from pathlib import Path

from ibid import assoc, bench, bm25
from ibid.assoc import _rows
from ibid.parse import PARSER_VERSION

ASSUMPTION = ("Label space is every statute string in the Lay train and test answers. A gold label no layer can predict counts as a miss. "
              "Macro scores average over the whole space, a label with no gold and no prediction scoring 0; this is our reading, the paper does not state its own.")

# Published bests, in percent, copied from the ILSIC paper (arXiv 2602.00881). Not re-run by us.
PUBLISHED = {
    "lay": [("macro_f1", 14.83, "GPT-4.1 two-shot", "Table 3"), ("micro_f1", 34.23, "GPT-4.1 two-shot", "Table 3"),
            ("micro_f1", 33.19, "fine-tuned Gemma-3", "Table 3")],
    "multi": [("macro_f1", 17.01, "GPT-4.1 zero-shot", "Table 5"), ("micro_f1", 33.95, "GPT-4.1 zero-shot", "Table 5")],
}
RESAMPLES = 1000


def _bootstrap(gold: list[set[str]], pred: list[set[str]], space: set[str]) -> dict:
    """95% percentile interval over test queries, seed 0, primary reading. Per-query counts are built once, so a resample is cheap."""
    per = [{c: (c in g and c in p, c in p and c not in g, c in g and c not in p) for c in g | p} for g, p in zip(gold, pred)]
    rng, out = random.Random(0), {"macro_f1": [], "micro_f1": []}
    for _ in range(RESAMPLES):
        tot: dict[str, list[int]] = {}
        for i in rng.choices(range(len(per)), k=len(per)):
            for c, v in per[i].items():
                t = tot.setdefault(c, [0, 0, 0])
                for j in range(3):
                    t[j] += v[j]
        out["macro_f1"].append(sum(bench.f1(*t) for t in tot.values()) / len(space))
        out["micro_f1"].append(bench.f1(*(sum(col) for col in zip(*tot.values()))))
    lo, hi = int(RESAMPLES * 0.025), int(RESAMPLES * 0.975) - 1
    return {k: [round(sorted(v)[lo], 6), round(sorted(v)[hi], 6)] for k, v in out.items()}


def _verdicts(primary: dict, benchmark: str) -> list[str]:
    """Above or below each published number, primary reading only."""
    return [f"{m} {primary[m] * 100:.2f}: {'above' if primary[m] * 100 > v else 'below'} {v:.2f} ({who}, {tab}; published, not re-run by us)"
            for m, v, who, tab in PUBLISHED[benchmark]]


def _reading(gold: list[set[str]], pred: list[set[str]], space: set[str]) -> dict:
    counts = list(bench.label_counts(gold, pred, space).values())
    prec = [tp / (tp + fp) if tp else 0.0 for tp, fp, _ in counts]
    rec = [tp / (tp + fn) if tp else 0.0 for tp, _, fn in counts]
    s = bench.score(gold, pred, space)
    return {"labels": len(space), "macro_f1": s["macro_f1"], "micro_f1": s["micro_f1"],
            "macro_precision": round(sum(prec) / len(space), 6), "macro_recall": round(sum(rec) / len(space), 6)}


def _frozen(frozen_path: str, index_path: str, rows: list[dict], cite: dict[str, str]) -> tuple[dict, list[set[str]], set[str]]:
    frozen = json.loads(Path(frozen_path).read_text())
    k, r, rollup, knobs = frozen["k"], frozen["r"], frozen["section_score"], bench.knobs_of(frozen.get("knobs"))
    if frozen["rule"]["params_sha256"] != bench.rule_hash(k, r, rollup, frozen["stop_words"], knobs):
        raise ValueError(f"{frozen_path} does not hold the rule it names")
    db = sqlite3.connect(f"file:{index_path}?mode=ro", uri=True)
    ix = bm25.Index(db, knobs["levels"], knobs["stem"])
    vocab = {label for label, c in cite.items() if c in ix.parent}  # what the rule can predict
    back = {cite[label]: label for label in vocab}
    pred = [{back[c] for c in bench.predict(bench.rank_sections(ix, row["instruction"], set(back), rollup, frozen["stop_words"], knobs), k, r)[1]}
            for row in rows]
    return {"layer": "frozen-rule", "version": frozen["rule"]["version"], "rule_params_sha256": frozen["rule"]["params_sha256"],
            "output_rule": "threshold"}, pred, vocab


def _model(model_path: str, expect: tuple[str, str], rows: list[dict], cite: dict[str, str]) -> tuple[dict, list[set[str]], set[str]]:
    model = assoc.open_model(model_path)  # offline prediction only (ADR 0005, 0009); nothing is refit
    got = (model.header.get("layer", assoc.LAYER), model.header["layer_version"])
    if got != expect:
        raise ValueError(f"{model_path} is {got[0]} {got[1]}, not the expected {expect[0]} {expect[1]}")
    vocab = {label for label, c in cite.items() if c in set(model.labels)}
    back = {cite[label]: label for label in vocab}
    pred = [{back[c] for c in model.predict(row["instruction"]) if c in back} for row in rows]
    return {"layer": got[0], "version": got[1], "model_sha256": model.sha256}, pred, vocab


def evaluate(split_path: str, train_path: str, index_path: str, frozen_path: str, out_path: str,
             model_path: str | None = None, expect: tuple[str, str] = ("", ""), ledger_path: str = "results/test-ledger-ilsic.json",
             rescore: bool = False, benchmark: str = "lay", space_from: str | None = None) -> int:
    """Score the frozen rule, or a model file, on the raw `instruction` of every row; no query rewrite, no network (ADR 0001)."""
    try:
        rows = _rows(split_path)
        # the spec's space is Lay train + Lay test answers: pass the Lay test as space_from when scoring the Multi test
        space = {a for row in _rows(train_path) + (_rows(space_from) if space_from else rows) for a in row["answer"]}
        if not rows or not space:
            raise ValueError("empty split or empty label space")
        cite = {label: f"IPC {m[1]}" for label in space if (m := assoc.IPC_CITE.fullmatch(label))}
        who, pred, vocab = (_model(model_path, expect, rows, cite) if model_path
                            else _frozen(frozen_path, index_path, rows, cite))
        prior = [e for e in bench.read_ledger(ledger_path)
                 if (e["split_sha256"], e["layer"], e["version"]) == (bench.sha256(split_path), who["layer"], who["version"])]
        if prior and not rescore:
            raise ValueError("this layer version was already scored on this split; pass --rescore-test to score it again")
    except (OSError, KeyError, ValueError, TypeError, sqlite3.Error) as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    gold = [set(row["answer"]) for row in rows]
    res = {**who, "parser_version": PARSER_VERSION, "split_sha256": bench.sha256(split_path),
           "train_sha256": bench.sha256(train_path), "queries": len(rows), "label_space": len(space), "assumption": ASSUMPTION,
           "primary": _reading(gold, pred, space), "secondary_vocabulary": _reading(gold, pred, vocab)}
    Path(ledger_path).write_text(json.dumps(bench.read_ledger(ledger_path) + [res], indent=2, sort_keys=True) + "\n")
    if prior:  # the first look stays visible beside the new one
        res["earlier_scorings"] = prior
    res["interval_95"] = _bootstrap(gold, pred, space)
    res["benchmark"], res["verdict_primary_reading"] = benchmark, _verdicts(res["primary"], benchmark)
    text = json.dumps(res, indent=2, sort_keys=True) + "\n"
    Path(out_path).write_text(text)
    print(text, end="")
    print("\n".join(["Verdict, primary reading only:"] + res["verdict_primary_reading"]))
    return 0
