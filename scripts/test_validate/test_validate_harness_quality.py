from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts.validate.checks.app_contracts import validate_database_policy, validate_migrations, validate_project_layout
from scripts.validate.checks.harness_quality import validate_qa_evidence, validate_tooling
from scripts.validate.checks.playwright_stories import validate_e2e_coverage


def write(path: Path, text: str = "") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_project_layout_catches_missing_stack_artifacts_and_root_pnpm(tmp_path: Path) -> None:
    write(tmp_path / "backend/pyproject.toml")
    write(tmp_path / "backend/.env.example")
    write(tmp_path / "frontend/package.json", "{}")
    write(tmp_path / "frontend/Dockerfile", "COPY package.json ./\nRUN pnpm install\n")
    write(tmp_path / "frontend/.env.example", "SERVICE_URL=http://localhost:8000\n")
    write(tmp_path / "frontend/app/page.tsx")
    write(tmp_path / "frontend/pages/_app.tsx")
    write(tmp_path / "frontend/src/app/page.tsx")
    write(tmp_path / "pnpm-lock.yaml")
    write(tmp_path / "pnpm-workspace.yaml")
    write(
        tmp_path / "docker-compose.yml",
        "services:\n  backend:\n    image: test\n  frontend:\n    image: test\n",
    )

    findings = validate_project_layout(tmp_path)
    messages = "\n".join(finding.format() for finding in findings)

    assert "backend/Dockerfile" in messages
    assert "backend/uv.lock" in messages
    assert "frontend/pnpm-lock.yaml" in messages
    assert "stack artifact must live under frontend/" in messages
    assert "backend service must use stack-local env file" in messages
    assert "duplicate Next App Router roots" in messages
    assert "do not mix legacy frontend/pages router" in messages
    assert "compose frontend env must not point service URLs at localhost" in messages


def test_database_policy_rejects_runtime_sqlite_default(tmp_path: Path) -> None:
    write(tmp_path / "backend/src/config/settings.py", 'DATABASE_URL = "sqlite:///./warehouse.db"\n')
    write(tmp_path / "backend/.env.example", "DATABASE_URL=sqlite:///./warehouse.db\n")
    write(tmp_path / "docker-compose.yml", "services:\n  backend:\n    image: test\n")

    findings = validate_database_policy(tmp_path)
    messages = "\n".join(finding.format() for finding in findings)

    assert "runtime database config must not default to SQLite" in messages
    assert "default documented DATABASE_URL must not use SQLite" in messages
    assert "compose must define the guideline database service" in messages


def test_migration_validator_rejects_empty_initial_revision(tmp_path: Path) -> None:
    write(
        tmp_path / "backend/alembic/versions/0001_initial_schema.py",
        "def upgrade() -> None:\n    pass\n\n\ndef downgrade() -> None:\n    pass\n",
    )

    findings = validate_migrations(tmp_path)
    messages = "\n".join(finding.format() for finding in findings)

    assert "migration upgrade() must not be empty" in messages
    assert "migration downgrade() must not be empty" in messages
    assert "initial migration must create schema tables" in messages


def test_qa_evidence_requires_command_provenance(tmp_path: Path) -> None:
    write(
        tmp_path / "feature-memory/inventory/slice.md",
        """## Status
- State: active
## Request
Build app.
## Slice Boundary
Fullstack.
## Do Not Touch
- none
## Implementation Plan
- build
## Acceptance Criteria
| ID | Criterion |
|---|---|
| AC-001 | works |
## Test Coverage
| Criteria | Test Type | Test Location |
|---|---|---|
| AC-001 | backend | backend/test/test_app.py |
## QA Handoff
- review
## Provenance
- source
""",
    )
    write(tmp_path / "backend/pyproject.toml")
    write(tmp_path / "frontend/package.json", "{}")

    findings = validate_qa_evidence(tmp_path)

    assert any("full slice must record deterministic QA evidence" in finding.message for finding in findings)


def test_qa_evidence_rejects_markdown_evidence(tmp_path: Path) -> None:
    slice_dir = tmp_path / "feature-memory/inventory"
    write(
        slice_dir / "slice.md",
        """## Status
- State: active
## Request
Build app.
## Slice Boundary
Fullstack.
## Do Not Touch
- none
## Implementation Plan
- build
## Acceptance Criteria
| ID | Criterion |
|---|---|
| AC-001 | works |
## Test Coverage
| Criteria | Test Type | Test Location |
|---|---|---|
| AC-001 | backend | backend/test/test_app.py |
## QA Handoff
- review
## Provenance
- source
""",
    )
    write(slice_dir / "qa-evidence.md", "| Command | Result |\n|---|---|\n| pytest | passed |\n")

    findings = validate_qa_evidence(tmp_path)

    assert any("QA evidence JSON" in finding.message for finding in findings)


