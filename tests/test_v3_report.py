import hashlib
import json
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SCRIPT = REPO / ".scratch/slice-9/v3-report.py"
MODEL = {"header": {"vocabulary_size": 7, "min_examples": 5,
                    "sources": {"ilsi": {"examples_used": 90}, "ilsic-lay": {"examples_used": 10}}}, "docs": {}, "counts": {}}
V2 = {"v1": {"ipc": 0.153, "bns": 0.163}, "v2": {"ipc": 0.548, "bns": 0.642}}
V3 = {"v1": {"ipc": 0.40, "bns": 0.30}, "v2": {"ipc": 0.50, "bns": 0.60}}


def build(root: Path, v3: dict, f1: float | None = 0.34) -> None:
    (root / "data").mkdir()
    (root / "results/layers").mkdir(parents=True)
    model = json.dumps(MODEL)
    (root / "data/assoc-nb-v3.json").write_text(model)
    sha = hashlib.sha256(model.encode()).hexdigest()
    for s in V2:
        for act in ("ipc", "bns"):
            for name, fig in ((f"multicharge-{s}-assoc-v2-{act}", V2), (f"multicharge-{s}-assoc-v3-{act}", v3)):
                doc = {"output": {"recall": fig[s][act]}, "inputs": {"layer": {"model": sha}}}
                (root / f"results/{name}.json").write_text(json.dumps(doc))
    (root / "results/layers/assoc-nb-v1-test.json").write_text(json.dumps({"scores": {"micro_f1": 0.3538}}))
    if f1 is not None:
        (root / "results/layers/assoc-nb-v3-test.json").write_text(json.dumps(
            {"scores": {"micro_f1": f1}, "micro_f1_by_label_space": {"own": {"labels": 140, "micro_f1": f1}, "v1": {"labels": 600, "micro_f1": 0.2}}}))


def report(v3: dict, f1: float | None = 0.34) -> str:
    with tempfile.TemporaryDirectory() as d:
        build(Path(d), v3, f1)
        r = subprocess.run([sys.executable, str(SCRIPT), d], capture_output=True, text=True)
        assert r.returncode == 0, r.stderr
        return r.stdout


class V3Report(unittest.TestCase):
    def test_kept_when_all_hold(self) -> None:
        out = report(V3)
        self.assertEqual(out.count("| pass |"), 5)
        self.assertIn("Verdict: **kept**", out)
        self.assertIn("140 labels: 34.0", out)
        self.assertIn("ilsi 90 (90.0%)", out)

    def test_equal_to_v2_on_set_v1_ipc_fails_the_line_and_the_verdict(self) -> None:
        out = report({**V3, "v1": {"ipc": 0.153, "bns": 0.30}})
        self.assertIn("| above 15.3 | 15.3 | fail |", out)
        self.assertIn("Verdict: **negative**", out)

    def test_low_micro_f1_is_negative_and_missing_is_undecided(self) -> None:
        self.assertIn("Verdict: **negative**", report(V3, 0.30))
        self.assertIn("Verdict: **not yet decided**", report(V3, None))

    def test_thresholds_match_adr_0008_and_output_is_repeatable(self) -> None:
        out = report(V3)
        adr = next((REPO / "docs/adr").glob("0008*")).read_text()
        rule = re.findall(r"\| \d \| .*? \| (?:above|at least) ([\d.]+)", adr)
        self.assertEqual(rule, ["15.3", "16.3", "49.8", "59.2", "33.4"])
        self.assertEqual(re.findall(r"(?:above|at least) ([\d.]+) \|", out), rule)
        self.assertEqual(out, report(V3))

    def test_refuses_a_model_that_did_not_make_the_results(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            build(Path(d), V3)
            (Path(d) / "data/assoc-nb-v3.json").write_text(json.dumps({**MODEL, "docs": {"x": 1}}))
            r = subprocess.run([sys.executable, str(SCRIPT), d], capture_output=True, text=True)
            self.assertNotEqual(r.returncode, 0)


if __name__ == "__main__":
    unittest.main()
