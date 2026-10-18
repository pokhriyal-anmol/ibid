"""`ibid setup`: offline checklist of poppler tools and source PDFs. Makes no network call."""
import hashlib
import json
import shlex
import shutil
from pathlib import Path

from ibid.ipc import parse_ipc
from ibid.parse import parse_bns

PARSERS = {"bns": parse_bns, "ipc": parse_ipc}
REPO = Path(__file__).resolve().parents[2]

TOOLS = ["pdftotext", "pdftohtml", "pdfseparate", "pdfunite"]
INSTALL = ["  run: brew install poppler          (macOS)", "  run: apt install poppler-utils     (Debian)"]


def _fetch_hint(name: str) -> str:
    return "ibid setup --fetch bns" if name == "bns" else "ibid setup --fetch ipc --url <direct https PDF url>"


def run(sources: str, raw_dir: str) -> int:
    manifest = json.loads(Path(sources).read_text())
    ok = True
    paths = {}
    for tool in TOOLS:
        found = shutil.which(tool)
        print(f"{'pass' if found else 'FAIL'}  tool {tool}" + (f" ({found})" if found else " not on PATH"))
        if not found:
            ok = False
            print("\n".join(INSTALL))
    for name, src in manifest.items():
        path = (Path(raw_dir) / src["file"]).resolve()
        if not path.is_file():
            ok = False
            print(f"FAIL  {name}: missing\n  get: {src['url']}\n  save as: {path}\n  or run: {_fetch_hint(name)}")
            continue
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        if actual != src["sha256"]:
            ok = False
            print(f"FAIL  {name}: present, hash differs (file not touched)\n  expected: {src['sha256']}\n  actual:   {actual}")
        else:
            print(f"pass  {name}: {path} hash ok")
            paths[name] = path
    if not ok:
        print("skip  parse not run: fix the failed checks above")
        return 1
    return _prove(manifest, paths)


def _prove(manifest: dict, paths: dict) -> int:
    """Parse each Act and compare its section count with the manifest; on success print the mcp line."""
    ok, counts = True, {}
    for name, src in manifest.items():
        counts[name] = sum(p.parent is None for p in PARSERS[name](str(paths[name])))
        good = counts[name] == src["sections"]
        ok = ok and good
        if not good:
            print(f"FAIL  {name}: parsed {counts[name]} sections, expected {src['sections']}")
    if not ok:
        return 1
    print(", ".join(f"{n.upper()} {c} sections" for n, c in counts.items()))
    print("\nAdd Ibid to Claude Code:\n" + " ".join(shlex.quote(x) for x in [
        "claude", "mcp", "add", "ibid", "--", "uv", "run", "--directory", str(REPO), "ibid", "mcp",
        "--bns", str(paths["bns"]), "--ipc", str(paths["ipc"]), "--concordance", str(REPO / "concordance/v3.json")]))
    return 0
