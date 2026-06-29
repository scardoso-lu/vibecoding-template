#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts.validate.checks.common import cli_main
from scripts.validate.checks.feature_memory import validate_feature_memory


if __name__ == "__main__":
    raise SystemExit(cli_main(validate_feature_memory, name="feature-memory"))

