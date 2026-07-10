"""Repository layer: all filesystem, git, and config reads.

Everything that touches the disk, git, or the environment lives here so the
service layer stays pure (data in, Findings out) and easy to test.
"""

from __future__ import annotations

import hashlib
import json
import re
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


# App surfaces whose working-tree state qa-evidence.json is bound to. memory/ and
# agent-evidence/ are deliberately excluded so persisting a verdict or evidence file
# does not invalidate the evidence that produced it.
_APP_STATE_PREFIXES = ("backend/", "frontend/")
_APP_STATE_ROOT_RE = re.compile(r"^docker-compose[^/]*\.ya?ml$")


def _is_app_state_path(path: str) -> bool:
    return path.startswith(_APP_STATE_PREFIXES) or bool(_APP_STATE_ROOT_RE.match(path))


def app_code_state(root: Path) -> dict[str, str] | None:
    """Digest of the app-code working-tree state, for evidence freshness binding.

    Returns {"head": <commit sha or "">, "app_digest": <sha256>} where the digest
    covers every dirty-tracked or untracked-non-ignored file under backend/,
    frontend/, or a root docker-compose file - combined with HEAD, this pins the
    exact code state the QA gate ran against. Returns None when git is unavailable
    or the root is not a work tree (callers then skip freshness checks entirely).
    """
    try:
        head = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=root,
            capture_output=True,
            text=True,
            check=False,
        )
        status = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=root,
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError:
        return None
    if status.returncode != 0:
        return None

    entries: list[str] = []
    for line in status.stdout.splitlines():
        if len(line) < 4:
            continue
        path = line[3:].strip()
        if " -> " in path:
            path = path.rsplit(" -> ", 1)[1]
        path = path.strip('"').replace("\\", "/")
        if not _is_app_state_path(path):
            continue
        file_path = root / path
        try:
            if file_path.is_file():
                content_hash = hashlib.sha256(file_path.read_bytes()).hexdigest()
            elif file_path.is_dir():
                # Untracked directories are listed as one entry; hash their files.
                content_hash = hashlib.sha256(
                    b"".join(
                        item.relative_to(root).as_posix().encode() + item.read_bytes()
                        for item in sorted(file_path.rglob("*"))
                        if item.is_file()
                    )
                ).hexdigest()
            else:
                content_hash = "DELETED"
        except OSError:
            content_hash = "UNREADABLE"
        entries.append(f"{path}\n{content_hash}")

    digest = hashlib.sha256("\n".join(sorted(entries)).encode("utf-8")).hexdigest()
    return {
        "head": head.stdout.strip() if head.returncode == 0 else "",
        "app_digest": digest,
    }


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
