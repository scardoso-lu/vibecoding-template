from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts.validate.checks.app_contracts import validate_backend_contract, validate_frontend_contract
from scripts.validate.checks.feature_memory import validate_test_coverage_mapping
from scripts.validate.checks.ownership import validate_ownership
from scripts.validate.checks.playwright_output import summarize_playwright_output
from scripts.validate.checks.playwright_stories import validate_qa_contract


def write(path: Path, text: str = "") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_backend_contract_requires_route_tests_and_env_keys(tmp_path: Path) -> None:
    write(tmp_path / "backend/src/domain/entities/part.py")
    write(tmp_path / "backend/src/application/use_cases/parts/create_part.py", "class CreatePart:\n    pass\n")
    write(tmp_path / "backend/src/infrastructure/__init__.py")
    write(tmp_path / "backend/src/presentation/routes/parts.py")
    write(tmp_path / "backend/src/config/settings.py", "DATABASE_URL: str\nAPI_PORT: int\n")
    write(tmp_path / "backend/.env.example", "DATABASE_URL=sqlite://\n")
    (tmp_path / "backend/alembic/versions").mkdir(parents=True)

    findings = validate_backend_contract(tmp_path)
    messages = "\n".join(finding.format() for finding in findings)

    assert "missing API route test" in messages
    assert "missing setting key API_PORT" in messages
    assert "mutating use case must use AuditWriter" in messages
    assert "no Alembic migration files" in messages


def test_frontend_contract_rejects_brittle_e2e_and_missing_action_tests(tmp_path: Path) -> None:
    write(tmp_path / "frontend/src/app/[lang]/(app)/parts/page.tsx")
    write(tmp_path / "frontend/app/page.tsx")
    write(tmp_path / "frontend/pages/_app.tsx")
    write(tmp_path / "frontend/src/components/parts/part-form.tsx")
    write(tmp_path / "frontend/src/services/parts.ts")
    write(tmp_path / "frontend/src/actions/parts.ts")
    write(tmp_path / "frontend/e2e/parts.spec.ts", "await page.waitForTimeout(1000)\nawait page.locator('.btn').click()\n")

    findings = validate_frontend_contract(tmp_path)
    messages = "\n".join(finding.format() for finding in findings)

    assert "do not use sleeps" in messages
    assert "prefer role/label/text locators" in messages
    assert "duplicate Next App Router roots" in messages
    assert "do not mix legacy frontend/pages router" in messages
    assert "missing Server Action test" in messages
    assert "missing form validation test" in messages
    assert "user-facing route should define loading" in messages


def test_qa_contract_reuses_playwright_story_validation(tmp_path: Path) -> None:
    slice_dir = tmp_path / "feature-memory/inventory"
    write(
        slice_dir / "slice.md",
        """## Status
State: IN PROGRESS
## E2E Test Stories
| Story ID | User Story | Test Location | Seed/Setup | Assertions | Slugs |
|---|---|---|---|---|---|
| S1 | As a user, I want to list parts, so I can review inventory. | frontend/e2e/parts.spec.ts::lists parts | seed | row visible | frontend/10 |
""",
    )
    write(tmp_path / "frontend/e2e/parts.spec.ts", "test('lists parts', async () => {})\n")

    findings = validate_qa_contract(tmp_path)

    assert any("missing // Story: comment" in finding.message for finding in findings)


def test_test_coverage_mapping_requires_criteria_ids_and_full_mapping(tmp_path: Path) -> None:
    slice_dir = tmp_path / "feature-memory/inventory"
    write(
        slice_dir / "slice.md",
        """## Status
State: IN PROGRESS
## Acceptance Criteria
- [ ] AC-001: User can list parts.
- [ ] AC-002: User can create parts.
## E2E Test Stories
| Story ID | User Story | Criteria | Test Location | Seed/Setup | Assertions | Slugs |
|---|---|---|---|---|---|---|
| S1 | As a user, I want to list parts, so I can review inventory. | AC-001 | frontend/e2e/parts.spec.ts::lists parts | seed | row visible | frontend/10 |
## Test Coverage
| Criteria | Test Type | Test Location |
|---|---|---|
| AC-999 | backend | backend/test/test_parts.py |
""",
    )
    write(tmp_path / "frontend/e2e/parts.spec.ts", "// Story: AC-001\ntest('lists parts', async () => {})\n")
    write(tmp_path / "backend/test/test_parts.py", "def test_parts(): pass\n")

    findings = validate_test_coverage_mapping(tmp_path)
    messages = "\n".join(finding.format() for finding in findings)

    assert "unknown acceptance criterion AC-999" in messages
    assert "acceptance criterion AC-002 is not mapped" in messages


def test_ownership_checks_agent_scope_pycache_and_do_not_touch(tmp_path: Path) -> None:
    slice_md = tmp_path / "feature-memory/inventory/slice.md"
    write(
        slice_md,
        """## Do Not Touch
- frontend/src/locked
## Acceptance Criteria
- done
""",
    )

    findings = validate_ownership(
        tmp_path,
        agent="qa",
        changed_files=["frontend/src/locked/page.tsx", "scripts/lib/__pycache__/x.pyc"],
        slice_path=slice_md,
    )
    messages = "\n".join(finding.format() for finding in findings)

    assert "QA may only change" in messages
    assert "generated Python cache file" in messages
    assert "changed file is listed in Do Not Touch" in messages


def test_playwright_output_summary_extracts_failures() -> None:
    output = """
  1) parts.spec.ts:12:7 - lists parts
    TimeoutError: locator.click: Timeout 30000ms exceeded.
      at frontend/e2e/parts.spec.ts:12:7
  1 failed
"""

    summary = summarize_playwright_output(output)

    assert "1) parts.spec.ts:12:7 - lists parts" in summary
    assert "TimeoutError: locator.click: Timeout 30000ms exceeded." in summary
    assert "at frontend/e2e/parts.spec.ts:12:7" in summary
    assert "1 failed" in summary



