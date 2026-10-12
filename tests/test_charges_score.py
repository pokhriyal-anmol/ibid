"""Slice 3 ticket 02: `ibid charges score`. Invented fixture set and fixture index, no real case text."""
import contextlib
import copy
import hashlib
import io
import json
import shutil
import tempfile
import unittest
from pathlib import Path

from ibid import bench, index
from ibid.cli import main
from ibid.parse import Provision

WORDS = {"IPC 100": "murder", "IPC 101": "theft", "IPC 102": "cheating", "IPC 103": "kidnapping", "IPC 104": "robbery",
         "IPC 105": "zebra", "IPC 106": "forgery", "IPC 107": "perjury",
         "BNS 200": "murder", "BNS 201": "theft", "BNS 202": "cheating", "BNS 203": "snatching", "BNS 204": "dacoity",
         "BNS 205": "mischief", "BNS 206": "perjury"}
PROVS = [Provision(c, t, None, ()) for c, t in WORDS.items()]
# One-word provisions of equal length, so a section scores its idf: a term in one provision beats a term in two.


def charge(name: str, ipc: list, bns: list) -> dict:
    return {"charge": name, "sections": {"ipc": ipc, "bns": bns}}


def item(iid: str, query: str, charges: list, basis: str = "agent-drafted-skeptic-refuted") -> dict:
    return {"id": iid, "query": query, "author_type": "judgment-excerpt", "source": "invented", "anonymised": True,
            "charges": charges, "label_basis": basis, "reviewed_by": "skeptic-1"}


ITEMS = [
    item("m1", "murder", [charge("murder", ["IPC 100"], ["BNS 200"])]),
    item("m2", "theft and cheating", [charge("theft", ["IPC 101"], ["BNS 201"]), charge("cheating", ["IPC 102"], ["BNS 202"])]),
    item("m3", "kidnapping robbery perjury", [charge("kidnapping", ["IPC 103"], []), charge("robbery", ["IPC 104"], ["BNS 204"]),
                                              charge("perjury", ["IPC 107"], ["BNS 206"])], "lawyer"),
    item("m4", "theft", [charge("theft", ["IPC 105", "IPC 101"], ["BNS 205", "BNS 201"])]),  # the first accepted section is never predicted
    item("m6", "kidnapping", [charge("kidnapping", ["IPC 103"], [])]),
]
K, R = 1, 0.5


def frozen_record(k=K, r=R, version="v2.11") -> dict:
    rule = {"name": "query-rule", "version": version, "params_sha256": bench.rule_hash(k, r, "max")}
    return {"rule": rule, "k": k, "r": r, "section_score": "max", "stop_words": bench.STOP_WORDS, "knobs": bench.DEFAULT_KNOBS}


class ChargesScoreTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp)
        index.build(str(self.tmp / "i.sqlite"), PROVS, []).close()
        self.frozen = self.tmp / "frozen.json"
        self.frozen.write_text(json.dumps(frozen_record()))

    def write(self, items=ITEMS, name="set.json", pin=True) -> Path:
        p = self.tmp / name
        p.write_text(json.dumps({"version": "t", "created": "2026-10-12", "licence_note": "invented", "label_policy": "invented", "items": items}))
        if pin:
            p.with_suffix(".sha256").write_text(hashlib.sha256(p.read_bytes()).hexdigest() + "\n")
        return p

    def score(self, act="ipc", items=ITEMS, out="out.json", expect=0, set_path=None):
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            code = main(["charges", "score", "--set", str(set_path or self.write(items)), "--index", str(self.tmp / "i.sqlite"),
                         "--frozen-rule", str(self.frozen), "--act", act, "--out", str(self.tmp / out)])
        self.assertEqual(code, expect, err.getvalue())
        return json.loads((self.tmp / out).read_text()) if expect == 0 else err.getvalue()

    def test_ipc_scores_match_hand_computed(self):
        r = self.score("ipc")
        # top-1: found m1, m2 theft, m3 kidnapping, m4, m6 = 5 of 8 charges; items fully found m1, m4, m6 = 3 of 5.
        self.assertEqual({k: r["top_k"][k] for k in ("items", "charges", "recall", "all_charges_hit", "mean_predictions")},
                         {"items": 5, "charges": 8, "recall": 0.625, "all_charges_hit": 0.6, "mean_predictions": 1.0})
        # threshold keeps every retrieved section: all 8 found, 1+2+3+1+1 predictions over 5 items.
        self.assertEqual({k: r["threshold"][k] for k in ("recall", "all_charges_hit", "mean_predictions")},
                         {"recall": 1.0, "all_charges_hit": 1.0, "mean_predictions": 1.6})

    def test_bns_scores_match_hand_computed(self):
        r = self.score("bns")
        # m6 has no BNS charge, m3 kidnapping has none: 2 excluded, 4 items and 6 charges scored.
        # top-1: m1, m4 found; m2 theft only; m3 perjury only (BNS 204 never matches) = 4 of 6; items 2 of 4.
        self.assertEqual({k: r["top_k"][k] for k in ("items", "charges", "recall", "all_charges_hit", "mean_predictions")},
                         {"items": 4, "charges": 6, "recall": round(4 / 6, 6), "all_charges_hit": 0.5, "mean_predictions": 1.0})
        self.assertEqual({k: r["threshold"][k] for k in ("recall", "all_charges_hit", "mean_predictions")},
                         {"recall": round(5 / 6, 6), "all_charges_hit": 0.75, "mean_predictions": 1.25})
        self.assertEqual(r["charges_excluded_no_counterpart"], 2)
        self.assertEqual(r["items_scored"], 4)

    def test_strata_by_charges_counted_for_the_act(self):
        s = self.score("ipc")["top_k"]["by_charges_per_item"]
        self.assertEqual({k: (v["items"], v["charges"], v["recall"], v["all_charges_hit"]) for k, v in s.items()},
                         {"1": (3, 3, 1.0, 1.0), "2": (1, 2, 0.5, 0.0), "3+": (1, 3, round(1 / 3, 6), 0.0)})
        b = self.score("bns", out="b.json")["threshold"]["by_charges_per_item"]  # m3 counts 2 charges under the BNS
        self.assertEqual({k: (v["items"], v["charges"], v["recall"]) for k, v in b.items()},
                         {"1": (2, 2, 1.0), "2": (2, 4, round(3 / 4, 6)), "3+": (0, 0, 0.0)})

    def test_any_accepted_section_finds_the_charge(self):
        # m4 accepts [IPC 105, IPC 101] and only IPC 101 is predicted; counting the first alone would score 0 of 1.
        m4 = [i for i in ITEMS if i["id"] == "m4"]
        r = self.score("ipc", m4)
        self.assertEqual((r["top_k"]["recall"], r["top_k"]["predictions"]), (1.0, {"m4": ["IPC 101"]}))
        first_only = copy.deepcopy(m4)
        first_only[0]["charges"][0]["sections"]["ipc"] = ["IPC 105"]
        self.assertEqual(self.score("ipc", first_only, "f.json")["top_k"]["recall"], 0.0)

    def test_missed_charges_list_item_charge_and_top_predicted(self):
        r = self.score("ipc")
        self.assertEqual(r["top_k"]["missed"], [{"id": "m2", "charge": "cheating", "top_predicted": ["IPC 101"]},
                                                {"id": "m3", "charge": "robbery", "top_predicted": ["IPC 103"]},
                                                {"id": "m3", "charge": "perjury", "top_predicted": ["IPC 103"]}])
        self.assertEqual(r["threshold"]["missed"], [])

    def test_predictions_come_only_from_the_chosen_act(self):
        # "murder" and "theft" match both Acts.
        for act in ("ipc", "bns"):
            r = self.score(act, out=f"{act}.json")
            for out in ("top_k", "threshold"):
                for pred in r[out]["predictions"].values():
                    self.assertTrue(pred and all(c.startswith(act.upper() + " ") for c in pred), (act, pred))

    def test_a_section_outside_any_label_list_is_predicted_and_found(self):
        # IPC 107 belongs to no benchmark label list; it is retrieved and found.
        r = self.score("ipc")
        self.assertIn("IPC 107", r["threshold"]["predictions"]["m3"])
        self.assertNotIn("perjury", [m["charge"] for m in r["threshold"]["missed"]])

    def test_sub_provision_label_is_found_by_its_section(self):
        provs = PROVS + [Provision("IPC 108", "arson", None, ("IPC 108(1)",)), Provision("IPC 108(1)", "arson", "IPC 108", ())]
        index.build(str(self.tmp / "i.sqlite"), provs, []).close()
        it = [item("s", "arson", [charge("arson", ["IPC 108(1)"], [])])]
        self.assertEqual(self.score("ipc", it)["top_k"]["recall"], 1.0)

    def test_records_set_rule_index_and_label_basis(self):
        r = self.score("ipc")
        self.assertEqual(r["inputs"], {"set_sha256": hashlib.sha256((self.tmp / "set.json").read_bytes()).hexdigest(),
                                       "index_sha256": bench.sha256(str(self.tmp / "i.sqlite"))})
        self.assertEqual((r["act"], r["rule"]["version"], r["rule"]["params_sha256"], r["charges_excluded_no_counterpart"]),
                         ("IPC", "v2.11", bench.rule_hash(K, R, "max"), 0))
        self.assertEqual(r["label_basis"], {"agent-drafted-skeptic-refuted": 4, "lawyer": 1})

    def test_two_identical_runs_are_byte_identical(self):
        self.score("ipc", out="a.json")
        self.score("ipc", out="b.json")
        self.assertEqual((self.tmp / "a.json").read_bytes(), (self.tmp / "b.json").read_bytes())

    def test_second_scoring_of_a_rule_version_is_reported_beside_the_first(self):
        first = self.score("ipc")["scorings_of_this_rule_version"]
        self.assertEqual(len(first), 1)
        self.frozen.write_text(json.dumps(frozen_record(k=2)))  # same version label, another k
        both = self.score("ipc", out="2.json")["scorings_of_this_rule_version"]
        self.assertEqual((len(both), both[0]), (2, first[0]))
        self.assertNotEqual(both[0]["scores"], both[1]["scores"])
        self.assertEqual(len(self.score("bns", out="3.json")["scorings_of_this_rule_version"]), 1)  # each Act has its own list

    def test_unpinned_or_changed_set_is_refused_and_writes_nothing(self):
        self.score(set_path=self.write(pin=False), expect=1, out="x.json")
        p = self.write()
        p.write_bytes(p.read_bytes().replace(b"murder", b"mudder", 1))
        self.assertIn("does not match its pin", self.score(set_path=p, expect=1, out="y.json"))
        self.assertFalse((self.tmp / "x.json").exists() or (self.tmp / "y.json").exists() or (self.tmp / "set.ledger.json").exists())

    def test_frozen_rule_that_does_not_hold_its_own_hash_is_refused(self):
        bad = frozen_record()
        bad["r"] = 0.9
        self.frozen.write_text(json.dumps(bad))
        self.score(expect=1)

    def test_invalid_item_is_refused(self):
        items = copy.deepcopy(ITEMS)
        items[0]["author_type"] = "model"
        self.assertIn("author_type", self.score(items=items, expect=1))


