from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts.validate.feature_memory import compaction_due_slices, validate_compaction, validate_feature_memory


FULL_SLICE = """# Slice

## Status
active
## Request
Build user-facing thing
## Slice Boundary
One outcome
## Do Not Touch
Nothing else
## Implementation Plan
Rows
## Acceptance Criteria
| ID | Criterion |
|---|---|
| AC-001 | Works |
## E2E Test Stories
| Story ID | User Story | Criteria | Test Location | Seed/Setup | Assertions | Slugs |
|---|---|---|---|---|---|---|
| e2e-001 | As a user, I want save, so data persists. | AC-001 | frontend/e2e/save.spec.ts::save | fixture | visible | frontend/13-e2e-playwright |
## Test Coverage
| Criteria | Test Type | Test Location |
|---|---|---|
| AC-001 | e2e | frontend/e2e/save.spec.ts::save |
## QA Handoff
- Playwright story tests required: yes
## Provenance
- frontend/13-e2e-playwright
"""


def test_valid_full_slice_passes(tmp_path: Path) -> None:
    slice_dir = tmp_path / "feature-memory" / "save"
    slice_dir.mkdir(parents=True)
    (slice_dir / "slice.md").write_text(FULL_SLICE, encoding="utf-8")
    (slice_dir / "rules.md").write_text(
        '## QA\nSource: get_guideline("frontend/13-e2e-playwright")\n',
        encoding="utf-8",
    )
    test_file = tmp_path / "frontend/e2e/save.spec.ts"
    test_file.parent.mkdir(parents=True)
    test_file.write_text("// Story: AC-001\ntest('save', async () => {})\n", encoding="utf-8")

    assert validate_feature_memory(tmp_path) == []


def test_missing_rules_and_sections_are_reported(tmp_path: Path) -> None:
    slice_dir = tmp_path / "feature-memory" / "broken"
    slice_dir.mkdir(parents=True)
    (slice_dir / "slice.md").write_text("## Status\nactive\n", encoding="utf-8")

    findings = validate_feature_memory(tmp_path)

    messages = "\n".join(f.message for f in findings)
    assert "missing required section ## Request" in messages
    assert "missing rules.md" in messages


def test_role_specific_memory_directory_is_reported(tmp_path: Path) -> None:
    slice_dir = tmp_path / "feature-memory" / "role-dir"
    (slice_dir / "backend").mkdir(parents=True)
    (slice_dir / "slice.md").write_text(FULL_SLICE, encoding="utf-8")
    (slice_dir / "rules.md").write_text(
        'Source: get_guideline("backend/01-architecture")\n',
        encoding="utf-8",
    )

    findings = validate_feature_memory(tmp_path)

    assert any("role-specific feature-memory directory" in f.message for f in findings)


def write_approved_slice(root: Path, name: str, date: str) -> None:
    slice_dir = root / "feature-memory" / name
    slice_dir.mkdir(parents=True)
    (slice_dir / "slice.md").write_text(
        f"""# {name}

## Status
- State: QA APPROVED
- QA verdict date: {date}
""",
        encoding="utf-8",
    )


def test_compaction_due_when_four_active_approved_slices_exist(tmp_path: Path) -> None:
    write_approved_slice(tmp_path, "one", "2026-01-01")
    write_approved_slice(tmp_path, "two", "2026-01-02")
    write_approved_slice(tmp_path, "three", "2026-01-03")
    write_approved_slice(tmp_path, "four", "2026-01-04")

    due = [path.name for path in compaction_due_slices(tmp_path)]

    assert due == ["one", "two", "three"]
    assert any("compaction due" in finding.message for finding in validate_compaction(tmp_path))


def test_compaction_ignores_history_and_non_approved_slices(tmp_path: Path) -> None:
    write_approved_slice(tmp_path, "one", "2026-01-01")
    write_approved_slice(tmp_path, "two", "2026-01-02")
    write_approved_slice(tmp_path, "three", "2026-01-03")
    history = tmp_path / "feature-memory" / "history" / "old"
    history.mkdir(parents=True)
    (history / "slice.md").write_text("## Status\n- State: QA APPROVED\n", encoding="utf-8")
    blocked = tmp_path / "feature-memory" / "blocked"
    blocked.mkdir(parents=True)
    (blocked / "slice.md").write_text("## Status\n- State: QA BLOCKED\n", encoding="utf-8")

    assert compaction_due_slices(tmp_path) == []



