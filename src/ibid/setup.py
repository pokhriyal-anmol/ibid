"""`ibid setup`: offline checklist of poppler tools and source PDFs. Makes no network call."""
import hashlib
import http.client
import json
import shlex
import os
import shutil
import sys
import tempfile
import urllib.request
from pathlib import Path
from urllib.parse import urlparse

from ibid.ipc import parse_ipc
from ibid.parse import parse_bns

PARSERS = {"bns": parse_bns, "ipc": parse_ipc}
REPO = Path(__file__).resolve().parents[2]

MODEL = REPO / "data/assoc-nb-v3.json"
FIT = "ibid assoc fit --source union ... --out data/assoc-nb-v3.json (see README, Learned mode)"
TOOLS = ["pdftotext", "pdftohtml", "pdfseparate", "pdfunite"]
INSTALL = ["  run: brew install poppler          (macOS)", "  run: apt install poppler-utils     (Debian)"]


def _fetch_hint(name: str) -> str:
    return "ibid setup --fetch ipc --url <direct https PDF url>" if name == "ipc" else f"ibid setup --fetch {name}"


CAP = 200 * 1024 * 1024
IPC_NEEDS_URL = ("error: --fetch ipc needs --url. The WIPO link is signed and expires, so get a direct PDF URL "
                 "from the WIPO Lex page ({page}) and pass it with --url.")


def _allowed(url: str) -> bool:
    u = urlparse(url)
    return u.scheme == "https" and bool(u.hostname) or u.scheme == "http" and u.hostname in ("127.0.0.1", "localhost")


def _download(url: str, target: Path, size: int, sha256: str) -> str | None:
    """Stream to a temp file beside target, check size then hash, rename. Returns the failed check or None."""
    cap = min(CAP, size)
    fd, tmp = tempfile.mkstemp(dir=target.parent, prefix=target.name + ".")
    try:
        got, h = 0, hashlib.sha256()
        with os.fdopen(fd, "wb") as f, urllib.request.urlopen(url, timeout=60) as r:
            while chunk := r.read(65536):
                got += len(chunk)
                if got > cap:
                    return f"size check failed: body exceeds {cap} bytes"
                h.update(chunk)
                f.write(chunk)
        if got != size:
            return f"size check failed: got {got} bytes, expected {size}"
        if h.hexdigest() != sha256:
            return f"hash check failed: got {h.hexdigest()}, expected {sha256}"
        os.replace(tmp, target)
        return None
    except http.client.IncompleteRead:
        return "size check failed: body truncated"
    except Exception as e:  # HTTPError, URLError, IncompleteRead, timeouts
        return f"download failed (HTTP/network error): {e}"
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def _target(raw_dir: str, name: str, src: dict) -> Path:
    """Where a source PDF lives: the same IBID_BNS_PDF / IBID_IPC_PDF override every other command honours."""
    return Path(os.environ.get(f"IBID_{name.upper()}_PDF") or Path(raw_dir) / src["file"])


def fetch(manifest: dict, raw_dir: str, name: str, url: str | None) -> int:
    src = manifest[name]
    if url is None and name == "ipc":
        print(IPC_NEEDS_URL.format(page=src["url"]), file=sys.stderr)
        return 1
    url = url or src["url"]
    target = _target(raw_dir, name, src)
    if target.exists():
        print(f"error: {target.resolve()} already exists; refusing to overwrite. Move it away to fetch again.", file=sys.stderr)
        return 1
    if not _allowed(url):
        print(f"error: url refused (only https, or http to 127.0.0.1/localhost): {url}", file=sys.stderr)
        return 1
    target.parent.mkdir(parents=True, exist_ok=True)
    failed = _download(url, target, src["bytes"], src["sha256"])
    if failed:
        print(f"error: {name}: {failed}", file=sys.stderr)
        return 1
    print(f"fetched {name}: {target.resolve()} (hash ok)")
    return 0


def _manifest(path: str) -> dict:
    """The sources file, checked to be a name-to-source object so a malformed one is an error line, not a traceback."""
    manifest = json.loads(Path(path).read_text())
    if not isinstance(manifest, dict) or not all(isinstance(s, dict) and _well_formed(s) for s in manifest.values()):
        raise ValueError(f"{path} must map each source name to an object with string url and sha256, and integer bytes and sections")
    return manifest


def _well_formed(src: dict) -> bool:
    ints = all(isinstance(src[k], int) and not isinstance(src[k], bool) for k in ("bytes", "sections") if k in src)
    return ints and all(isinstance(src.get(k), str) for k in ("url", "sha256"))


def run(sources: str, raw_dir: str, fetch_name: str | None = None, url: str | None = None) -> int:
    manifest = _manifest(sources)
    if fetch_name:
        if fetch(manifest, raw_dir, fetch_name, url):
            return 1
        run(sources, raw_dir)
        return 0
    ok = True
    paths = {}
    for tool in TOOLS:
        found = shutil.which(tool)
        print(f"{'pass' if found else 'FAIL'}  tool {tool}" + (f" ({found})" if found else " not on PATH"))
        if not found:
            ok = False
            print("\n".join(INSTALL))
    for name, src in manifest.items():
        path = _target(raw_dir, name, src).resolve()
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
    print(f"optional  learned model {MODEL}: present, sha256 {hashlib.sha256(MODEL.read_bytes()).hexdigest()}"
          if MODEL.is_file() else f"optional  learned model {MODEL}: absent (only needed for search mode learned). fit: {FIT}")
    if not ok:
        print("skip  parse not run: fix the failed checks above")
        return 1
    return _prove(manifest, paths)


def _prove(manifest: dict, paths: dict) -> int:
    """Parse each Act and compare its section count with the manifest; on success print the mcp line."""
    ok, counts = True, {}
    for name, src in manifest.items():
        if name not in PARSERS:  # slice 15 sources are checked for presence and hash only
            continue
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
