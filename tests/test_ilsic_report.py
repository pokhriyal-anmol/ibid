import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RESULTS = [json.loads(p.read_text()) for p in sorted((ROOT / "results").glob("ilsic-*-*.json"))]
CAVEATS = ("primary reading", "secondary reading", "not independent evidence", "cc by-nc-sa 4.0", "legal accuracy", "zero-label")


def primary_micro(benchmark: str, layer: str, version: str) -> str:
    """The micro-F1 cell (interval dropped) of the layer's row in the benchmark's primary-reading table."""
    text = (ROOT / "results/ilsic-report.md").read_text()
    section = next(s for s in text.split("\n## ") if re.match(rf".*\({benchmark},", s.splitlines()[0]))
    table = section.split("### Primary reading")[1].split("###")[0]
    rows = {c[0]: c for c in ([x.strip() for x in ln.strip("|").split("|")] for ln in table.splitlines() if ln.startswith("|"))}
    return rows.get(f"{layer} {version}", rows.get(layer))[2].split()[0]


class IlsicReport(unittest.TestCase):
    def test_ledger_has_one_look_per_result_file_and_none_twice(self):
        # ilsic eval refuses a second scoring (test_ilsic); this checks the committed ledger holds exactly the scored results
        ledger = json.loads((ROOT / "results/test-ledger-ilsic.json").read_text())
        keys = [(e["layer"], e["version"], e["split_sha256"]) for e in ledger]
        self.assertEqual(sorted(keys), sorted((r["layer"], r["version"], r["split_sha256"]) for r in RESULTS))
        self.assertEqual(len(keys), len(set(keys)))

    def test_report_states_caveats_and_both_readings(self):
        text = (ROOT / "results/ilsic-report.md").read_text().lower()
        for needle in CAVEATS:
            self.assertIn(needle, text)

    def test_report_holds_every_primary_micro_score_in_its_own_row(self):
        for r in RESULTS:
            row = primary_micro(r"ILSIC-" + r["benchmark"].capitalize(), r["layer"], r["version"])
            self.assertEqual(row, f"{r['primary']['micro_f1'] * 100:.2f}", (r["benchmark"], r["layer"], r["version"]))


if __name__ == "__main__":
    unittest.main()
