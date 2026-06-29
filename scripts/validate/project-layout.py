#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts.validate.checks.app_contracts import validate_project_layout
from scripts.validate.checks.common import cli_main


if __name__ == "__main__":
    sys.exit(cli_main(validate_project_layout, name="project-layout"))

