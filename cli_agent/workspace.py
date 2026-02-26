from __future__ import annotations

from pathlib import Path


class WorkspaceError(Exception):
    pass


class Workspace:
    def __init__(self, root: str | Path) -> None:
        self.root = Path(root).expanduser().resolve()
        if not self.root.exists():
            raise WorkspaceError(f"Workspace does not exist: {self.root}")
        if not self.root.is_dir():
            raise WorkspaceError(f"Workspace is not a directory: {self.root}")

    def resolve_safe(self, user_path: str | Path) -> Path:
        candidate = (self.root / Path(user_path)).resolve()
        if not self._is_within_root(candidate):
            raise WorkspaceError(f"Path escapes workspace: {user_path}")
        return candidate

    def _is_within_root(self, candidate: Path) -> bool:
        try:
            candidate.relative_to(self.root)
            return True
        except ValueError:
            return False
