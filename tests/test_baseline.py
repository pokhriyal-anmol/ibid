"""Ticket 08: the baseline is reproducible and the harness can fail. Scored mode, pinned gold."""
import dataclasses
import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from ibid import cli
from ibid.cli import main
from ibid.parse import parse_bns

ROOT = Path(__file__).parent.parent
GOLD, CONC, BASELINE = ROOT / "gold" / "v1.json", ROOT / "concordance" / "v1.json", ROOT / "results" / "baseline-v1.json"
PDF, IPC_PDF = os.environ["IBID_BNS_PDF"], os.environ["IBID_IPC_PDF"]


class BaselineTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp)
        self.base = json.loads(BASELINE.read_text())["categories"]

    def run_scored(self, name="r", pdf=PDF, conc=str(CONC)):
        out = self.tmp / f"{name}.json"
        code = main(["eval", "--gold", str(GOLD), "--bns", pdf, "--ipc", IPC_PDF, "--concordance", conc,
                     "--index", str(self.tmp / f"{name}.sqlite"), "--out", str(out)])
        return code, out

    def test_clean_run_reproduces_the_committed_baseline_byte_for_byte(self):
        code, out = self.run_scored()
        self.assertEqual(code, 0)
        self.assertEqual(out.read_bytes(), BASELINE.read_bytes())

    def test_scrambled_section_text_lowers_the_affected_category(self):
        def scrambled(path):
            ps = parse_bns(path)
            return [dataclasses.replace(p, text=" ".join(reversed(p.text.split()))) if p.citation == "BNS 85" else p for p in ps]
        with mock.patch.object(cli, "parse_bns", scrambled):
            code, out = self.run_scored()
        self.assertEqual(code, 0)
        got = json.loads(out.read_text())["categories"]
        self.assertLess(got["section_lookup"]["passed"], self.base["section_lookup"]["passed"])

    def test_wrong_concordance_mapping_lowers_the_correspondence_category(self):
        entries = json.loads(CONC.read_text())
        victim = next(e for e in entries if e["type"] == "one-to-one" and e["ipc"] == ["IPC 34"])
        victim["bns"] = ["BNS 1"]
        bad = self.tmp / "wrong-conc.json"
        bad.write_text(json.dumps(entries))
        code, out = self.run_scored(conc=str(bad))
        self.assertEqual(code, 0)
        got = json.loads(out.read_text())["categories"]
        self.assertLess(got["ipc_to_bns"]["passed"], self.base["ipc_to_bns"]["passed"])

    def test_pages_swapped_in_the_source_refuse_to_score_and_write_nothing(self):
        pages = self.tmp / "pages"
        pages.mkdir()
        subprocess.run(["pdfseparate", PDF, str(pages / "%03d.pdf")], check=True)
        order = list(range(1, len(list(pages.iterdir())) + 1))
        order[28], order[29] = order[29], order[28]
        swapped = self.tmp / "swapped.pdf"
        subprocess.run(["pdfunite", *[str(pages / f"{i:03d}.pdf") for i in order], str(swapped)], check=True)
        code, out = self.run_scored(pdf=str(swapped))
        self.assertEqual(code, 1)
        self.assertFalse(out.exists())

    def test_no_model_is_a_dependency(self):
        deps = (ROOT / "pyproject.toml").read_text()
        for name in ("anthropic", "openai", "transformers", "sentence-transformers", "langchain"):
            self.assertNotIn(name, deps)


if __name__ == "__main__":
    unittest.main()
