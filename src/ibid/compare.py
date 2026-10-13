"""`ibid charges compare`: one report over the results files of `ibid charges score`, for several layers and sets."""
import hashlib
import json
import sys
from pathlib import Path

from ibid.charges import SECTION_NUMBER
from ibid.report import OUTPUTS, pts, table

BASELINE = "baseline"


def _pct(x: float) -> str:
    return pts(x, 1)


def _fig(f: dict) -> str:
    return f"recall {_pct(f['recall'])}, all-charges-hit {_pct(f['all_charges_hit'])}, {f['mean_predictions']:.2f} predictions"


def _rows(d: dict) -> tuple[str, str, list[dict], list[dict], dict, dict]:
    """(layer, version, one row per scored output, scorings of this version as {output: figures}, layer inputs, layer counts)."""
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
    return layer, version, rows, scorings, {**inputs, "index_sha256": d["inputs"]["index_sha256"]}, d.get("layer_counts", {})


def _row_cells(r: dict, base: dict | None) -> list[str]:
    found = round(r["recall"] * r["charges"])
    cells = [r["layer"], r["layer_version"], r["set_name"], r["set"][:12], r["act"], r["output"], f"{found} of {r['charges']}"]
    for key in ("recall", "all_charges_hit"):
        cells.append(_pct(r[key]))
        cells += [f"{(r[key] - base[o][key]) * 100:+.1f}" for o in ("top-k", "threshold")] if base else ["-", "-"]
    return cells + [f"{r['mean_predictions']:.2f}", r["inputs"].get("concordance", "-")[:8]]


def _caveats(layer: str, version: str, rows: list[dict], scorings: dict, inputs: dict, named: dict, counts: dict) -> list[str]:
    """`named` maps a set hash to (queries naming sections, queries, BNS labels come from the concordance); `counts` is keyed by (set, Act, concordance)."""
    out = [f"### {layer} {version}", ""]
    for r in sorted({x["set"]: x for x in rows}.values(), key=lambda x: x["set_name"]):
        n, total, _ = named[r["set"]]
        out.append(f"- Set {r['set_name']}: label basis {json.dumps(r['basis'], sort_keys=True)}; {n} of {total} queries name their sections, "
                   "so a layer that reads cited sections is scored on text that states the answer.")
    if "concordance" in inputs:
        for r in sorted({x["set"]: x for x in rows}.values(), key=lambda x: x["set_name"]):
            if named[r["set"]][2]:
                out.append(f"- Set {r['set_name']}: its BNS labels come from verified concordance entries, the table this layer reads. "
                           "BNS recall here is IPC recall carried through the same table, not an independent check against the BNS, "
                           "and is not comparable with layers that do not read the concordance.")
    if "model" in inputs:
        out.append(f"- Learned weights: fitted model {inputs['model']}. The score measures agreement with labels the weights were fitted toward.")
    if "producer" in inputs:
        out.append(f"- A model produced an input: {inputs['producer']}. Retrieval from that input is code. The sub-queries are the model's "
                   "paraphrase of the query and can carry section numbers or legal terms the model knows, so the score measures the model plus the baseline.")
    if layer == "cited":
        out.append("- Some labels were drafted from the sections the queries name, so this layer is scored against answers drafted from the same mentions. "
                   "A citation with no verified concordance entry gives no prediction in the other Act, which is why the BNS figure is low.")
    for (s, act, conc), c in sorted((k, c) for k, c in counts.items() if c):
        out.append(f"- Counts recorded by the layer on set {s}, {act}, concordance {conc}: " + ", ".join(f"{k} {v}" for k, v in sorted(c.items())) + ".")
    for (s, act), sc in sorted(scorings.items()):
        out.append(f"- {len(sc)} scoring{'s' if len(sc) != 1 else ''} of this layer version on set {s}, {act}:")
        out += [f"  - {'; '.join(f'{o}: {_fig(f)}' for o, f in x.items())}" for x in sc]
    return out + [""]


def _ilsi(d: dict) -> list[list[str]]:
    """Rows of (layer, version, split, split hash, output, rule or model hash, cases, scores). The baseline has a top-k and a threshold row."""
    split = "test" if "test_scores" in d else "dev"
    if "rule" in d:
        layer, version, ident, sha = BASELINE, d["rule"]["version"], d["rule"]["params_sha256"], d["inputs"]["split_sha256"]
        outs = {"top-k": d["scores"]}
        for e in d.get("test_scores", []):  # the threshold output of this rule on this split, scored in the same run
            if e["split_sha256"] == sha and e["rule"]["version"] == version and "threshold_scores" in e:
                outs["threshold"] = e["threshold_scores"]
    else:
        layer, version, ident, sha = d["layer"], d["layer_version"], d["model_sha256"], d["split_sha256"]
        outs = {f"top-{d['k']}" if "k" in d else "output": d["scores"]}
    return [[layer, version, split, sha, o, ident, str(d["cases"]), _pct(f["micro_f1"]), _pct(f["macro_f1"]), _pct(f["jaccard"])]
            for o, f in outs.items()]


