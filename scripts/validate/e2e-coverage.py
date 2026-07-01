#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts.validate.common import cli_main
from scripts.validate.playwright_stories import validate_e2e_coverage


if __name__ == "__main__":
    sys.exit(cli_main(validate_e2e_coverage, name="e2e-coverage"))