def test_qa_evidence_json_requires_passed_runs_and_expected_commands(tmp_path: Path) -> None:
    slice_dir = tmp_path / "feature-memory/inventory"
    write(
        slice_dir / "slice.md",
        """## Status
- State: active
## Request
Build app.
## Slice Boundary
Fullstack.
## Do Not Touch
- none
## Implementation Plan
- build
## Acceptance Criteria
| ID | Criterion |
|---|---|
| AC-001 | works |
## Test Coverage
| Criteria | Test Type | Test Location |
|---|---|---|
| AC-001 | backend | backend/test/test_app.py |
## QA Handoff
- review
## Provenance
- source
""",
    )
    write(tmp_path / "backend/pyproject.toml")
    write(tmp_path / "frontend/package.json", "{}")
    write(tmp_path / "docker-compose.yml", "services:\n  backend:\n    image: test\n")
    write(
        slice_dir / "qa-evidence.json",
        json.dumps(
            {
                "generated_by": {
                    "command": "python scripts\\validate\\gate.py --root . --slice feature-memory\\inventory\\slice.md",
                    "cwd": ".",
                },
                "runs": [
                    {
                        "command": "uv run pytest --cov=src --cov-report=json:coverage.json --cov-fail-under=80",
                        "cwd": "backend",
                        "exit_code": 1,
                        "started_at": "2026-06-29T00:00:00Z",
                        "finished_at": "2026-06-29T00:00:01Z",
                        "output_path": "feature-memory/inventory/evidence/backend.txt",
                    }
                ]
            }
        ),
    )

    findings = validate_qa_evidence(tmp_path)
    messages = "\n".join(finding.format() for finding in findings)

    assert "did not pass" in messages
    assert "validate-tools project-layout ." in messages
    assert "docker compose up" in messages
    assert "runtime-smoke.json" in messages
    assert "runtime-smoke.py" in messages
    assert "frontend test command" in messages
    assert "unit_coverage" in messages


