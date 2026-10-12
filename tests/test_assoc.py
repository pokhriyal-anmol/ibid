"""Slice 3 ticket 08: the assoc-nb layer (`ibid assoc fit|predict|eval`). Invented fixtures, no real case text."""
import ast
import contextlib
import hashlib
import io
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

from ibid import assoc, bench, index
from ibid.cli import main
from test_charges_score import ITEMS, PROVS

LABELS = {n: f"Section {n} in The Indian Penal Code" for n in range(100, 106)}
# a3 and m1 are the interesting rows: a3 has two labels; m1 is a held-out set id and must never be counted.
TRAIN = [("a1", ["The murder of a man.", "Knife knife!"], [100]), ("a2", ["theft of a purse"], [101]),
         ("a3", ["murder and theft"], [100, 101]), ("a4", ["cheating cheating"], [102]),
         ("a5", ["kidnap"], [103]), ("a6", ["robber"], [104]), ("a7", ["zebra"], [105]),
         ("m1", ["zebra zebra zebra"], [101])]
CONC = [{"ipc": ["IPC 100"], "bns": ["BNS 200"], "type": "one-to-one", "verified": True},
        {"ipc": ["IPC 101"], "bns": ["BNS 201"], "type": "one-to-one", "verified": False}]


def imports_of(source: str) -> set[str]:
    out = set()
    for n in ast.walk(ast.parse(source)):
        if isinstance(n, ast.Import):
            out |= {a.name.split(".")[0] for a in n.names}
        elif isinstance(n, ast.ImportFrom):
            out.add((n.module or "").split(".")[0])
    return out


class AssocTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp)
        index.build(str(self.tmp / "i.sqlite"), PROVS, []).close()
        (self.tmp / "labels.json").write_text(json.dumps({v: i for i, v in enumerate(LABELS.values())}))
        self.set = self.tmp / "set.json"
        self.set.write_text(json.dumps({"version": "t", "created": "2026-10-12", "licence_note": "invented", "label_policy": "invented", "items": ITEMS}))
        self.set.with_suffix(".sha256").write_text(hashlib.sha256(self.set.read_bytes()).hexdigest() + "\n")
        (self.tmp / "conc.json").write_text(json.dumps(CONC))
        self.train = self.write_split("train.jsonl", TRAIN)

    def write_split(self, name, rows) -> Path:
        p = self.tmp / name
        p.write_text("".join(json.dumps({"id": i, "text": t, "labels": [LABELS[n] for n in ls]}) + "\n" for i, t, ls in rows))
        return p

    def cli(self, *argv, expect=0):
        err = io.StringIO()
        with contextlib.redirect_stderr(err), contextlib.redirect_stdout(io.StringIO()):
            code = main(list(argv))
        self.assertEqual(code, expect, err.getvalue())
        return err.getvalue()

    def fit(self, out="m.json", train=None) -> Path:
        self.cli("assoc", "fit", "--train", str(train or self.train), "--holdout-set", str(self.set),
                 "--labels", str(self.tmp / "labels.json"), "--out", str(self.tmp / out))
        return self.tmp / out

    def test_counts_equal_hand_computed_and_held_out_id_is_dropped(self):
        m = json.loads(self.fit().read_text())
        self.assertEqual(m["counts"]["IPC 100"], {"murder": 2, "man": 1, "knife": 2, "theft": 1})
        self.assertEqual(m["counts"]["IPC 101"], {"theft": 2, "purse": 1, "murder": 1})  # no zebra from held-out m1
        self.assertEqual(m["counts"]["IPC 105"], {"zebra": 1})
        self.assertEqual({c: m["docs"][c] for c in ("IPC 100", "IPC 101", "IPC 102")}, {"IPC 100": 2, "IPC 101": 2, "IPC 102": 1})
        h = m["header"]
        self.assertEqual((h["holdout_ids_dropped_from_train"], h["cases_fitted"], h["layer"]), (1, 7, "assoc-nb"))
        self.assertEqual(h["train_sha256"], bench.sha256(str(self.train)))
        self.assertEqual(h["holdout_ids_sha256"], hashlib.sha256(json.dumps(sorted(i["id"] for i in ITEMS)).encode()).hexdigest())

    def test_distinctive_words_rank_their_label_first_and_k_is_five(self):
        model = assoc.Model(str(self.fit()))
        for words, label in (("knife", "IPC 100"), ("purse", "IPC 101"), ("cheating", "IPC 102"), ("robber", "IPC 104")):
            top = model.predict(words)
            self.assertEqual(top[0], label, words)
            self.assertEqual(len(top), 5)  # 6 labels in the fixture, top 5 returned

    def test_fit_is_byte_identical_and_a_changed_training_byte_changes_the_hash(self):
        a, b = self.fit("a.json"), self.fit("b.json")
        self.assertEqual(a.read_bytes(), b.read_bytes())
        other = self.write_split("train2.jsonl", [(i, [t.replace("purse", "pursf") for t in ts], ls) for i, ts, ls in TRAIN])
        self.assertNotEqual(bench.sha256(str(self.fit("c.json", other))), bench.sha256(str(a)))

    def test_layer_imports_only_the_standard_library_and_ibid(self):
        allowed = set(sys.stdlib_module_names) | {"ibid"}
        self.assertLessEqual(imports_of(Path(assoc.__file__).read_text()), allowed)
        self.assertFalse(imports_of("import requests\nfrom anthropic import x") <= allowed)  # the check can fail

    def test_predict_file_is_scored_by_the_one_scorer_and_bns_comes_only_from_verified_entries(self):
        model = self.fit()
        self.cli("assoc", "predict", "--model", str(model), "--set", str(self.set), "--concordance", str(self.tmp / "conc.json"),
                 "--index", str(self.tmp / "i.sqlite"), "--out", str(self.tmp / "p.json"))
        p = json.loads((self.tmp / "p.json").read_text())
        self.assertEqual((p["layer"], p["inputs"]["model"], p["set_sha256"]),
                         ("assoc-nb", bench.sha256(str(model)), hashlib.sha256(self.set.read_bytes()).hexdigest()))
        self.assertEqual(p["items"]["m1"]["ipc"][0], "IPC 100")  # query "murder"
        self.assertEqual(p["items"]["m1"]["bns"], ["BNS 200"])  # IPC 101 is also predicted but its entry is unverified
        self.assertNotIn("BNS 201", p["items"]["m2"]["bns"])
        self.cli("charges", "score", "--set", str(self.set), "--index", str(self.tmp / "i.sqlite"), "--predictions", str(self.tmp / "p.json"),
                 "--act", "ipc", "--out", str(self.tmp / "s.json"))
        self.assertEqual(json.loads((self.tmp / "s.json").read_text())["layer"], "assoc-nb")

    def eval(self, split, *extra, expect=0, ledger="ledger.json", out="e.json"):
        err = self.cli("assoc", "eval", "--model", str(self.tmp / "m.json"), "--split", str(split), "--manifest", str(self.tmp / "man.json"),
                       "--ledger", str(self.tmp / ledger), "--out", str(self.tmp / out), *extra, expect=expect)
        return json.loads((self.tmp / out).read_text()) if expect == 0 else err

    def test_eval_scores_with_the_benchmark_scorer_and_guards_the_test_split(self):
        self.fit()
        rows = [("d1", ["knife"], [100]), ("d2", ["purse"], [101]), ("d3", ["cheating"], [102])]
        dev, test = self.write_split("dev.jsonl", rows), self.write_split("test.jsonl", rows + [("d4", ["knife"], [100])])
        (self.tmp / "man.json").write_text(json.dumps({"test.jsonl": {"sha256": bench.sha256(str(test))}}))
        s = self.eval(dev)["scores"]  # each gold label is ranked first among 5 predictions: tp 3, fp 12; Jaccard 1/5 per case
        self.assertEqual((s["micro_f1"], s["jaccard"]), (round(6 / 18, 6), 0.2))
        self.assertFalse((self.tmp / "ledger.json").exists())  # dev never reaches the ledger
        self.assertEqual(len(self.eval(test)["test_scores"]), 1)
        self.assertIn("already scored", self.eval(test, expect=1))
        self.assertEqual(len(json.loads((self.tmp / "ledger.json").read_text())), 1)
        self.assertEqual(len(self.eval(test, "--rescore-test")["test_scores"]), 2)
        entry = json.loads((self.tmp / "ledger.json").read_text())[0]
        self.assertEqual((entry["layer"], entry["layer_version"], entry["split_sha256"]), ("assoc-nb", "v1", bench.sha256(str(test))))

    def test_test_split_copied_under_another_name_is_still_guarded(self):
        self.fit()
        test = self.write_split("test.jsonl", [("d1", ["knife"], [100])])
        copy = self.tmp / "renamed.jsonl"
        shutil.copy(test, copy)
        (self.tmp / "man.json").write_text(json.dumps({"test.jsonl": {"sha256": bench.sha256(str(test))}}))
        self.eval(copy)
        self.assertIn("already scored", self.eval(copy, expect=1))


if __name__ == "__main__":
    unittest.main()
