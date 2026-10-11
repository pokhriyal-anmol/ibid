"""Slice 2 ticket 09: the report. Every number is read from the log, the ledger and the test results file."""
import json
import sys
from pathlib import Path

PUBLISHED = (
    ("m-F1 (micro or macro not confirmed)", "28.08", "IL-TUR benchmark, statute identification (arXiv 2512.21902 describes its splits)"),
    ("macro-F1", "28.45", "LeSICiN paper, Zenodo record 6053791"),
)
CAVEATS = (
    "Different models: the published scores come from trained classifiers, Ibid is deterministic retrieval with no training.",
    "Possibly a different dataset copy: Ibid uses the LeSICiN Zenodo release, the IL-TUR copy is gated and was not obtained.",
    "Split counts may differ from the published setup.",
    "Metric protocol may differ: our metrics are our own implementation until the official evaluation script is read.",
    "No rank is claimed.",
)
METRICS = ("micro_f1", "macro_f1", "jaccard")
OUTPUTS = (("top_k", "top-k"), ("threshold", "threshold"))


def pts(v: float) -> str:
    return f"{v * 100:.2f}"


def cell(scores: dict) -> str:
    return " / ".join(pts(scores[m]) for m in METRICS)


def table(header: list[str], rows: list[list[str]]) -> list[str]:
    return ["| " + " | ".join(r) + " |" for r in [header, ["---"] * len(header), *rows]] + [""]


def provenance(label: str, rule: dict, hashes: dict) -> str:
    h = "".join(f", {k} {v}" for k, v in sorted(hashes.items()))
    return f"- {label}: rule {rule['name']} {rule['version']}, rule hash {rule['params_sha256']}{h}"


def build(rounds: list[dict], ledger: list[dict], results: dict, frozen_round: int) -> str:
    first, last = rounds[0], rounds[-1]
    frozen = next(e for e in rounds if e["round"] == frozen_round)  # StopIteration is caught by the caller
    shown = [("round 0", first), (f"frozen round ({frozen['round']})", frozen)]
    if frozen is not last:
        shown.append((f"last logged round ({last['round']})", last))
    out = ["# Ibid on the LeSICiN statute-identification benchmark", "",
           "Scores are points, shown as micro-F1 / macro-F1 / Jaccard.", "", "## Scores", ""]
    rows = []
    for key, name in OUTPUTS:
        for label, e in shown:
            for split in ("train", "dev"):
                rows.append([name, f"{label} {split}", cell(e[split][key]["scores"])])
        for i, t in enumerate(ledger):
            sc = t["scores"] if key == "top_k" else t["threshold_scores"]
            rows.append([name, f"test score {i + 1}, k {t['k']}, r {t['r']}", cell(sc)])
    out += table(["output", "run", "scores"], rows)
    out += ["## Train/dev gap (top-k, train minus dev, points)", ""]
    out += table(["round", "micro-F1 gap", "macro-F1 gap"],
                 [[str(e["round"]), pts(e["gap"]["micro_f1"]), pts(e["gap"]["macro_f1"])] for _, e in shown])
    for key, name in OUTPUTS:
        out += [f"## Strata, {name}: dev round 0, dev frozen, test", ""]
        cols = [("dev round 0", first["dev"][key]["strata"]),
                ("dev frozen", frozen["dev"][key]["strata"]),
                ("test", results["strata"] if key == "top_k" else results["threshold"]["strata"])]
        srows = [[f"{dim} {b}", *(f"{s[dim][b]['cases']} cases: {cell(s[dim][b]['scores'])}" for _, s in cols)]
                 for dim in ("gold_label_count", "words") for b in cols[0][1][dim]]
        out += table(["stratum", *(c for c, _ in cols)], srows)
    never = results["per_label"]["never_found"]
    out += ["## Labels never found (test, top-k)", "", ", ".join(never) if never else "none", "",
            "## Published scores, not comparable like for like", ""]
    out += table(["metric", "published", "source"], [list(p) for p in PUBLISHED])
    out += ["Caveats:", "", *[f"- {c}" for c in CAVEATS], "", "## What these numbers rest on", ""]
    for label, e in shown:
        out.append(provenance(label, e["rule"], e["inputs"] | {"parser": e["parser_version"]}))
    for t in ledger:
        out.append(provenance(f"test score on split {t['split_sha256']}", t["rule"], {}))
    out.append(f"- test results file: split {results['inputs']['split_sha256']}, labels {results['inputs']['labels_sha256']}, "
               f"index {results['inputs']['index_sha256']}, rule hash {results['rule']['params_sha256']}")
    match = all(t["rule"]["params_sha256"] == last["rule"]["params_sha256"] for t in ledger)
    out.append(f"- ledger rule matches the final logged round: {'yes' if match else 'NO'}")
    return "\n".join(out) + "\n"


def run_report(log_path: str, ledger_path: str, results_path: str, out_path: str, frozen_path: str) -> int:
    try:
        rounds = json.loads(Path(log_path).read_text())["rounds"]
        ledger = json.loads(Path(ledger_path).read_text())
        results = json.loads(Path(results_path).read_text())
        if not rounds or not any(e["split_sha256"] == results["inputs"]["split_sha256"] for e in ledger):
            raise ValueError("no logged rounds, or the results file is not a scored test split in the ledger")
        text = build(rounds, ledger, results, json.loads(Path(frozen_path).read_text())["round"])
    except (OSError, KeyError, ValueError, StopIteration) as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    Path(out_path).write_text(text)
    return 0
