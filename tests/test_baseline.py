"""Ticket 08: the baseline is reproducible and the harness can fail. Scored mode, pinned gold."""
import json
import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from ibid import parse
from ibid.cli import main

ROOT = Path(__file__).parent.parent
GOLD, CONC, BASELINE = ROOT / "gold" / "v2.json", ROOT / "concordance" / "v2.json", ROOT / "results" / "baseline-v2.json"
from pdfs import BNS_PDF as PDF, IPC_PDF


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
        real = parse.body_lines

        def scrambled(path):  # words reversed inside BNS 85 only; its heading and the section count stay intact
            out, inside = [], False
            for line, indented in real(path):
                m = re.match(r"(\d+)\.", line)
                inside = m[1] == "85" if m else inside
                if inside:
                    head, _, rest = line.partition(" ") if m else ("", "", line)
                    line = f"{head} {' '.join(reversed(rest.split()))}".strip()
                out.append((line, indented))
            return out
        with mock.patch.object(parse, "body_lines", scrambled):
            code, out = self.run_scored()
        self.assertEqual(code, 0)
        passed = {o["id"]: o["pass"] for o in json.loads(out.read_text())["outcomes"]}
        self.assertFalse(passed["section_lookup-5"])  # BNS 85
        self.assertTrue(passed["section_lookup-1"])

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

    MODEL_PACKAGES = ("anthropic", "openai", "transformers", "sentence_transformers", "langchain", "requests", "httpx")

    @classmethod
    def model_uses(cls, lock: str, sources: dict[str, str], net_ok: tuple[str, ...] = ()) -> list[str]:
        """Model or network packages in the lock, or imported by any source file. Files named in net_ok may use stdlib network modules."""
        norm = lambda s: s.replace("-", "_")
        found = [f"uv.lock: {n}" for n in re.findall(r'^name = "([^"]+)"', lock, re.M) if norm(n) in cls.MODEL_PACKAGES]
        for path, src in sources.items():
            for mod in re.findall(r"^\s*(?:import|from)\s+([\w]+)", src, re.M):
                if norm(mod) in cls.MODEL_PACKAGES or (mod in ("urllib", "socket", "http") and not path.endswith(net_ok)):
                    found.append(f"{path}: {mod}")
        return found

    def test_no_model_is_a_dependency_or_an_import(self):
        # setup.py is the one network module: it downloads source PDFs, never calls a model (slice 10).
        sources = {str(p): p.read_text() for p in (ROOT / "src" / "ibid").glob("*.py")}
        self.assertEqual(self.model_uses((ROOT / "uv.lock").read_text(), sources, net_ok=("setup.py",)), [])

    def test_the_model_check_fails_on_a_known_bad_lock_and_import(self):
        bad = self.model_uses('name = "anthropic"\n', {"x.py": "def f():\n    import openai\n"})
        self.assertEqual(bad, ["uv.lock: anthropic", "x.py: openai"])
        bad = self.model_uses("", {"src/setup.py": "import openai\nimport urllib.request\n"}, net_ok=("setup.py",))
        self.assertEqual(bad, ["src/setup.py: openai"])


if __name__ == "__main__":
    unittest.main()
