"""Where the gitignored source PDFs are: the env vars, else the main checkout's data/raw (a git worktree has none)."""
import os
import unittest
import subprocess
from pathlib import Path


def _main_checkout() -> Path:
    here = Path(__file__).parent
    common = subprocess.run(["git", "rev-parse", "--path-format=absolute", "--git-common-dir"], cwd=here,
                            capture_output=True, text=True, check=True).stdout.strip()
    return Path(common).parent


BNS_PDF = os.environ.get("IBID_BNS_PDF") or str(_main_checkout() / "data/raw/bns-prs.pdf")
IPC_PDF = os.environ.get("IBID_IPC_PDF") or str(_main_checkout() / "data/raw/ipc-wipo.pdf")
CRPC_PDF = os.environ.get("IBID_CRPC_PDF") or str(_main_checkout() / "data/raw/crpc-indiacode.pdf")
BNSS_PDF = os.environ.get("IBID_BNSS_PDF") or str(_main_checkout() / "data/raw/bnss-prs.pdf")
TABLE_PDF = os.environ.get("IBID_BNSS_CRPC_TABLE_PDF") or str(_main_checkout() / "data/raw/capt/comparison_summary_BNSS_to_CrPC.pdf")

needs_ipc = unittest.skipUnless(os.path.exists(IPC_PDF), "IPC PDF absent: its WIPO link expires, so CI cannot fetch it")
