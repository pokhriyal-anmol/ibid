"""Slice 3 ticket 08: the assoc-nb layer (`ibid assoc fit|predict|eval`). Invented fixtures, no real case text."""
import ast
import contextlib
import hashlib
import io
import json
import lzma
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

from ibid import assoc, bench, index
from ibid.cli import main
from ibid.parse import Provision
from test_charges_score import ITEMS, PROVS, charge, item

FIX = Path(__file__).parent / "fixtures"
V1_FIXTURE_SHA256 = "1588dba2f1832d167dbeecca51d5af3be4b58bd40e9228e3bbeaaa0c16d4a7f5"  # the v1 fit of TRAIN below, taken before the ilsic-lay path existed
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
        extra = [Provision(f"IPC {n}", "invented", None, ()) for n in ("34", "149", "120B")]  # in the index, yet never labels
        index.build(str(self.tmp / "i.sqlite"), PROVS + extra, []).close()
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
        words = (("knife", "IPC 100"), ("purse", "IPC 101"), ("cheating", "IPC 102"), ("robber", "IPC 104"))
        probe = self.tmp / "probe.json"
        items = [item(f"w{n}", w, [charge("any", [label], [])]) for n, (w, label) in enumerate(words)]
        probe.write_text(json.dumps({"version": "t", "created": "2026-10-12", "licence_note": "invented", "label_policy": "invented", "items": items}))
        probe.with_suffix(".sha256").write_text(hashlib.sha256(probe.read_bytes()).hexdigest() + "\n")
        self.cli("assoc", "predict", "--model", str(self.fit()), "--set", str(probe), "--concordance", str(self.tmp / "conc.json"),
                 "--index", str(self.tmp / "i.sqlite"), "--out", str(self.tmp / "probe-p.json"))
        got = json.loads((self.tmp / "probe-p.json").read_text())["items"]
        for n, (w, label) in enumerate(words):
            self.assertEqual(got[f"w{n}"]["ipc"][0], label, w)
            self.assertEqual(len(got[f"w{n}"]["ipc"]), 5, w)  # 6 labels in the fixture, top 5 returned

    def test_fit_is_byte_identical_and_a_changed_training_byte_changes_the_hash(self):
        a, b = self.fit("a.json"), self.fit("b.json")
        self.assertEqual(a.read_bytes(), b.read_bytes())
        other = self.write_split("train2.jsonl", [(i, [t.replace("purse", "pursf") for t in ts], ls) for i, ts, ls in TRAIN])
        self.assertNotEqual(bench.sha256(str(self.fit("c.json", other))), bench.sha256(str(a)))

    def fit_lay(self, out="v2.json", train=None, split=None, set_rows=(0, 2), expect=0):
        s = self.tmp / "lay-set.json"
        s.write_text(json.dumps({"items": [{"id": f"x{r}", "source": f"ILSIC Layman test split, row {r}"} for r in set_rows]}))
        err = self.cli("assoc", "fit", "--source", "ilsic-lay", "--train", str(train or FIX / "ilsic-lay-train.jsonl"),
                       "--holdout-split", str(split or FIX / "ilsic-lay-split.jsonl"), "--holdout-set", str(s),
                       "--min-posts", "2", "--index", str(self.tmp / "i.sqlite"), "--out", str(self.tmp / out), expect=expect)
        return self.tmp / out if expect == 0 else err

    def test_ilsic_lay_header_counts_equal_hand_computed(self):
        m = json.loads(self.fit_lay().read_text())
        h = m["header"]
        self.assertEqual((h["layer"], h["layer_version"], h["min_posts"], h["posts_read"], h["posts_fitted"]), ("assoc-nb", "v2", 2, 10, 5))
        self.assertEqual(h["posts_dropped"], {"held_out": 1, "no_offence_section": 3, "none_above_threshold": 1})
        self.assertEqual((h["other_act_citations_dropped"], h["vocabulary_size"]), (2, 2))
        self.assertEqual((h["train_sha256"], h["holdout_split_sha256"]),
                         (bench.sha256(str(FIX / "ilsic-lay-train.jsonl")), bench.sha256(str(FIX / "ilsic-lay-split.jsonl"))))
        self.assertEqual(m["docs"], {"IPC 100": 3, "IPC 101": 3})  # 102 has one post, under the threshold; 34, 149, 120B, CrPC never labels
        self.assertEqual(m["counts"]["IPC 100"], {"murder": 3, "man": 1, "knife": 2, "theft": 1})
        self.assertEqual(m["counts"]["IPC 101"], {"theft": 4, "purse": 2, "murder": 1})

    def test_ilsic_lay_post_equal_to_a_split_post_is_not_counted(self):
        m = json.loads(self.fit_lay().read_text())
        self.assertNotIn("stole", m["counts"]["IPC 101"], "held-out post 'A stranger  stole my PURSE' was fitted")
        self.assertEqual(m["header"]["posts_dropped"]["held_out"], 1)

    def test_ilsic_lay_refuses_a_set_item_whose_source_row_is_not_in_the_split(self):
        self.assertIn("source row", self.fit_lay(set_rows=(0, 3), expect=1))

    def test_ilsic_lay_fit_is_byte_identical_reads_xz_and_a_changed_byte_changes_the_hash(self):
        a, b = self.fit_lay("a.json"), self.fit_lay("b.json")
        self.assertEqual(a.read_bytes(), b.read_bytes())
        raw = (FIX / "ilsic-lay-train.jsonl").read_bytes()
        xz = self.tmp / "train.jsonl.xz"
        xz.write_bytes(lzma.compress(raw))
        self.assertEqual(json.loads(self.fit_lay("x.json", train=xz).read_text())["counts"], json.loads(a.read_text())["counts"])
        bad = self.tmp / "train2.jsonl"
        bad.write_bytes(raw.replace(b"cheating", b"cheatinf"))
        self.assertNotEqual(json.loads(self.fit_lay("c.json", train=bad).read_text())["header"]["train_sha256"],
                            json.loads(a.read_text())["header"]["train_sha256"])

    def test_v1_model_on_the_fixture_is_unchanged(self):
        self.assertEqual(bench.sha256(str(self.fit())), V1_FIXTURE_SHA256)

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
