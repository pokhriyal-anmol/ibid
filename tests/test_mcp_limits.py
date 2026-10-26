"""The measured limits in the `search` description and the learned caveat are read-checked against results/layer-comparison.md."""
import json
import unittest
from pathlib import Path

from ibid import mcp
from mcp_harness import Client
from pdfs import _main_checkout
from test_mcp_learned import MODEL as INVENTED, with_model

ROOT = Path(__file__).parent.parent
REAL_MODEL = next((p for p in (ROOT / "data/assoc-nb-v3.json", _main_checkout() / "data/assoc-nb-v3.json") if p.exists()), ROOT / "data/assoc-nb-v3.json")


def rows(layer: str, version: str) -> dict[str, list[str]]:
    """set -> recall percents of that layer's IPC rows in layer-comparison.md, in file order."""
    out: dict[str, list[str]] = {}
    for line in (ROOT / "results/layer-comparison.md").read_text().splitlines():
        c = [x.strip() for x in line.split("|")]
        if len(c) > 9 and (c[1], c[2]) == (layer, version) and c[5] == "IPC" and " of " in c[7]:
            out.setdefault(c[3], []).append(c[8])
    return out


def expected() -> tuple[str, str]:
    kw, ln = rows("baseline", "v2.11"), rows("assoc-nb", "v3")
    lo, hi = (lambda s: min(kw[s], key=float)), (lambda s: max(kw[s], key=float))
    keyword = (f"Keyword search finds {lo('v1')} to {hi('v1')} percent of IPC charges on set v1 "
               f"and {lo('v2')} to {hi('v2')} percent on set v2 (story-style queries, measured per set).")
    (v1,), (v2,) = ln["v1"], ln["v2"]
    return keyword, ("Learned mode was fitted on court-judgment text and layperson forum posts, covers 140 IPC sections, "
                     f"finds {v2} percent of IPC charges on layperson posts (set v2) and {v1} percent on judgment text (set v1), "
                     "was measured on labels that are incomplete, and is not legal advice.")


class LimitsTest(unittest.TestCase):
    def test_tools_list_shows_mode_and_the_report_figures(self):
        c = Client()
        try:
            search = {t["name"]: t for t in c.request("tools/list")["result"]["tools"]}["search"]
        finally:
            c.close()
        self.assertEqual(search["inputSchema"]["properties"]["mode"]["enum"], ["keyword", "learned"])
        keyword, caveat = expected()
        self.assertIn(keyword, search["description"])
        self.assertIn(caveat, search["description"])

    def test_learned_call_returns_the_fixed_caveat(self):
        c = with_model(INVENTED)
        try:
            out = c.call("search", {"query": "murder", "mode": "learned"})["result"]["structuredContent"]
        finally:
            c.close()
        self.assertEqual(out["caveat"], expected()[1])

    @unittest.skipUnless(REAL_MODEL.exists(), f"{REAL_MODEL} absent: the section-count check needs the fitted model")
    def test_section_count_is_the_models_label_count(self):
        n = len(json.loads(REAL_MODEL.read_text())["docs"])
        self.assertIn(f"covers {n} IPC sections", mcp.CAVEAT)
