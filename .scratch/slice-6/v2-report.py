"""Recompute every figure in v2-report.md. Run from the repo root:

  uv run python .scratch/slice-6/v2-report.py <data dir holding assoc-nb-v1.json and assoc-nb-v2.json>

Stdlib only. It asserts its own recall against the committed results files, so a wrong
roll-up, a wrong predictions file or a stale model hash stops it instead of printing."""
import hashlib
import json
import sys
from pathlib import Path

data = Path(sys.argv[1])
SET = json.loads(Path("gold/multicharge/v2.json").read_text())["items"]
POSTS = {  # layer version -> predictions file for set v2, scored results file per Act
    "v1": ("results/layers/assoc-nb-v1-multicharge-v2-predictions.json", "results/multicharge-v2-assoc-{act}.json"),
    "v2": ("results/layers/assoc-nb-v2-multicharge-v2-predictions.json", "results/multicharge-v2-assoc-v2-{act}.json"),
}


def sec(c: str) -> str:
    return c.split("(")[0]  # an accepted sub-provision counts as its section


vocab, found = {}, {}
for v, (pred_path, res_path) in POSTS.items():
    model = data / f"assoc-nb-{v}.json"
    pred = json.loads(Path(pred_path).read_text())
    assert hashlib.sha256(model.read_bytes()).hexdigest() == pred["inputs"]["model"], f"{model} is not the model that made {pred_path}"
    vocab[v] = set(json.loads(model.read_text())["docs"])
    found[v] = pred["items"]

ipc_sections = {s for i in SET for c in i["charges"] for s in map(sec, c["sections"]["ipc"])}
print(f"set v2 IPC sections: {len(ipc_sections)}")
for v in vocab:
    print(f"{v} vocabulary: {len(vocab[v])} sections, {len(ipc_sections & vocab[v])} of the set's {len(ipc_sections)}")
v1, v2 = vocab["v1"], vocab["v2"]
group = {s: ("both" if s in v1 and s in v2 else "v2 only" if s in v2 else "v1 only" if s in v1 else "neither") for s in ipc_sections}
for g in ("both", "v2 only", "v1 only", "neither"):
    print(f"sections {g}: {sorted(s for s in group if group[s] == g)}")


def recall(v: str, act: str, pick) -> tuple[int, int]:
    hit = total = 0
    for i in SET:
        pred = {sec(c) for c in found[v][i["id"]][act.lower()]}
        for c in i["charges"]:
            if not c["sections"][act.lower()] or not pick(c):
                continue
            total += 1
            hit += any(sec(s) in pred for s in c["sections"][act.lower()])
    return hit, total


print("\nrecall % from the scored results files (baseline row is top-k / threshold):")
for s in ("v1", "v2"):
    for act in ("ipc", "bns"):
        r = lambda f, k="output": 100 * json.loads(Path(f).read_text())[k]["recall"]
        b = f"results/multicharge-{s}-{act}.json"
        v1f = f"results/multicharge-{s}-assoc-{act}" + ("-concv3" if s == "v1" else "") + ".json"  # concordance v3, the one v2 used
        print(f"  set {s} {act.upper()}: baseline {r(b, 'top_k'):.1f} / {r(b, 'threshold'):.1f}, "
              f"assoc-nb v1 {r(v1f):.1f}, assoc-nb v2 {r(f'results/multicharge-{s}-assoc-v2-{act}.json'):.1f}")
for v in ("v1", "v2"):
    n = sum(any(group.get(c) == "v2 only" for c in map(sec, p["ipc"])) for p in found[v].values())
    print(f"{v} predicts a v2-only section in {n} of {len(found[v])} items")

for act in ("IPC", "BNS"):
    for v, (_, res_path) in POSTS.items():
        out = json.loads(Path(res_path.format(act=act.lower())).read_text())["output"]
        h, t = recall(v, act, lambda c: True)
        assert (t, round(h / t, 6)) == (out["charges"], out["recall"]), (act, v, h, t, out["recall"])  # the committed scorer agrees
    print(f"\n{act}: charges by group of the charge's IPC section; found / charges (recall %)")
    for label, keep in (("v1 vocabulary", lambda g: g in ("both", "v1 only")), ("not in v1 vocabulary", lambda g: g in ("v2 only", "neither"))):
        row = []
        for v in ("v1", "v2"):
            h, t = recall(v, act, lambda c: keep(group[sec(c["sections"]["ipc"][0])]))
            row.append(f"{v}: {h} of {t} ({100 * h / t:.1f}%)")
        print(f"  {label}: " + "; ".join(row))
    print(f"  all: " + "; ".join("%s: %d of %d" % ((v,) + recall(v, act, lambda c: True)) for v in ("v1", "v2")))
