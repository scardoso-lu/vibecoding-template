#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts.validate.checks.common import repo_root_from
from scripts.validate.checks.ownership import validate_ownership


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=repo_root_from())
    parser.add_argument("--agent", choices=["backend-developer", "frontend-developer", "qa"])
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
        print(json.dumps({"ownership": [finding.__dict__ for finding in findings]}, indent=2))
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

