from __future__ import annotations

import argparse
import json
import re
import sys
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable

@dataclass
class Finding:
    path: str
    message: str
    line: int | None = None

    def format(self) -> str:
        suffix = f":{self.line}" if self.line is not None else ""
        return f"{self.path}{suffix}: {self.message}"


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


def line_number(text: str, index: int) -> int:
    return text.count("\n", 0, index) + 1


def parse_md_table(text: str, heading: str) -> list[dict[str, str]]:
    heading_pattern = re.compile(rf"^##+\s+{re.escape(heading)}\s*$", re.MULTILINE)
    match = heading_pattern.search(text)
    if not match:
        return []
    lines = text[match.end() :].splitlines()
    table_lines: list[str] = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("## ") or stripped.startswith("### "):
            break
        if stripped.startswith("|") and stripped.endswith("|"):
            table_lines.append(stripped)
        elif table_lines and stripped:
            break
    if len(table_lines) < 2:
        return []
    headers = [cell.strip() for cell in table_lines[0].strip("|").split("|")]
    rows: list[dict[str, str]] = []
    for raw in table_lines[2:]:
        cells = [cell.strip().strip("`") for cell in raw.strip("|").split("|")]
        if len(cells) == len(headers):
            rows.append(dict(zip(headers, cells, strict=True)))
    return rows


def has_heading(text: str, heading: str) -> bool:
    return re.search(rf"^##+\s+{re.escape(heading)}\s*$", text, re.MULTILINE) is not None


def section_text(text: str, heading: str) -> str:
    match = re.search(rf"^##+\s+{re.escape(heading)}\s*$", text, re.MULTILINE)
    if not match:
        return ""
    block = text[match.end() :]
    next_heading = re.search(r"^##+\s+", block, re.MULTILINE)
    return block[: next_heading.start()] if next_heading else block


def split_ids(value: str) -> set[str]:
    return set(re.findall(r"\bAC-\d{3}\b", value))


def acceptance_criteria_ids(text: str) -> tuple[set[str], list[str]]:
    block = section_text(text, "Acceptance Criteria")
    ids: set[str] = set()
    invalid: list[str] = []
    for raw in block.splitlines():
        line = raw.strip()
        if not line.startswith(("-", "*", "|")):
            continue
        if line.startswith("|"):
            continue
        found = split_ids(line)
        if found:
            ids.update(found)
        elif line.startswith(("- [ ]", "- [x]", "- [X]", "* [ ]", "* [x]", "* [X]", "- ", "* ")):
            invalid.append(line)
    for row in parse_md_table(text, "Acceptance Criteria"):
        value = row.get("ID") or row.get("Criterion ID") or row.get("Criteria") or ""
        found = split_ids(value)
        if found:
            ids.update(found)
        elif row:
            invalid.append(str(row))
    return ids, invalid


def hook_commands(config: object) -> list[str]:
    commands: list[str] = []
    if not isinstance(config, dict):
        return commands
    hooks = config.get("hooks", {})
    if not isinstance(hooks, dict):
        return commands
    for entries in hooks.values():
        if not isinstance(entries, list):
            continue
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            for hook in entry.get("hooks", []):
                if isinstance(hook, dict) and isinstance(hook.get("command"), str):
                    commands.append(hook["command"])
    return commands


def hook_matchers(config: object) -> list[str]:
    matchers: list[str] = []
    if not isinstance(config, dict):
        return matchers
    hooks = config.get("hooks", {})
    if not isinstance(hooks, dict):
        return matchers
    for entries in hooks.values():
        if not isinstance(entries, list):
            continue
        for entry in entries:
            if isinstance(entry, dict) and isinstance(entry.get("matcher"), str):
                matchers.append(entry["matcher"])
    return matchers


def cli_main(
    validator: Callable[[Path], list[Finding]] | None = None,
    *,
    name: str | None = None,
    validators: dict[str, Callable[[Path], list[Finding]]] | None = None,
) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=repo_root_from())
    parser.add_argument("--json", action="store_true", dest="json_output")
    args = parser.parse_args()
    root = args.root.resolve()
    if validator is None:
        if validators is None:
            raise ValueError("validators are required when validator is None")
        results = {validator_name: fn(root) for validator_name, fn in validators.items()}
    else:
        results = {name or "validator": validator(root)}
    if args.json_output:
        print(json.dumps({k: [finding.__dict__ for finding in v] for k, v in results.items()}, indent=2))
    else:
        for validator_name, findings in results.items():
            if findings:
                print(f"{validator_name}: {len(findings)} finding(s)")
                for finding in findings:
                    print(f"  {finding.format()}")
            else:
                print(f"{validator_name}: ok")
    return 1 if any(results.values()) else 0

