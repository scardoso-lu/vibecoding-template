#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts.validate.checks.playwright_output import summarize_playwright_output


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("path", nargs="?", type=Path, help="Playwright output file. Reads stdin when omitted.")
    args = parser.parse_args()

    text = args.path.read_text(encoding="utf-8") if args.path else sys.stdin.read()
    summary = summarize_playwright_output(text)
    if summary:
        for line in summary:
            print(line)
        return 1
    print("playwright-output: no failures found")
    return 0


if __name__ == "__main__":
    sys.exit(main())