def compare(results: list[str], sets: list[str], ilsi: list[str], out_path: str) -> int:
    try:
        set_info = {}
        for p in sets:
            raw = Path(p).read_bytes()
            qs = [i["query"] for i in json.loads(raw)["items"]]
            policy = json.loads(raw).get("label_policy", "")
            named = (sum(bool(SECTION_NUMBER.search(q)) for q in qs), len(qs), "concordance" in policy.lower())
            set_info[hashlib.sha256(raw).hexdigest()] = (Path(p).stem, named)
        rows, layers = [], {}
        for p in results:
            layer, version, rs, scorings, inputs, counts = _rows(json.loads(Path(p).read_text()))
            for r in rs:
                if r["set"] not in set_info:
                    raise ValueError(f"{p}: set {r['set']} is not among the --set files")
                r.update(layer=layer, layer_version=version, set_name=set_info[r["set"]][0], index=inputs["index_sha256"], inputs=inputs)
            rows += rs
            rec = layers.setdefault((layer, version), {"rows": [], "scorings": {}, "inputs": {}, "counts": {}})
            rec["rows"] += rs
            rec["inputs"].update(inputs)
            rec["counts"][(rs[0]["set_name"], rs[0]["act"], inputs.get("concordance", "-")[:8])] = counts
            rec["scorings"][(rs[0]["set_name"], rs[0]["act"])] = scorings
        ilsi_rows = [r for p in ilsi for r in _ilsi(json.loads(Path(p).read_text()))]
    except (OSError, KeyError, ValueError, TypeError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    base = {(r["set"], r["act"], r["output"]): r for r in rows if r["layer"] == BASELINE}
    if missing := sorted({(r["set_name"], r["act"]) for r in rows if r["layer"] != BASELINE and (r["set"], r["act"], "top-k") not in base}):
        print(f"error: no baseline results for {missing}", file=sys.stderr)
        return 1
    order = sorted(rows, key=lambda r: (r["layer"] != BASELINE, r["layer"], r["layer_version"], r["set_name"], r["act"], r["inputs"].get("concordance", ""), [o for _, o in OUTPUTS].index(r["output"]) if r["output"] != "output" else 0, r["recall"]))
    head = ["layer", "version", "set", "set hash", "Act", "output", "charges found", "recall %", "vs top-k", "vs threshold",
            "all-charges-hit %", "vs top-k", "vs threshold", "mean predictions", "concordance"]
    cells = []
    for r in order:
        b = None if r["layer"] == BASELINE else {o: base[(r["set"], r["act"], o)] for o in ("top-k", "threshold")}
        cells.append(_row_cells(r, b))
    doc = ["# Comparison across layers and sets", "",
           "Generated by `ibid charges compare` from the results files. Differences are percentage points against the baseline "
           "on the same set and Act. Nothing here is typed by hand.", "", "## Multi-charge sets, per charge", ""]
    doc += table(head, cells)
    doc += ["## Inputs of every row", ""]
    doc += table(["layer", "version", "set", "Act", "output", "set sha256", "index sha256", "layer inputs"],
                  [[r["layer"], r["layer_version"], r["set_name"], r["act"], r["output"], r["set"], r["index"],
                    "`" + json.dumps(r["inputs"], sort_keys=True) + "`"] for r in order])
    doc += ["## What each number is and is not", ""]
    for (layer, version), rec in sorted(layers.items(), key=lambda kv: (kv[0][0] != BASELINE, kv[0])):
        doc += _caveats(layer, version, rec["rows"], rec["scorings"], rec["inputs"], {s: v[1] for s, v in set_info.items()}, rec["counts"])
    if ilsi_rows:
        doc += ["## ILSI splits, a different task", "",
                "Judgment-level section prediction over 100 labels, scored by micro-F1, macro-F1 and Jaccard. "
                "It is not comparable with the per-charge figures above.", ""]
        doc += table(["layer", "version", "split", "split sha256", "output", "model or rule sha256", "cases", "micro-F1 %", "macro-F1 %", "Jaccard %"],
                      sorted(ilsi_rows))
    Path(out_path).write_text("\n".join(doc))
    return 0
