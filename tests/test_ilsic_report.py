import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def ledger_keys(entries: list[dict]) -> list[tuple]:
    return [(e["layer"], e["version"], e["split_sha256"]) for e in entries]


class IlsicReport(unittest.TestCase):
    def test_ledger_has_one_look_per_layer_version_and_split(self):
        keys = ledger_keys(json.loads((ROOT / "results/test-ledger-ilsic.json").read_text()))
        self.assertEqual(len(keys), 12)  # 6 layers x 2 splits
        self.assertEqual(len(keys), len(set(keys)))

    def test_duplicate_entry_is_caught(self):  # known-bad input for the check above
        e = {"layer": "a", "version": "v1", "split_sha256": "x"}
        keys = ledger_keys([e, e])
        self.assertNotEqual(len(keys), len(set(keys)))

    def test_report_states_caveats_and_both_readings(self):
        text = (ROOT / "results/ilsic-report.md").read_text().lower()
        for needle in ("primary reading", "secondary reading", "not independent evidence", "cc by-nc-sa 4.0", "legal accuracy", "zero-label"):
            self.assertIn(needle, text)


if __name__ == "__main__":
    unittest.main()
