from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts.validate.checks.workflow import run_validators


def test_aggregator_returns_named_validator_results(tmp_path: Path) -> None:
    results = run_validators(tmp_path, names=["agent-guidance", "feature-memory"])

    assert set(results) == {"agent-guidance", "feature-memory"}
    assert isinstance(results["agent-guidance"], list)
    assert isinstance(results["feature-memory"], list)



