"""`ibid setup`: offline checklist of poppler tools and source PDFs. Makes no network call."""
import hashlib
import json
import shutil
from pathlib import Path

TOOLS = ["pdftotext", "pdftohtml", "pdfseparate", "pdfunite"]
INSTALL = ["  run: brew install poppler          (macOS)", "  run: apt install poppler-utils     (Debian)"]


def _fetch_hint(name: str) -> str:
    return "ibid setup --fetch bns" if name == "bns" else "ibid setup --fetch ipc --url <direct https PDF url>"


def run(sources: str, raw_dir: str) -> int:
    manifest = json.loads(Path(sources).read_text())
    ok = True
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
    return 0 if ok else 1