class MatchesBenchRunTest(unittest.TestCase):
    """The frozen rule scored by charge predicts what `bench run` predicts, with the label space lifted to the Act."""

    def test_predictions_equal_bench_run_on_the_same_queries(self):
        tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, tmp)
        index.build(str(tmp / "i.sqlite"), PROVS, []).close()
        ipc = sorted(c for c in WORDS if c.startswith("IPC "))
        label = lambda c: f"Section {c.split()[1]} in The Indian Penal Code"
        (tmp / "labels.json").write_text(json.dumps({label(c): n for n, c in enumerate(ipc)}))
        (tmp / "dev.jsonl").write_text(json.dumps({"id": "d", "text": ["theft"], "labels": [label("IPC 101")]}) + "\n")
        (tmp / "split.jsonl").write_text("".join(json.dumps({"id": i["id"], "text": [i["query"]], "labels": [label("IPC 100")]}) + "\n"
                                                 for i in ITEMS))
        (tmp / "manifest.json").write_text(json.dumps({n: {"sha256": bench.sha256(str(tmp / n))}
                                                       for n in ("dev.jsonl", "split.jsonl", "labels.json")}))
        common = ["--labels", str(tmp / "labels.json"), "--index", str(tmp / "i.sqlite"), "--manifest", str(tmp / "manifest.json")]
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(main(["bench", "round", "--train", str(tmp / "dev.jsonl"), "--dev", str(tmp / "dev.jsonl"), *common,
                                   "--log", str(tmp / "log.json"), "--k", "2", "--r", "0.8"]), 0)
            self.assertEqual(main(["bench", "freeze", "--log", str(tmp / "log.json"), "--out", str(tmp / "frozen.json")]), 0)
            self.assertEqual(main(["bench", "run", "--split", str(tmp / "split.jsonl"), *common, "--k", "2", "--r", "0.8",
                                   "--out", str(tmp / "bench.json")]), 0)
        (tmp / "set.json").write_text(json.dumps({"version": "t", "created": "x", "licence_note": "x", "label_policy": "x", "items": ITEMS}))
        (tmp / "set.sha256").write_text(bench.sha256(str(tmp / "set.json")) + "\n")
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(main(["charges", "score", "--set", str(tmp / "set.json"), "--index", str(tmp / "i.sqlite"),
                                   "--frozen-rule", str(tmp / "frozen.json"), "--act", "ipc", "--out", str(tmp / "c.json")]), 0)
        b, c = json.loads((tmp / "bench.json").read_text()), json.loads((tmp / "c.json").read_text())
        self.assertTrue(c["threshold"]["predictions"])
        self.assertEqual(c["top_k"]["predictions"], {i: b["predictions"][i] for i in c["top_k"]["predictions"]})
        self.assertEqual(c["threshold"]["predictions"], {i: b["threshold"]["predictions"][i] for i in c["threshold"]["predictions"]})
        self.assertEqual((c["k"], c["r"], c["rule"]["params_sha256"]), (2, 0.8, b["rule"]["params_sha256"]))


if __name__ == "__main__":
    unittest.main()
