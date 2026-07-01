#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path
from typing import Callable, Iterable

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts.validate.agent_guidance import validate_agent_guidance
from scripts.validate.app_contracts import (
    validate_backend_contract,
    validate_database_policy,
    validate_frontend_contract,
    validate_migrations,
    validate_project_layout,
)
from scripts.validate.common import Finding, cli_main
from scripts.validate.feature_memory import (
    validate_compaction,
    validate_feature_memory,
    validate_test_coverage_mapping,
)
from scripts.validate.harness_quality import validate_qa_evidence, validate_tooling
from scripts.validate.hook_registration import validate_hook_registration
from scripts.validate.ownership import validate_ownership
from scripts.validate.playwright_stories import (
    validate_e2e_coverage,
    validate_playwright_stories,
    validate_qa_contract,
)

VALIDATORS: dict[str, Callable[[Path], list[Finding]]] = {
    "agent-guidance": validate_agent_guidance,
    "feature-memory": validate_feature_memory,
    "compaction": validate_compaction,
    "playwright-stories": validate_playwright_stories,
    "test-coverage": validate_test_coverage_mapping,
    "e2e-coverage": validate_e2e_coverage,
    "hook-registration": validate_hook_registration,
    "project-layout": validate_project_layout,
    "database": validate_database_policy,
    "migrations": validate_migrations,
    "backend": validate_backend_contract,
    "frontend": validate_frontend_contract,
    "qa": validate_qa_contract,
    "qa-evidence": validate_qa_evidence,
    "tooling": validate_tooling,
    "ownership": validate_ownership,
}


def run_validators(
    root: Path, names: Iterable[str] | None = None
) -> dict[str, list[Finding]]:
    selected = list(names or VALIDATORS)
    return {name: VALIDATORS[name](root) for name in selected}


def workflow_cli() -> int:
    return cli_main(validators=VALIDATORS)


def script_entry(validator_name: str) -> int:
    return cli_main(VALIDATORS[validator_name], name=validator_name)


if __name__ == "__main__":
    raise SystemExit(workflow_cli())
