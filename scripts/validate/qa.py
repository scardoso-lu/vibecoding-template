#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts.validate.checks.common import cli_main
from scripts.validate.checks.playwright_stories import validate_qa_contract


if __name__ == "__main__":
    sys.exit(cli_main(validate_qa_contract, name="qa"))

