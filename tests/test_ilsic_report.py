import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RESULTS = [json.loads(p.read_text()) for p in sorted((ROOT / "results").glob("ilsic-*-*.json"))]
CAVEATS = ("primary reading", "secondary reading", "not independent evidence", "cc by-nc-sa 4.0", "legal accuracy", "zero-label")


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

    def test_report_holds_every_primary_micro_score(self):
        text = (ROOT / "results/ilsic-report.md").read_text()
        for r in RESULTS:
            self.assertIn(f"{r['primary']['micro_f1'] * 100:.2f}", text, (r["layer"], r["version"]))


if __name__ == "__main__":
    unittest.main()
