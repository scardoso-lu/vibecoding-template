"""Repository layer: all filesystem, git, and config reads.

Everything that touches the disk, git, or the environment lives here so the
service layer stays pure (data in, Findings out) and easy to test.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Iterable


def repo_root_from(start: Path | None = None) -> Path:
    current = (start or Path.cwd()).resolve()
    for path in (current, *current.parents):
        if (path / ".git").exists() or (path / "AGENTS.md").exists():
            return path
    return current


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def iter_text_files(root: Path, paths: Iterable[str]) -> Iterable[Path]:
    for rel in paths:
        path = root / rel
        if path.is_file():
            yield path
        elif path.is_dir():
            yield from (
                item
                for item in path.rglob("*")
                if item.is_file()
                and item.suffix in {".md", ".toml", ".json", ".sh", ".py", ".txt"}
                and ".venv" not in item.parts
                and "node_modules" not in item.parts
            )


def load_json(path: Path) -> tuple[object | None, str | None]:
    """Parse a JSON file, returning (data, error_message)."""
    try:
        return json.loads(read_text(path)), None
    except json.JSONDecodeError as exc:
        return None, str(exc)


def git_changed_files(root: Path) -> list[str]:
    result = subprocess.run(
        ["git", "status", "--short"],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return []
    changed: list[str] = []
    for line in result.stdout.splitlines():
        if not line.strip():
            continue
        path = line[3:].strip()
        if " -> " in path:
            path = path.rsplit(" -> ", 1)[1]
        changed.append(path.replace("\\", "/"))
    return changed
