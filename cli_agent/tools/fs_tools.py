from __future__ import annotations

from pathlib import Path

from ..workspace import Workspace


def list_dir(workspace: Workspace, path: str = ".") -> dict:
    target = workspace.resolve_safe(path)
    items = []
    for child in sorted(target.iterdir(), key=lambda p: p.name.lower()):
        items.append({"name": child.name, "is_dir": child.is_dir()})
    return {"path": str(target), "items": items}


def read_file(workspace: Workspace, path: str) -> dict:
    target = workspace.resolve_safe(path)
    if not target.exists() or not target.is_file():
        return {"ok": False, "error": f"File not found: {path}"}
    return {"ok": True, "path": str(target), "content": target.read_text(encoding="utf-8")}


def write_file(workspace: Workspace, path: str, content: str) -> dict:
    target = workspace.resolve_safe(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    return {"ok": True, "path": str(target), "bytes": len(content.encode("utf-8"))}


def apply_patch(workspace: Workspace, unified_diff: str) -> dict:
    lines = unified_diff.splitlines()
    if not lines:
        return {"ok": False, "error": "Empty diff"}

    file_line = next((line for line in lines if line.startswith("+++ ")), None)
    if file_line is None:
        return {"ok": False, "error": "Missing '+++' file header in diff"}

    raw_path = file_line[4:].strip()
    if raw_path.startswith("b/"):
        raw_path = raw_path[2:]
    target = workspace.resolve_safe(raw_path)

    if not target.exists():
        return {"ok": False, "error": f"Target file does not exist: {raw_path}"}

    original = target.read_text(encoding="utf-8").splitlines()
    result: list[str] = []
    src_idx = 0
    i = 0

    while i < len(lines):
        line = lines[i]
        if not line.startswith("@@ "):
            i += 1
            continue

        header = line
        parts = header.split(" ")
        old_range = parts[1]
        old_start = int(old_range.split(",")[0][1:])
        old_start_idx = old_start - 1

        while src_idx < old_start_idx and src_idx < len(original):
            result.append(original[src_idx])
            src_idx += 1

        i += 1
        while i < len(lines):
            hunk_line = lines[i]
            if hunk_line.startswith("@@ "):
                break
            if hunk_line.startswith("+"):
                result.append(hunk_line[1:])
            elif hunk_line.startswith("-"):
                src_idx += 1
            elif hunk_line.startswith(" "):
                if src_idx >= len(original) or original[src_idx] != hunk_line[1:]:
                    return {"ok": False, "error": "Patch context mismatch"}
                result.append(original[src_idx])
                src_idx += 1
            i += 1

    while src_idx < len(original):
        result.append(original[src_idx])
        src_idx += 1

    target.write_text("\n".join(result) + "\n", encoding="utf-8")
    return {"ok": True, "path": str(target)}
