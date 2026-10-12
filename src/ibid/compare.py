"""`ibid charges compare`: one report over the results files of `ibid charges score`, for several layers and sets."""
import hashlib
import json
import sys
from pathlib import Path

from ibid.charges import SECTION_NUMBER

BASELINE = "baseline"
OUTPUTS = (("top_k", "top-k"), ("threshold", "threshold"))  # the baseline's two output rules, always the first rows


def _pct(x: float) -> str:
    return f"{x * 100:.1f}"


def _fig(f: dict) -> str:
    return f"recall {_pct(f['recall'])}, all-charges-hit {_pct(f['all_charges_hit'])}, {f['mean_predictions']:.2f} predictions"


def _rows(d: dict) -> tuple[str, str, list[dict], list[dict], dict]:
    """(layer, version, one row per scored output, scorings of this version as {output: figures}, layer inputs)."""
    base = {"set": d["inputs"]["set_sha256"], "act": d["act"], "basis": d["label_basis"]}
    if "rule" in d:  # a frozen-rule results file: two output rules
        outs = {label: d[key] for key, label in OUTPUTS}
        scorings = [{label: s["scores"][key] for key, label in OUTPUTS} for s in d["scorings_of_this_rule_version"]]
        layer, version, inputs = BASELINE, d["rule"]["version"], {"rule_params_sha256": d["rule"]["params_sha256"]}
    else:  # a predictions file's results: one output
        outs = {"output": d["output"]}
        scorings = [{"output": s["scores"]["output"]} for s in d["scorings_of_this_layer_version"]]
        layer, version, inputs = d["layer"], d["layer_version"], d["inputs"]["layer"]
    rows = [{**base, "output": o, **f} for o, f in outs.items()]
    return layer, version, rows, scorings, {**inputs, "index_sha256": d["inputs"]["index_sha256"]}


def _row_cells(r: dict, base: dict | None) -> list[str]:
    found = round(r["recall"] * r["charges"])
    cells = [r["layer"], r["layer_version"], r["set_name"], r["set"][:12], r["act"], r["output"], f"{found} of {r['charges']}"]
    for key in ("recall", "all_charges_hit"):
        cells.append(_pct(r[key]))
        cells += [f"{(r[key] - base[o][key]) * 100:+.1f}" for o in ("top-k", "threshold")] if base else ["-", "-"]
    return cells + [f"{r['mean_predictions']:.2f}"]


def _caveats(layer: str, version: str, rows: list[dict], scorings: dict, inputs: dict, named: dict) -> list[str]:
    out = [f"### {layer} {version}", ""]
    for r in sorted({x["set"]: x for x in rows}.values(), key=lambda x: x["set_name"]):
        n, total = named[r["set"]]
        out.append(f"- Set {r['set_name']}: label basis {json.dumps(r['basis'], sort_keys=True)}; {n} of {total} queries name their sections, "
                   "so a layer that reads cited sections is scored on text that states the answer.")
    if "model" in inputs:
        out.append(f"- Learned weights: fitted model {inputs['model']}. The score measures agreement with labels the weights were fitted toward.")
    if "producer" in inputs:
        out.append(f"- A model produced an input: {inputs['producer']}. Retrieval from that input is code.")
    for (s, act), sc in sorted(scorings.items()):
        out.append(f"- {len(sc)} scoring{'s' if len(sc) != 1 else ''} of this layer version on set {s}, {act}:")
        out += [f"  - {'; '.join(f'{o}: {_fig(f)}' for o, f in x.items())}" for x in sc]
    return out + [""]


def _ilsi(d: dict) -> list[str]:
    if "rule" in d:
        layer, version, ident = BASELINE, d["rule"]["version"], d["rule"]["params_sha256"]
        split = d["inputs"]["split_sha256"]
    else:
        layer, version, ident, split = d["layer"], d["layer_version"], d["model_sha256"], d["split_sha256"]
    s = d["scores"]
    return [layer, version, split, ident, str(d["cases"]), _pct(s["micro_f1"]), _pct(s["macro_f1"]), _pct(s["jaccard"])]


