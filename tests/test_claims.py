"""docs/claims.md quotes figures from result files. Each figure is recomputed here, so the document cannot drift from the results."""
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).parents[1]
DOC = (ROOT / "docs" / "claims.md").read_text()


def load(path: str):
    return json.loads((ROOT / path).read_text())


def pct(x: float) -> str:
    return f"{x * 100:.2f}"


def ledger(path: str, layer: str, version: str | None = None) -> dict:
    hits = [e for e in load(path) if e["layer"] == layer and (version is None or e["layer_version"] == version)]
    assert len(hits) == 1, f"{path}: expected one {layer} entry, found {len(hits)}"
    return hits[0]["scores"]


def best_ilsic_micro(split: str) -> float:
    return max(load(str(p.relative_to(ROOT)))["primary"]["micro_f1"] for p in (ROOT / "results").glob(f"ilsic-{split}-*.json"))


def figures() -> dict[str, float]:
    iltur, ilsi = load("results/iltur-lsi-test-linear-lr-v1-stats.json"), load("results/ilsi-test-linear-lr-v2-stats.json")
    conc = load("concordance/v3.json")
    return {
        "C2 IL-TUR macro-F1": ledger("results/test-ledger-iltur-assoc.json", "linear-lr", "v1")["macro_f1"],
        "C2 interval low": iltur["macro_f1_95ci"][0], "C2 interval high": iltur["macro_f1_95ci"][1],
        "C3 ILSI macro-F1": ledger("results/test-ledger-assoc.json", "linear-lr", "v2")["macro_f1"],
        "C3 interval low": ilsi["macro_f1_95ci"][0], "C3 interval high": ilsi["macro_f1_95ci"][1],
        "C4 ILSI baseline micro-F1": load("results/test-ledger.json")[0]["scores"]["micro_f1"],
        "C4 IL-TUR baseline micro-F1": load("results/test-ledger-iltur.json")[0]["scores"]["micro_f1"],
        "C5 IPC recall": load("results/multicharge-v2-assoc-v3-ipc.json")["output"]["recall"],
        "C5 BNS recall": load("results/multicharge-v2-assoc-v3-bns.json")["output"]["recall"],
        "C6 best Lay micro-F1": best_ilsic_micro("lay"), "C6 best Multi micro-F1": best_ilsic_micro("multi"),
    }


class ClaimsTest(unittest.TestCase):
    def test_every_figure_in_the_ledger_equals_its_result_file(self):
        for name, value in figures().items():
            with self.subTest(name):
                self.assertTrue(pct(value) in DOC, f"{name}: {pct(value)} is not in docs/claims.md")

    def test_concordance_counts_equal_the_pinned_file(self):
        conc = load("concordance/v3.json")
        want = f"{len(conc)} entries, {sum(1 for e in conc if e['verified'])} served"
        self.assertTrue(want in DOC, f"'{want}' is not in docs/claims.md")

    def test_the_document_names_what_it_may_not_claim(self):
        self.assertTrue("State of the art" in DOC and "The most complete" in DOC, "the may-not-claim section is missing")


if __name__ == "__main__":
    unittest.main()
