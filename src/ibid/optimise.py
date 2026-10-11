"""Slice 2 ticket 08: one logged optimisation round and the declared stopping rule. Reads train and dev, never test."""
import json
import re
import sqlite3
import sys
from pathlib import Path

from ibid import bench

GAIN_BAR, HURTS_BAR, STREAK, CAP = 0.005, 0.005, 3, 20  # 0.5 points on a 0-1 scale
UNSUPPORTED = {"tokenisation", "bm25", "levels"}  # declared knobs this command cannot vary yet: refused, not ignored
WORD = re.compile(r"[^\W\d_]+")


def apply_change(params: dict, change: str) -> dict:
    """The params after exactly one declared change; ValueError for anything else."""
    knob, _, value = change.partition("=")
    if not value:
        raise ValueError("a change looks like knob=value")
    if knob in UNSUPPORTED:
        raise ValueError(f"{knob} is declared but this command cannot vary it yet")
    new = dict(params)
    if knob == "stop_words":
        op, word = value[0], value[1:]
        if op not in "+-" or not WORD.fullmatch(word) or word != word.lower():
            raise ValueError("stop_words changes one word at a time: +word or -word")
        words = set(params["stop_words"])
        new["stop_words"] = sorted(words | {word} if op == "+" else words - {word})
    elif knob == "k":
        new["k"] = int(value)
    elif knob == "r":
        new["r"] = float(value)
    elif knob == "rollup":
        new["rollup"] = value
    else:
        raise ValueError(f"{knob} is not a declared knob")
    bench.check_params(new["k"], new["r"], new["rollup"])
    if new == params:
        raise ValueError("the change changes nothing")
    return new


def evaluate(db: sqlite3.Connection, cases: list[dict], gold: list[set[str]], space: set[str], p: dict) -> dict:
    ranked = [bench.rank_sections(db, " ".join(c["text"]), space, p["rollup"], p["stop_words"]) for c in cases]
    top_k, above_r = zip(*(bench.predict(x, p["k"], p["r"]) for x in ranked))
    out = {}
    for name, sets in (("top_k", top_k), ("threshold", above_r)):
        sets = [set(s) for s in sets]
        out[name] = {"scores": bench.score(gold, sets, space), "strata": bench.strata(cases, gold, sets, space)}
    return out


def stopping_status(rounds: list[dict]) -> dict:
    """Saturation, the cap and the overfit signal, all read from top-k macro F1 of the logged rounds."""
    def gains(split):
        v = [r[split]["top_k"]["scores"]["macro_f1"] for r in rounds]
        return [round(b - a, 6) for a, b in zip(v, v[1:])]
    dev, train = gains("dev"), gains("train")
    return {"saturated": len(dev) >= STREAK and all(g < GAIN_BAR for g in dev[-STREAK:]),
            "cap_reached": len(rounds) - 1 >= CAP,
            # shortcut: "stops improving while train keeps rising" read as the last 2 rounds, tune if it fires noisily
            "overfitting": len(dev) >= 2 and all(d <= 0 < t for d, t in zip(dev[-2:], train[-2:]))}


def freezable(entry: dict) -> bool:
    return not entry["flags"] or entry["owner_approved"]


def single_label_micro(entry: dict) -> float:
    return entry["dev"]["top_k"]["strata"]["gold_label_count"]["1"]["scores"]["micro_f1"]


def run_round(train: str, dev: str, labels: str, index: str, manifest: str, log_path: str, changes: list[str],
              k: int | None, r: float | None, rollup: str | None) -> int:
    try:
        return _round(train, dev, labels, index, manifest, log_path, changes, k, r, rollup)
    except (ValueError, KeyError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 1


def _next_params(rounds, changes, k, r, rollup):
    """(params, knob, change) for the round about to run."""
    if rounds:
        if len(changes) != 1 or (k, r, rollup) != (None, None, None):
            raise ValueError("a round after round 0 takes exactly one --change and no k, r or rollup")
        return (apply_change(rounds[-1]["params"], changes[0]), *changes[0].split("=", 1))
    if changes or k is None or r is None:
        raise ValueError("round 0 is the unmodified rule: give --k and --r, no --change")
    params = {"stop_words": sorted(bench.STOP_WORDS), "k": k, "r": r, "rollup": rollup or "max"}
    bench.check_params(k, r, params["rollup"])
    return params, None, None


def _round(train, dev, labels, index, manifest, log_path, changes, k, r, rollup) -> int:
    test_hash = bench.pinned_test_hash(manifest)
    for p in (train, dev):  # shortcut: by name and by pinned hash; ticket 07 owns the once-only guard
        if Path(p).stem == "test" or bench.sha256(p) == test_hash:
            raise ValueError("the test split is never read by an optimisation round")
    if bench.verify_pinned([train, dev, labels], manifest):
        return 1
    rounds = json.loads(Path(log_path).read_text())["rounds"] if Path(log_path).exists() else []
    params, knob, change = _next_params(rounds, changes, k, r, rollup)
    space = bench.load_space(labels)
    db = sqlite3.connect(f"file:{index}?mode=ro", uri=True)
    n = len(rounds)
    entry = {"round": n, "knob": knob, "change": change, "params": params,
             "rule": {"name": bench.RULE_NAME, "version": bench.RULE_VERSION if n == 0 else f"{bench.RULE_VERSION}.{n}",
                      "params_sha256": bench.rule_hash(params["k"], params["r"], params["rollup"], params["stop_words"])},
             "inputs": {name: bench.sha256(p) for name, p in
                        (("train_sha256", train), ("dev_sha256", dev), ("labels_sha256", labels), ("index_sha256", index))},
             "parser_version": bench.PARSER_VERSION}
    for name, path in (("train", train), ("dev", dev)):
        cases, gold = bench.load_cases(path, space)
        entry[name] = {"cases": len(cases), **evaluate(db, cases, gold, space, params)}
    entry["gap"] = {m: round(entry["train"]["top_k"]["scores"][m] - entry["dev"]["top_k"]["scores"][m], 6)
                    for m in ("micro_f1", "macro_f1")}
    drop = round(single_label_micro(rounds[-1]) - single_label_micro(entry), 6) if rounds else 0
    entry["flags"] = ["hurts-simple"] if drop > HURTS_BAR else []
    entry["owner_approved"] = False  # the owner sets this to true in the log to let a flagged round become the frozen rule
    entry["status"] = stopping_status(rounds + [entry])
    Path(log_path).parent.mkdir(parents=True, exist_ok=True)
    Path(log_path).write_text(json.dumps({"rounds": rounds + [entry]}, indent=2, sort_keys=True) + "\n")
    print(f"round {n}: dev macro_f1 {entry['dev']['top_k']['scores']['macro_f1']} flags {entry['flags']} status {entry['status']}")
    return 0