def _table(head: list[str], rows: list[list[str]]) -> list[str]:
    return ["| " + " | ".join(head) + " |", "|" + "---|" * len(head)] + ["| " + " | ".join(r) + " |" for r in rows] + [""]


def compare(results: list[str], sets: list[str], ilsi: list[str], out_path: str) -> int:
    try:
        set_info = {}
        for p in sets:
            raw = Path(p).read_bytes()
            qs = [i["query"] for i in json.loads(raw)["items"]]
            set_info[hashlib.sha256(raw).hexdigest()] = (Path(p).stem, (sum(bool(SECTION_NUMBER.search(q)) for q in qs), len(qs)))
        rows, layers = [], {}
        for p in results:
            layer, version, rs, scorings, inputs = _rows(json.loads(Path(p).read_text()))
            if not rs:
                raise ValueError(f"{p}: no scored output")
            for r in rs:
                if r["set"] not in set_info:
                    raise ValueError(f"{p}: set {r['set']} is not among the --set files")
                r.update(layer=layer, layer_version=version, set_name=set_info[r["set"]][0], index=inputs["index_sha256"], inputs=inputs)
            rows += rs
            rec = layers.setdefault((layer, version), {"rows": [], "scorings": {}, "inputs": {}})
            rec["rows"] += rs
            rec["inputs"].update(inputs)
            rec["scorings"][(rs[0]["set_name"], rs[0]["act"])] = scorings
        ilsi_rows = [_ilsi(json.loads(Path(p).read_text())) for p in ilsi]
    except (OSError, KeyError, ValueError, TypeError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    base = {(r["set"], r["act"], r["output"]): r for r in rows if r["layer"] == BASELINE}
    if missing := sorted({(r["set_name"], r["act"]) for r in rows if r["layer"] != BASELINE and (r["set"], r["act"], "top-k") not in base}):
        print(f"error: no baseline results for {missing}", file=sys.stderr)
        return 1
    order = sorted(rows, key=lambda r: (r["layer"] != BASELINE, r["layer"], r["layer_version"], r["set_name"], r["act"], [o for _, o in OUTPUTS].index(r["output"]) if r["output"] != "output" else 0, r["recall"]))
    head = ["layer", "version", "set", "set hash", "Act", "output", "charges found", "recall %", "vs top-k", "vs threshold",
            "all-charges-hit %", "vs top-k", "vs threshold", "mean predictions"]
    cells = []
    for r in order:
        b = None if r["layer"] == BASELINE else {o: base[(r["set"], r["act"], o)] for o in ("top-k", "threshold")}
        cells.append(_row_cells(r, b))
    doc = ["# Comparison across layers and sets", "",
           "Generated by `ibid charges compare` from the results files. Differences are percentage points against the baseline "
           "on the same set and Act. Nothing here is typed by hand.", "", "## Multi-charge sets, per charge", ""]
    doc += _table(head, cells)
    doc += ["## Inputs of every row", ""]
    doc += _table(["layer", "version", "set", "Act", "output", "set sha256", "index sha256", "layer inputs"],
                  [[r["layer"], r["layer_version"], r["set_name"], r["act"], r["output"], r["set"], r["index"],
                    "`" + json.dumps(r["inputs"], sort_keys=True) + "`"] for r in order])
    doc += ["## What each number is and is not", ""]
    for (layer, version), rec in sorted(layers.items(), key=lambda kv: (kv[0][0] != BASELINE, kv[0])):
        doc += _caveats(layer, version, rec["rows"], rec["scorings"], rec["inputs"], {s: v[1] for s, v in set_info.items()})
    if ilsi_rows:
        doc += ["## ILSI test split, a different task", "",
                "Judgment-level section prediction over 100 labels, scored by micro-F1, macro-F1 and Jaccard. "
                "It is not comparable with the per-charge figures above.", ""]
        doc += _table(["layer", "version", "split sha256", "model or rule sha256", "cases", "micro-F1 %", "macro-F1 %", "Jaccard %"],
                      sorted(ilsi_rows))
    Path(out_path).write_text("\n".join(doc))
    return 0
