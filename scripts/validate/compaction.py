#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts.validate.common import repo_root_from
from scripts.validate.feature_memory import approved_active_slices, compaction_due_slices


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=repo_root_from())
    parser.add_argument("--json", action="store_true", dest="json_output")
    parser.add_argument("--enforce", action="store_true", help="exit 1 when compaction is due")
    args = parser.parse_args()

    root = args.root.resolve()
    approved = approved_active_slices(root)
    due = compaction_due_slices(root)

    payload = {
        "approved_active_count": len(approved),
        "compaction_due": bool(due),
        "compact": [path.relative_to(root).as_posix() for path in due],
        "history_target": "feature-memory/history/",
    }

    if args.json_output:
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

    return 1 if args.enforce and due else 0


if __name__ == "__main__":
    raise SystemExit(main())

