#!/usr/bin/env python3
"""Single CLI entrypoint (view layer) for every deterministic check.

    python scripts/validate/cli.py <check> [--root .] [--json]
    python scripts/validate/cli.py all               # every workflow validator
    python scripts/validate/cli.py doctor            # all + hook syntax/registration
    python scripts/validate/cli.py gate --slice feature-memory/<feature>/slice.md
    python scripts/validate/cli.py compaction [--enforce] [--json]
    python scripts/validate/cli.py ownership [--agent A] [--slice S] [--changed-file F ...]
    python scripts/validate/cli.py runtime-smoke [--config C] [--url U] [--must-contain T ...] [--forbid T ...]
    python scripts/validate/cli.py playwright-output [--file F]

`cli.py <check>` is the only interface; hooks, templates, and docs call it.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts.validate import view
from scripts.validate.controller import VALIDATORS, run_doctor, run_validators
from scripts.validate.models import repo_root_from
from scripts.validate.services import (
    feature_memory,
    gate,
    ownership,
    playwright_output,
    runtime_smoke,
)

SPECIAL = {"gate", "compaction", "ownership", "runtime-smoke", "playwright-output"}


def _emit(results: dict, as_json: bool) -> int:
    text, has_findings = view.render(results, as_json=as_json)
    print(text)
    return 1 if has_findings else 0


def _resolve(root: Path, rel: Path | None) -> Path | None:
    if rel is None:
        return None
    return rel if rel.is_absolute() else (root / rel)


def build_parser() -> argparse.ArgumentParser:
    # Shared options accepted both before and after the subcommand, so the hook
    # form `cli.py <check> --root .` works as well as `cli.py --root . <check>`.
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--root", type=Path, default=None)
    common.add_argument("--json", action="store_true", dest="json_output")

    parser = argparse.ArgumentParser(prog="validate", parents=[common])
    sub = parser.add_subparsers(dest="check", required=True)

    def add(name: str) -> argparse.ArgumentParser:
        return sub.add_parser(name, parents=[common])

    for name in [*[n for n in VALIDATORS if n not in SPECIAL], "all", "doctor"]:
        add(name)

    gate_p = add("gate")
    gate_p.add_argument("--slice", type=Path, required=True, dest="slice_path")
    gate_p.add_argument("--coverage-threshold", type=float, default=80.0)

    comp_p = add("compaction")
    comp_p.add_argument("--enforce", action="store_true")

    own_p = add("ownership")
    own_p.add_argument(
        "--agent", choices=["backend-developer", "frontend-developer", "qa"]
    )
    own_p.add_argument("--slice", type=Path, dest="slice_path")
    own_p.add_argument("--changed-file", action="append", dest="changed_files")

    smoke_p = add("runtime-smoke")
    smoke_p.add_argument("--config", type=Path)
    smoke_p.add_argument("--url")
    smoke_p.add_argument("--must-contain", action="append", default=[])
    smoke_p.add_argument("--forbid", action="append", default=[])

    po_p = add("playwright-output")
    po_p.add_argument("--file", type=Path)

    return parser


def _compaction(root: Path, *, enforce: bool, as_json: bool) -> int:
    approved = feature_memory.approved_active_slices(root)
    due = feature_memory.compaction_due_slices(root)
    payload = {
        "approved_active_count": len(approved),
        "compaction_due": bool(due),
        "compact": [path.relative_to(root).as_posix() for path in due],
        "history_target": "feature-memory/history/",
    }
    if as_json:
        print(json.dumps(payload, indent=2))
    elif due:
        print(
            "compaction: due - move the three oldest QA-approved slices to "
            "feature-memory/history/:"
        )
        for rel in payload["compact"]:
            print(f"  - {rel}")
    else:
        print(f"compaction: ok ({len(approved)} active QA-approved slice(s))")
    return 1 if enforce and due else 0


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    root = (args.root or repo_root_from()).resolve()
    check = args.check

    if check == "gate":
        return gate.run_gate(root, args.slice_path, args.coverage_threshold)
    if check == "runtime-smoke":
        return runtime_smoke.run_smoke(
            _resolve(root, args.config), args.url, args.must_contain, args.forbid
        )
    if check == "playwright-output":
        text = (
            _resolve(root, args.file).read_text(encoding="utf-8")
            if args.file
            else sys.stdin.read()
        )
        for line in playwright_output.summarize_playwright_output(text):
            print(line)
        return 0
    if check == "compaction":
        return _compaction(root, enforce=args.enforce, as_json=args.json_output)
    if check == "ownership":
        findings = ownership.validate_ownership(
            root,
            agent=args.agent,
            changed_files=args.changed_files,
            slice_path=_resolve(root, args.slice_path),
        )
        return _emit({"ownership": findings}, args.json_output)
    if check == "all":
        return _emit(run_validators(root), args.json_output)
    if check == "doctor":
        return _emit(run_doctor(root), args.json_output)

    return _emit(run_validators(root, [check]), args.json_output)


if __name__ == "__main__":
    raise SystemExit(main())
