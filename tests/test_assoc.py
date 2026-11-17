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
            out.add("ibid" if n.level else n.module.split(".")[0])  # a relative import is inside the package
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
        p.write_text("".join(json.dumps({"id": i, "text": t, "labels": [LABELS.get(n) or f"Section {n} in The Indian Penal Code" for n in ls]}) + "\n" for i, t, ls in rows))
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

    def fit_v3(self, out="v3.json", ilsi_rows=TRAIN, min_examples=1, ilsi_set=None, labels=None):
        s = self.tmp / "lay-set.json"
        s.write_text(json.dumps({"items": [{"id": f"x{r}", "source": f"ILSIC Layman test split, row {r}"} for r in (0, 2)]}))
        self.cli("assoc", "fit", "--source", "union", "--train", str(self.write_split("ilsi-u.jsonl", ilsi_rows)),
                 "--holdout-set", str(ilsi_set or self.set), "--labels", str(labels or self.tmp / "labels.json"),
                 "--lay-train", str(FIX / "ilsic-lay-train.jsonl"), "--holdout-split", str(FIX / "ilsic-lay-split.jsonl"),
                 "--lay-holdout-set", str(s), "--min-posts", str(min_examples), "--index", str(self.tmp / "i.sqlite"), "--out", str(self.tmp / out))
        return json.loads((self.tmp / out).read_text())

    def test_v3_header_names_both_sources_and_counts_are_the_sum_of_the_two_single_fits(self):
        m, v1 = self.fit_v3(), json.loads(self.fit().read_text())
        v2 = json.loads(self.fit_lay_min1().read_text())
        h = m["header"]
        self.assertEqual((h["layer"], h["layer_version"], h["min_examples"], h["vocabulary_size"]), ("assoc-nb", "v3", 1, len(m["docs"])))
        self.assertEqual(h["sources"]["ilsi"], {"train_sha256": bench.sha256(str(self.tmp / "ilsi-u.jsonl")), "examples_used": 7,
                                                "examples_dropped": {"held_out": 1, "no_offence_section": 0, "none_above_threshold": 0}})
        lay = h["sources"]["ilsic-lay"]
        self.assertEqual((lay["train_sha256"], lay["examples_used"], lay["examples_dropped"]),
                         (bench.sha256(str(FIX / "ilsic-lay-train.jsonl")), 6, {"held_out": 1, "no_offence_section": 3, "none_above_threshold": 0}))
        for c, terms in m["counts"].items():
            want = {t: v1["counts"].get(c, {}).get(t, 0) + v2["counts"].get(c, {}).get(t, 0) for t in set(v1["counts"].get(c, {})) | set(v2["counts"].get(c, {}))}
            self.assertEqual(terms, want, c)
            self.assertEqual(m["docs"][c], v1["docs"].get(c, 0) + v2["docs"].get(c, 0), c)

    def fit_lay_min1(self):
        s = self.tmp / "lay-set1.json"
        s.write_text(json.dumps({"items": [{"id": f"x{r}", "source": f"ILSIC Layman test split, row {r}"} for r in (0, 2)]}))
        self.cli("assoc", "fit", "--source", "ilsic-lay", "--train", str(FIX / "ilsic-lay-train.jsonl"), "--holdout-split", str(FIX / "ilsic-lay-split.jsonl"),
                 "--holdout-set", str(s), "--min-posts", "1", "--index", str(self.tmp / "i.sqlite"), "--out", str(self.tmp / "v2m1.json"))
        return self.tmp / "v2m1.json"

    @staticmethod
    def leaked(m):
        """Terms of held-out items found in the model: set v1's m1 'zebra' (IPC 101) and the Layman test post 'stole'."""
        return [t for c, terms in m["counts"].items() for t in terms if (t == "zebra" and c == "IPC 101") or t == "stole"]

    def test_v3_training_data_holds_no_held_out_id_and_the_check_can_fail(self):
        self.assertEqual(self.leaked(self.fit_v3()), [], "a held-out item leaked into the v3 training data")
        empty = self.tmp / "empty-set.json"
        empty.write_text(json.dumps({"items": []}))  # known-bad: the set v1 drop removed
        self.assertEqual(self.leaked(self.fit_v3("bad.json", ilsi_set=empty)), ["zebra"])

    def test_v3_threshold_is_on_the_union_and_34_149_120b_never_appear(self):
        labels = self.tmp / "labels2.json"
        labels.write_text(json.dumps({f"Section {n} in The Indian Penal Code": i for i, n in enumerate([*range(100, 106), 34, 149, "120B"])}))
        # IPC 103: a5 + 3 = 4 union examples; IPC 104: a6 + 4 = 5.
        rows = [*TRAIN, *((f"b{n}", ["x"], [103]) for n in range(3)), *((f"c{n}", ["y"], [104]) for n in range(4)),
                *((f"{k}{n}", ["common"], [k, 100]) for k in (34, 149, "120B") for n in range(5)), ("e1", ["alone"], [34])]
        m = self.fit_v3("t.json", ilsi_rows=rows, min_examples=5, labels=labels)
        self.assertNotIn("IPC 103", m["docs"], "a section with 4 union examples was included")
        self.assertEqual(m["docs"]["IPC 104"], 5)
        self.assertTrue({"IPC 34", "IPC 149", "IPC 120B"}.isdisjoint(m["docs"]), m["docs"])
        self.assertEqual(m["header"]["vocabulary_size"], len(m["docs"]))
        src = m["header"]["sources"]
        self.assertEqual((src["ilsi"]["examples_used"], src["ilsi"]["examples_dropped"]), (23, {"held_out": 1, "no_offence_section": 1, "none_above_threshold": 6}))
        self.assertEqual((src["ilsic-lay"]["examples_used"], src["ilsic-lay"]["examples_dropped"]["none_above_threshold"]), (5, 1))

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

    def predict_scored(self, model, name):
        self.cli("assoc", "predict", "--model", str(model), "--set", str(self.set), "--concordance", str(self.tmp / "conc.json"),
                 "--index", str(self.tmp / "i.sqlite"), "--out", str(self.tmp / f"{name}.json"))
        self.cli("charges", "score", "--set", str(self.set), "--index", str(self.tmp / "i.sqlite"), "--predictions", str(self.tmp / f"{name}.json"),
                 "--act", "ipc", "--out", str(self.tmp / f"{name}-s.json"), "--ledger", str(self.tmp / f"{name}-l.json"))
        return json.loads((self.tmp / f"{name}.json").read_text())

    def test_predict_names_the_layer_version_and_train_source_from_the_model_header(self):
        model = self.fit_lay()
        p = self.predict_scored(model, "p2")  # the scorer validated this file
        self.assertEqual((p["layer"], p["layer_version"], p["inputs"]["model"]), ("assoc-nb", "v2", bench.sha256(str(model))))
        self.assertEqual((p["inputs"]["train_sha256"], p["inputs"]["train_source"]),
                         (bench.sha256(str(FIX / "ilsic-lay-train.jsonl")), "ilsic-lay"))
        p1 = self.predict_scored(self.fit(), "p1")
        self.assertEqual((p1["layer_version"], p1["inputs"]["train_source"]), ("v1", "ilsi"))
        self.assertEqual(p1["inputs"]["train_sha256"], bench.sha256(str(self.train)))

    def score_v3(self, pred, name, ledger="v3.ledger.json", expect=0, *extra):
        return self.cli("charges", "score", "--set", str(self.set), "--index", str(self.tmp / "i.sqlite"), "--predictions", str(pred),
                        "--act", "ipc", "--out", str(self.tmp / name), "--ledger", str(self.tmp / ledger), *extra, expect=expect)

    def test_predict_v3_names_layer_version_hash_and_both_train_sources(self):
        model = self.fit_v3()
        h = json.loads((self.tmp / "v3.json").read_text())["header"]["sources"]
        p = self.predict_scored(self.tmp / "v3.json", "pv3")
        self.assertEqual((p["layer"], p["layer_version"], p["inputs"]["model"], p["inputs"]["train_source"]),
                         ("assoc-nb", "v3", bench.sha256(str(self.tmp / "v3.json")), "ilsi+ilsic-lay"))
        self.assertEqual((p["inputs"]["train_sha256_ilsi"], p["inputs"]["train_sha256_ilsic-lay"]),
                         (h["ilsi"]["train_sha256"], h["ilsic-lay"]["train_sha256"]))

    def test_scorer_refuses_a_predictions_file_whose_version_is_not_the_one_in_its_results_name(self):
        self.fit_v3()
        self.predict_scored(self.tmp / "v3.json", "pv3")
        pred = self.tmp / "pv3.json"
        d = json.loads(pred.read_text())
        d["layer_version"] = "v2"  # known-bad: a v2 file offered as the v3 results
        bad = self.tmp / "bad.json"
        bad.write_text(json.dumps(d))
        err = self.score_v3(bad, "multicharge-v1-assoc-v3-ipc.json", "bad.ledger.json", 1)
        self.assertIn("v3", err)
        self.assertFalse((self.tmp / "multicharge-v1-assoc-v3-ipc.json").exists())
        self.score_v3(pred, "multicharge-v1-assoc-v3-ipc.json", "ok.ledger.json")

    def test_a_v3_file_scored_twice_is_refused_unless_rescore(self):
        self.fit_v3()
        self.predict_scored(self.tmp / "v3.json", "pv3")
        self.score_v3(self.tmp / "pv3.json", "a.json")
        led = (self.tmp / "v3.ledger.json").read_bytes()
        self.assertIn("already scored", self.score_v3(self.tmp / "pv3.json", "b.json", "v3.ledger.json", 1))
        self.assertEqual((self.tmp / "v3.ledger.json").read_bytes(), led)
        self.score_v3(self.tmp / "pv3.json", "c.json", "v3.ledger.json", 0, "--rescore")

    def eval(self, split, *extra, expect=0, ledger="ledger.json", out="e.json", model="m.json"):
        err = self.cli("assoc", "eval", "--model", str(self.tmp / model), "--split", str(split), "--manifest", str(self.tmp / "man.json"),
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

    def v3_test_split(self):
        rows = [("d1", ["knife"], [100]), ("d2", ["purse"], [101]), ("d3", ["cheating"], [102]), ("d4", ["knife"], [100]),
                ("d5", ["zebra"], [105])]  # d5's label is in v1's space but not in v3's
        test = self.write_split("test.jsonl", rows)
        (self.tmp / "man.json").write_text(json.dumps({"test.jsonl": {"sha256": bench.sha256(str(test))}}))
        return test

    def test_v3_eval_ledger_names_v3_and_the_model_hash_and_a_second_run_is_refused(self):
        self.fit_v3(min_examples=2)
        test, labels = self.v3_test_split(), str(self.tmp / "labels.json")
        self.eval(test, "--labels", labels, model="v3.json")
        self.assertIn("already scored", self.eval(test, "--labels", labels, model="v3.json", expect=1))
        (entry,) = json.loads((self.tmp / "ledger.json").read_text())
        self.assertEqual((entry["layer_version"], entry["model_sha256"]), ("v3", bench.sha256(str(self.tmp / "v3.json"))))

    def test_v3_eval_carries_micro_f1_over_its_own_and_over_v1_label_space_each_with_its_size(self):
        self.fit_v3(min_examples=2)
        labels = str(self.tmp / "labels.json")
        res = self.eval(self.v3_test_split(), "--labels", labels, model="v3.json")
        # v3 keeps 3 labels, so each of the 5 cases gets all 3 as predictions (15). d1 to d4 are right in both spaces (tp 4, fp 11).
        # Own space: d5's zebra is outside it, fn 0, F1 = 8/19. v1's 6-label space counts d5 as a miss, fn 1, F1 = 8/20.
        self.assertEqual(res["micro_f1_by_label_space"], {"own": {"labels": 3, "micro_f1": round(8 / 19, 6)},
                                                          "v1": {"labels": 6, "micro_f1": 0.4}})
        self.assertEqual(res["scores"]["micro_f1"], round(8 / 19, 6))  # the rule's figure
        self.assertEqual(json.loads((self.tmp / "ledger.json").read_text())[0]["micro_f1_by_label_space"], res["micro_f1_by_label_space"])

    def test_v3_entry_leaves_the_v1_and_v2_ledger_entries_byte_for_byte(self):
        self.fit_v3(min_examples=2)
        old = [{"cases": 1, "layer": "assoc-nb", "layer_version": v, "model_sha256": "x", "scores": {"micro_f1": 0.5}, "split_sha256": "y"} for v in ("v1", "v2")]
        text = json.dumps(old, indent=2, sort_keys=True) + "\n"
        (self.tmp / "ledger.json").write_text(text)
        self.eval(self.v3_test_split(), "--labels", str(self.tmp / "labels.json"), model="v3.json")
        new = (self.tmp / "ledger.json").read_text()
        self.assertEqual(len(json.loads(new)), 3)
        self.assertTrue(new.startswith(text[:-3]))  # the first two entries are the same bytes, the list just grows

    def test_v1_eval_scores_do_not_change_with_or_without_the_label_space_option(self):
        self.fit()
        dev = self.write_split("dev.jsonl", [("d1", ["knife"], [100]), ("d2", ["purse"], [101])])
        a = self.eval(dev)["scores"]
        b = self.eval(dev, "--labels", str(self.tmp / "labels.json"))
        self.assertEqual(a, b["scores"])
        self.assertEqual(b["micro_f1_by_label_space"]["own"], b["micro_f1_by_label_space"]["v1"])


if __name__ == "__main__":
    unittest.main()
