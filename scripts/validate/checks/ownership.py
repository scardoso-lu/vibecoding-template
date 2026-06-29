from __future__ import annotations

import re
import subprocess
from pathlib import Path
from typing import Sequence

from scripts.validate.checks.common import Finding, read_text

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


def _do_not_touch_entries(slice_path: Path) -> list[str]:
    if not slice_path.exists():
        return []
    text = read_text(slice_path)
    match = re.search(r"^##+\s+Do Not Touch\s*$", text, re.MULTILINE)
    if not match:
        return []
    block = text[match.end() :]
    next_heading = re.search(r"^##+\s+", block, re.MULTILINE)
    if next_heading:
        block = block[: next_heading.start()]
    entries: list[str] = []
    for line in block.splitlines():
        stripped = line.strip().lstrip("-*").strip().strip("`")
        if stripped and not stripped.lower().startswith("none"):
            entries.append(stripped.replace("\\", "/"))
    return entries


def validate_ownership(
    root: Path,
    *,
    agent: str | None = None,
    changed_files: Sequence[str] | None = None,
    slice_path: Path | None = None,
) -> list[Finding]:
    findings: list[Finding] = []
    files = [path.replace("\\", "/") for path in (changed_files if changed_files is not None else git_changed_files(root))]
    for changed in files:
        if "__pycache__/" in changed or changed.endswith(".pyc"):
            findings.append(Finding(changed, "generated Python cache file must not be tracked or changed"))

    if agent == "backend-developer":
        for changed in files:
            if changed.startswith("frontend/"):
                findings.append(Finding(changed, "backend-developer must not change frontend files"))
    elif agent == "frontend-developer":
        for changed in files:
            if changed.startswith("backend/src/") or changed.startswith("backend/alembic/"):
                findings.append(Finding(changed, "frontend-developer must not change backend implementation files"))
    elif agent == "qa":
        allowed_prefixes = ("frontend/e2e/", "feature-memory/")
        for changed in files:
            if changed and not changed.startswith(allowed_prefixes):
                findings.append(Finding(changed, "QA may only change Playwright E2E files and terminal slice state"))

    if slice_path is not None:
        entries = _do_not_touch_entries(slice_path)
        for changed in files:
            for entry in entries:
                if not entry:
                    continue
                normalized = entry.rstrip("/")
                if changed == normalized or changed.startswith(f"{normalized}/"):
                    findings.append(Finding(changed, f"changed file is listed in Do Not Touch: {entry}"))
    return findings