def test_qa_evidence_requires_coverage_above_threshold_and_e2e_pointer(tmp_path: Path) -> None:
    slice_dir = tmp_path / "feature-memory/inventory"
    write(
        slice_dir / "slice.md",
        """## Status
- State: active
## Request
Build app.
## Slice Boundary
Fullstack.
## Do Not Touch
- none
## Implementation Plan
- build
## Acceptance Criteria
| ID | Criterion |
|---|---|
| AC-001 | works |
## Test Coverage
| Criteria | Test Type | Test Location |
|---|---|---|
| AC-001 | backend | backend/test/test_app.py |
## QA Handoff
- review
## Provenance
- source
""",
    )
    write(tmp_path / "backend/pyproject.toml")
    write(tmp_path / "frontend/package.json", "{}")
    write(tmp_path / "docker-compose.yml", "services:\n  backend:\n    image: test\n")
    write(
        slice_dir / "runtime-smoke.json",
        json.dumps({"url": "http://localhost:3000/app", "must_contain": ["Inventory"], "forbid": ["Unhandled error"]}),
    )
    write(
        slice_dir / "qa-evidence.json",
        json.dumps(
            {
                "generated_by": {
                    "command": "python scripts\\validate\\gate.py --root . --slice feature-memory\\inventory\\slice.md",
                    "cwd": ".",
                },
                "runs": [
                    {
                        "command": "uv run pytest --cov=src --cov-report=json:coverage.json --cov-fail-under=80",
                        "cwd": "backend",
                        "exit_code": 0,
                        "started_at": "2026-06-29T00:00:00Z",
                        "finished_at": "2026-06-29T00:00:01Z",
                        "output_path": "feature-memory/inventory/evidence/backend.txt",
                    },
                    {
                        "command": "validate-tools project-layout .",
                        "cwd": ".",
                        "exit_code": 0,
                        "started_at": "2026-06-29T00:00:01Z",
                        "finished_at": "2026-06-29T00:00:02Z",
                        "output_path": "feature-memory/inventory/evidence/layout.txt",
                    },
                    {
                        "command": "docker compose up --build --wait",
                        "cwd": ".",
                        "exit_code": 0,
                        "started_at": "2026-06-29T00:00:02Z",
                        "finished_at": "2026-06-29T00:00:03Z",
                        "output_path": "feature-memory/inventory/evidence/docker-compose-up.txt",
                    },
                    {
                        "command": "python scripts\\validate\\runtime-smoke.py --config feature-memory\\inventory\\runtime-smoke.json",
                        "cwd": ".",
                        "exit_code": 0,
                        "started_at": "2026-06-29T00:00:03Z",
                        "finished_at": "2026-06-29T00:00:04Z",
                        "output_path": "feature-memory/inventory/evidence/runtime-smoke.txt",
                    },
                    {
                        "command": "uv run pytest --cov=src --cov-report=json:coverage.json --cov-fail-under=80",
                        "cwd": "backend",
                        "exit_code": 0,
                        "started_at": "2026-06-29T00:00:04Z",
                        "finished_at": "2026-06-29T00:00:05Z",
                        "output_path": "feature-memory/inventory/evidence/backend.txt",
                    },
                    {
                        "command": "npx pnpm@10.16.0 --dir frontend test:coverage",
                        "cwd": ".",
                        "exit_code": 0,
                        "started_at": "2026-06-29T00:00:05Z",
                        "finished_at": "2026-06-29T00:00:06Z",
                        "output_path": "feature-memory/inventory/evidence/frontend.txt",
                    },
                    {
                        "command": "npx pnpm@10.16.0 --dir frontend build",
                        "cwd": ".",
                        "exit_code": 0,
                        "started_at": "2026-06-29T00:00:06Z",
                        "finished_at": "2026-06-29T00:00:07Z",
                        "output_path": "feature-memory/inventory/evidence/build.txt",
                    },
                    {
                        "command": "npx pnpm@10.16.0 --dir frontend e2e",
                        "cwd": ".",
                        "exit_code": 0,
                        "started_at": "2026-06-29T00:00:07Z",
                        "finished_at": "2026-06-29T00:00:08Z",
                        "output_path": "feature-memory/inventory/evidence/e2e.txt",
                    },
                    {
                        "command": "docker compose down --remove-orphans",
                        "cwd": ".",
                        "exit_code": 0,
                        "started_at": "2026-06-29T00:00:08Z",
                        "finished_at": "2026-06-29T00:00:09Z",
                        "output_path": "feature-memory/inventory/evidence/docker-compose-down.txt",
                    },
                ],
                "unit_coverage": [
                    {"surface": "backend", "minimum_percent": 80, "actual_percent": 79, "summary_path": "backend/coverage.json"}
                ],
            }
        ),
    )

    findings = validate_qa_evidence(tmp_path)
    messages = "\n".join(finding.format() for finding in findings)

    assert "backend coverage 79% is below required 80%" in messages
    assert "missing frontend unit coverage" in messages
    assert "missing e2e_coverage_path" in messages


def test_e2e_coverage_requires_all_initial_prompt_stories_to_map_to_tests(tmp_path: Path) -> None:
    slice_dir = tmp_path / "feature-memory/inventory"
    write(slice_dir / "slice.md", "## Status\n- State: active\n")
    write(
        slice_dir / "e2e-coverage.json",
        json.dumps(
            {
                "user_stories": [
                    {"id": "US-001", "prompt_text": "track warehouse items", "covered_by": ["e2e-001"]},
                    {"id": "US-002", "prompt_text": "match vendors", "covered_by": []},
                ],
                "tests": [
                    {
                        "id": "e2e-001",
                        "location": "frontend/e2e/warehouse.spec.ts::tracks items",
                        "covers": ["US-001"],
                    }
                ],
            }
        ),
    )
    write(tmp_path / "frontend/e2e/warehouse.spec.ts", "// Covers: US-001\ntest('tracks items', async () => {})\n")

    findings = validate_e2e_coverage(tmp_path)
    messages = "\n".join(finding.format() for finding in findings)

    assert "user story US-002 is not covered by any E2E test" in messages
    assert "E2E test file missing test id marker e2e-001" in messages


def test_tooling_rejects_unconfigured_validate_tools_run_and_root_manifest_checks(tmp_path: Path) -> None:
    write(
        tmp_path / ".codex/hooks/verify-subagent.sh",
        "validate-tools run\nif [ -f pyproject.toml ]; then echo backend; fi\nif [ -f package.json ]; then echo frontend; fi\n",
    )
    write(tmp_path / "frontend/package.json", json.dumps({"scripts": {"lint": "next lint"}}))

    findings = validate_tooling(tmp_path)
    messages = "\n".join(finding.format() for finding in findings)

    assert "validate-tools run requires config" in messages
    assert "backend/pyproject.toml" in messages
    assert "frontend/package.json" in messages
    assert "lint script must be non-interactive" in messages

