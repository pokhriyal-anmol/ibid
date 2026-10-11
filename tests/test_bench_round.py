"""Slice 2 ticket 08: optimisation rounds, the log and the stopping rule. Invented fixture only."""
import contextlib
import io
import json
import shutil
import tempfile
import unittest
from pathlib import Path

from ibid import bench, index, optimise
from ibid.cli import main
from ibid.parse import Provision


def prov(cite, text):
    return Provision(cite, text, None, ())


PROVISIONS = [prov("IPC 1", "theft of movable property"), prov("IPC 2", "murder causing death"),
              prov("IPC 3", "cheating deceiving by personation"), prov("IPC 4", "kidnapping from lawful guardianship")]
L = {n: f"Section {n} in The Indian Penal Code" for n in (1, 2, 3, 4)}
CASES = [
    {"id": "s1", "text": ["theft of movable property murder"], "labels": [L[1]]},
    {"id": "m1", "text": ["cheating deceiving personation kidnapping"], "labels": [L[3], L[4]]},
    {"id": "s2", "text": ["murder causing death"], "labels": [L[2]]},
]


def quiet(argv):
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = main(argv)
    return code, out.getvalue(), err.getvalue()


class RoundTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp)
        index.build(str(self.tmp / "i.sqlite"), PROVISIONS, []).close()
        (self.tmp / "labels.json").write_text(json.dumps({label: i for i, label in enumerate(L.values())}))
        self.log = self.tmp / "log.json"
        self.write("train.jsonl", CASES)
        self.write("dev.jsonl", CASES)

    def write(self, name, cases):
        (self.tmp / name).write_text("".join(json.dumps(c) + "\n" for c in cases))

    def manifest(self, extra=()):
        names = ("train.jsonl", "dev.jsonl", "labels.json", *extra)
        path = self.tmp / "manifest.json"
        path.write_text(json.dumps({n: {"sha256": bench.sha256(str(self.tmp / n))} for n in names}))
        return str(path)

    def round(self, *changes, k=None, r=None, train="train.jsonl", dev="dev.jsonl", manifest=None):
        argv = ["bench", "round", "--train", str(self.tmp / train), "--dev", str(self.tmp / dev),
                "--labels", str(self.tmp / "labels.json"), "--index", str(self.tmp / "i.sqlite"),
                "--manifest", manifest or self.manifest(), "--log", str(self.log)]
        for c in changes:
            argv += ["--change", c]
        for flag, v in (("--k", k), ("--r", r)):
            argv += [flag, str(v)] if v is not None else []
        return quiet(argv)

    def rounds(self):
        return json.loads(self.log.read_text())["rounds"]

    def start(self, k=1, r=0.5):
        self.assertEqual(self.round(k=k, r=r)[0], 0)

    def single_run(self, k, r, rollup="max"):
        out = self.tmp / "single.json"
        code, _, _ = quiet(["bench", "run", "--split", str(self.tmp / "dev.jsonl"), "--labels", str(self.tmp / "labels.json"),
                            "--index", str(self.tmp / "i.sqlite"), "--k", str(k), "--r", str(r), "--rollup", rollup,
                            "--out", str(out), "--manifest", self.manifest()])
        self.assertEqual(code, 0)
        return json.loads(out.read_text())

    def test_logged_rounds_match_independent_single_runs(self):
        self.start()
        for change in ("k=2", "r=0.9", "rollup=sum"):
            self.assertEqual(self.round(change)[0], 0)
        entries = self.rounds()
        self.assertEqual([e["round"] for e in entries], [0, 1, 2, 3])
        self.assertEqual([e["knob"] for e in entries], [None, "k", "r", "rollup"])
        self.assertEqual([e["rule"]["version"] for e in entries], ["v1", "v1.1", "v1.2", "v1.3"])
        for e in entries:
            p = e["params"]
            single = self.single_run(p["k"], p["r"], p["rollup"])
            self.assertEqual(e["dev"]["top_k"]["scores"], single["scores"])
            self.assertEqual(e["dev"]["top_k"]["strata"], single["strata"])
            self.assertEqual(e["dev"]["threshold"]["scores"], single["threshold"]["scores"])
            self.assertEqual(e["rule"]["params_sha256"], single["rule"]["params_sha256"])
            self.assertEqual(e["gap"]["macro_f1"], round(e["train"]["top_k"]["scores"]["macro_f1"]
                                                         - e["dev"]["top_k"]["scores"]["macro_f1"], 6))
        self.assertEqual(len({e["rule"]["params_sha256"] for e in entries}), 4)
        self.assertEqual(entries[1]["dev"]["top_k"]["scores"]["macro_f1"], round(11 / 12, 6))  # hand-computed: k=2 adds one false IPC 2 for s1

    def use(self, provisions, cases):
        (self.tmp / "i.sqlite").unlink()
        index.build(str(self.tmp / "i.sqlite"), provisions, []).close()
        self.write("train.jsonl", cases)
        self.write("dev.jsonl", cases)

    def test_one_stop_word_change_alters_query_score_and_hash(self):
        self.use(PROVISIONS, [{"id": "t", "text": ["theft"], "labels": [L[1]]}])
        self.start(k=1)
        before = self.rounds()[0]
        self.assertEqual(before["dev"]["top_k"]["scores"]["micro_f1"], 1.0)
        self.assertEqual(self.round("stop_words=+theft")[0], 0)
        after = self.rounds()[1]
        self.assertEqual(after["dev"]["top_k"]["scores"]["micro_f1"], 0.0)  # the query is now empty
        self.assertIn("theft", after["params"]["stop_words"])
        self.assertEqual(len(after["params"]["stop_words"]), len(before["params"]["stop_words"]) + 1)
        self.assertEqual(after["rule"]["params_sha256"], bench.rule_hash(1, 0.5, "max", after["params"]["stop_words"]))
        self.assertEqual(self.round("stop_words=-theft")[0], 0)
        back = self.rounds()[2]
        self.assertEqual(back["rule"]["params_sha256"], before["rule"]["params_sha256"])
        self.assertEqual(back["dev"]["top_k"]["scores"], before["dev"]["top_k"]["scores"])

    def test_rollup_round_changes_the_logged_score(self):
        # sections 6 and 7 tie under max (top-1 is the lowest citation, 6); under sum 7 scores twice 6
        provisions = [prov("IPC 6", "robbery violence"), Provision("IPC 7", "violence", None, ("IPC 7(a)", "IPC 7(b)")),
                      Provision("IPC 7(a)", "robbery violence", "IPC 7", ()),
                      Provision("IPC 7(b)", "robbery violence", "IPC 7", ())]
        labels = {f"Section {n} in The Indian Penal Code": n for n in (6, 7)}
        (self.tmp / "labels.json").write_text(json.dumps(labels))
        self.use(provisions, [{"id": "t", "text": ["robbery"], "labels": ["Section 7 in The Indian Penal Code"]}])
        self.start(k=1)
        self.assertEqual(self.round("rollup=sum")[0], 0)
        r0, r1 = self.rounds()
        self.assertEqual((r0["dev"]["top_k"]["scores"]["micro_f1"], r1["dev"]["top_k"]["scores"]["micro_f1"]), (0.0, 1.0))

    def test_refused_rounds_leave_the_log_untouched(self):
        self.start()
        raw = self.log.read_bytes()
        bad = [("k=2", "r=0.9"), ("label_prior=on",), ("tokenisation=letters",), ("stop_words=+a,b",),
               ("stop_words=the,of",), ("k=1",), ("k=0",), ("r=2",), ("rollup=median",), ("k",)]
        for changes in bad:
            code, _, err = self.round(*changes)
            self.assertEqual((changes, code), (changes, 1))
            self.assertIn("error:", err)
            if changes == ("label_prior=on",):
                self.assertIn("not a declared knob", err)
            self.assertEqual(self.log.read_bytes(), raw, changes)
        self.assertEqual(self.round()[0], 1)  # a later round with no change at all

    def test_round_zero_is_the_unmodified_rule(self):
        self.assertEqual(self.round("k=2", k=1, r=0.5)[0], 1)
        self.assertEqual(self.round()[0], 1)  # no k and r
        self.assertFalse(self.log.exists())

    def test_three_sub_bar_dev_gains_report_saturation(self):
        self.start()
        flags = []
        for word in ("foo", "bar", "baz"):
            self.assertEqual(self.round(f"stop_words=+{word}")[0], 0)
            flags.append(self.rounds()[-1]["status"]["saturated"])
        self.assertEqual(flags, [False, False, True])
        self.assertIn("'saturated': True", self.round("stop_words=+qux")[1])

    def test_stopping_status_cap_and_overfit_on_synthetic_logs(self):
        def rounds(dev, train):
            return [{"dev": {"top_k": {"scores": {"macro_f1": d}}}, "train": {"top_k": {"scores": {"macro_f1": t}}}}
                    for d, t in zip(dev, train)]
        climbing = [round(0.1 + 0.01 * i, 6) for i in range(21)]  # every gain is 1 point: not saturated
        s = optimise.stopping_status(rounds(climbing[:20], climbing[:20]))
        self.assertEqual((s["cap_reached"], s["saturated"]), (False, False))  # 19 rounds after round 0
        s = optimise.stopping_status(rounds(climbing, climbing))
        self.assertEqual((s["cap_reached"], s["saturated"], s["overfitting"]), (True, False, False))
        dev = [0.2, 0.25, 0.24, 0.23]
        train = [0.2, 0.3, 0.35, 0.4]
        self.assertTrue(optimise.stopping_status(rounds(dev, train))["overfitting"])
        self.assertFalse(optimise.stopping_status(rounds(dev, [0.2, 0.3, 0.35, 0.35]))["overfitting"])  # train flat
        self.assertFalse(optimise.stopping_status(rounds([0.2, 0.25, 0.3, 0.35], train))["overfitting"])  # dev rising
        s = optimise.stopping_status(rounds([0.2, 0.2, 0.2, 0.2], [0.2] * 4))
        self.assertTrue(s["saturated"])
        self.assertFalse(optimise.stopping_status(rounds([0.2, 0.2, 0.3, 0.3], [0.2] * 4))["saturated"])  # streak broken

    def test_round_that_hurts_single_label_cases_is_flagged(self):
        self.start(k=1)
        self.assertEqual(self.round("k=2")[0], 0)
        r0, r1 = self.rounds()
        self.assertGreater(r1["dev"]["top_k"]["scores"]["macro_f1"], r0["dev"]["top_k"]["scores"]["macro_f1"])
        single = lambda e: e["dev"]["top_k"]["strata"]["gold_label_count"]["1"]["scores"]["micro_f1"]
        self.assertGreater(single(r0) - single(r1), 0.005)
        self.assertEqual((r0["flags"], r1["flags"]), ([], ["hurts-simple"]))
        self.assertFalse(optimise.freezable(r1))
        self.assertTrue(optimise.freezable({**r1, "owner_approved": True}))
        self.assertTrue(optimise.freezable(r0))

    def test_test_split_is_never_read(self):
        self.write("test.jsonl", CASES)
        self.write("heldout.jsonl", [{"id": "t", "text": ["murder"], "labels": [L[2]]}])
        by_name = self.round(k=1, r=0.5, dev="test.jsonl", manifest=self.manifest(("test.jsonl",)))
        self.assertEqual(by_name[0], 1)
        self.assertIn("never read", by_name[2])
        # renamed copy of the pinned test file is caught by its hash
        shutil.copy(self.tmp / "test.jsonl", self.tmp / "renamed.jsonl")
        mf = json.loads(Path(self.manifest(("test.jsonl", "renamed.jsonl"))).read_text())
        mf["test.jsonl"]["sha256"] = bench.sha256(str(self.tmp / "renamed.jsonl"))
        (self.tmp / "m2.json").write_text(json.dumps(mf))
        by_hash = self.round(k=1, r=0.5, dev="renamed.jsonl", manifest=str(self.tmp / "m2.json"))
        self.assertEqual(by_hash[0], 1)
        self.assertIn("never read", by_hash[2])
        self.assertFalse(self.log.exists())

    def test_changed_data_byte_is_refused(self):
        manifest = self.manifest()
        self.write("dev.jsonl", CASES[:2])
        code, _, err = self.round(k=1, r=0.5, manifest=manifest)
        self.assertEqual(code, 1)
        self.assertIn("dev.jsonl", err)
        self.assertFalse(self.log.exists())


if __name__ == "__main__":
    unittest.main()
