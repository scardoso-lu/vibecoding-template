#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts.validate.checks.common import repo_root_from
from scripts.validate.checks.hook_registration import validate_hook_registration


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=repo_root_from())
    parser.add_argument("--json", action="store_true", dest="json_output")
    parser.add_argument("--no-smoke", action="store_true", help="validate registration only")
    args = parser.parse_args()

    root = args.root.resolve()
    findings = validate_hook_registration(root, smoke=not args.no_smoke)

    if args.json_output:
        print(json.dumps({"hook-registration": [finding.__dict__ for finding in findings]}, indent=2))
    elif findings:
        print(f"hook-registration: {len(findings)} finding(s)")
        for finding in findings:
            print(f"  {finding.format()}")
    else:
        print("hook-registration: ok")

    return 1 if findings else 0


if __name__ == "__main__":
    raise SystemExit(main())

