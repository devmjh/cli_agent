from __future__ import annotations

import subprocess
from pathlib import Path


def _git(args: list[str], cwd: str | Path) -> dict:
    proc = subprocess.run(
        ["git", *args],
        cwd=str(cwd),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        shell=False,
    )
    return {
        "ok": proc.returncode == 0,
        "exit_code": proc.returncode,
        "stdout": proc.stdout,
        "stderr": proc.stderr,
    }


def git_status(cwd: str | Path) -> dict:
    return _git(["status", "--short"], cwd)


def git_diff(cwd: str | Path) -> dict:
    return _git(["diff"], cwd)
