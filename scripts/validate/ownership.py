#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Sequence

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts.validate.common import Finding, read_text, repo_root_from


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
    files = [
        path.replace("\\", "/")
        for path in (
            changed_files if changed_files is not None else git_changed_files(root)
        )
    ]
    for changed in files:
        if "__pycache__/" in changed or changed.endswith(".pyc"):
            findings.append(
                Finding(
                    changed,
                    "generated Python cache file must not be tracked or changed",
                )
            )

    if agent == "backend-developer":
        for changed in files:
            if changed.startswith("frontend/"):
                findings.append(
                    Finding(changed, "backend-developer must not change frontend files")
                )
    elif agent == "frontend-developer":
        for changed in files:
            if changed.startswith("backend/src/") or changed.startswith(
                "backend/alembic/"
            ):
                findings.append(
                    Finding(
                        changed,
                        "frontend-developer must not change backend implementation files",
                    )
                )
    elif agent == "qa":
        allowed_prefixes = ("frontend/e2e/", "feature-memory/")
        for changed in files:
            if changed and not changed.startswith(allowed_prefixes):
                findings.append(
                    Finding(
                        changed,
                        "QA may only change Playwright E2E files and terminal slice state",
                    )
                )

    if slice_path is not None:
        entries = _do_not_touch_entries(slice_path)
        for changed in files:
            for entry in entries:
                if not entry:
                    continue
                normalized = entry.rstrip("/")
                if changed == normalized or changed.startswith(f"{normalized}/"):
                    findings.append(
                        Finding(
                            changed, f"changed file is listed in Do Not Touch: {entry}"
                        )
                    )
    return findings


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=repo_root_from())
    parser.add_argument(
        "--agent", choices=["backend-developer", "frontend-developer", "qa"]
    )
    parser.add_argument("--slice", type=Path)
    parser.add_argument("--changed-file", action="append", dest="changed_files")
    parser.add_argument("--json", action="store_true", dest="json_output")
    args = parser.parse_args()

    root = args.root.resolve()
    slice_path = args.slice
    if slice_path is not None and not slice_path.is_absolute():
        slice_path = root / slice_path

    findings = validate_ownership(
        root,
        agent=args.agent,
        changed_files=args.changed_files,
        slice_path=slice_path,
    )
    if args.json_output:
        print(
            json.dumps(
                {"ownership": [finding.__dict__ for finding in findings]}, indent=2
            )
        )
    else:
        if findings:
            print(f"ownership: {len(findings)} finding(s)")
            for finding in findings:
                print(f"  {finding.format()}")
        else:
            print("ownership: ok")
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
