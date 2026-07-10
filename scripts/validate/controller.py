"""Controller layer: the check registry and run orchestration.

Maps check names to service functions and runs the selected checks, returning
Findings for the view to render. Special runners (gate, runtime-smoke,
playwright-output) are dispatched by the CLI directly since they do
not follow the `validate_*(root) -> list[Finding]` shape.
"""

from __future__ import annotations

from pathlib import Path
from typing import Callable, Iterable

from scripts.validate.models import Finding
from scripts.validate.services import (
    agent_evidence,
    agent_guidance,
    app_contracts,
    feature_memory,
    harness,
    harness_quality,
    hook_registration,
    ownership,
    playwright_stories,
    verification,
)

# check name -> validator(root) -> list[Finding]
VALIDATORS: dict[str, Callable[[Path], list[Finding]]] = {
    "agent-guidance": agent_guidance.validate_agent_guidance,
    "agent-evidence": agent_evidence.validate_agent_evidence,
    "memory": feature_memory.validate_feature_memory,
    "playwright-stories": playwright_stories.validate_playwright_stories,
    "test-coverage": feature_memory.validate_test_coverage_mapping,
    "e2e-coverage": playwright_stories.validate_e2e_coverage,
    "hook-registration": hook_registration.validate_hook_registration,
    "harness": harness.validate_harness,
    "project-layout": app_contracts.validate_project_layout,
    "database": app_contracts.validate_database_policy,
    "migrations": app_contracts.validate_migrations,
    "backend": app_contracts.validate_backend_contract,
    "frontend": app_contracts.validate_frontend_contract,
    "qa": playwright_stories.validate_qa_contract,
    "qa-evidence": harness_quality.validate_qa_evidence,
    "verification": verification.validate_verification,
    "tooling": harness_quality.validate_tooling,
    "ownership": ownership.validate_ownership,
}


def run_validators(
    root: Path, names: Iterable[str] | None = None
) -> dict[str, list[Finding]]:
    selected = list(names or VALIDATORS)
    return {name: VALIDATORS[name](root) for name in selected}


def run_doctor(root: Path, *, smoke: bool = True) -> dict[str, list[Finding]]:
    """Every workflow validator plus hook syntax/registration integrity."""
    results = run_validators(root)
    results["hook-registration"] = hook_registration.validate_hook_registration(
        root, smoke=smoke
    )
    results["hook-syntax"] = hook_registration.validate_hook_syntax(root)
    return results
