from __future__ import annotations

import shlex
import subprocess
from pathlib import Path


def run_shell(cmd: str, cwd: str | Path, timeout_s: int = 120) -> dict:
    args = shlex.split(cmd)
    proc = subprocess.run(
        args,
        cwd=str(cwd),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        shell=False,
        timeout=timeout_s,
    )
    return {
        "ok": proc.returncode == 0,
        "exit_code": proc.returncode,
        "stdout": proc.stdout,
        "stderr": proc.stderr,
    }
