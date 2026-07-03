from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts.validate.feature_memory import (
    compaction_due_slices,
    global_rules_slugs,
    parse_dependencies,
    validate_compaction,
    validate_feature_memory,
)


SLUG = "frontend/13-e2e-playwright"

FULL_SLICE = f"""# Slice

## Status
active
## Request
Build user-facing thing
## Slice Boundary
One outcome
## Dependencies
- Depends on: none
- Rules: {SLUG}
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
| e2e-001 | As a user, I want save, so data persists. | AC-001 | frontend/e2e/save.spec.ts::save | fixture | visible | {SLUG} |
## Test Coverage
| Criteria | Test Type | Test Location |
|---|---|---|
| AC-001 | e2e | frontend/e2e/save.spec.ts::save |
## QA Handoff
- Playwright story tests required: yes
## Provenance
- {SLUG}
"""


def write_global_rules(root: Path, *slugs: str) -> None:
    slugs = slugs or (SLUG,)
    body = "# Rules\n\n"
    for slug in slugs:
        body += f'### `{slug}`\nSource: get_guideline("{slug}")\n- Always ...\n\n'
    (root / "feature-memory").mkdir(parents=True, exist_ok=True)
    (root / "feature-memory" / "rules.md").write_text(body, encoding="utf-8")


def write_slice(root: Path, name: str, body: str = FULL_SLICE) -> Path:
    slice_dir = root / "feature-memory" / name
    slice_dir.mkdir(parents=True, exist_ok=True)
    (slice_dir / "slice.md").write_text(body, encoding="utf-8")
    return slice_dir


def write_e2e_test(root: Path) -> None:
    test_file = root / "frontend/e2e/save.spec.ts"
    test_file.parent.mkdir(parents=True, exist_ok=True)
    test_file.write_text(
        "// Story: AC-001\ntest('save', async () => {})\n", encoding="utf-8"
    )


def test_parse_dependencies_reads_slug_refs() -> None:
    depends_on, rules = parse_dependencies(FULL_SLICE)
    assert depends_on == []  # "none"
    assert rules == [SLUG]


def test_parse_dependencies_missing_lines_return_none() -> None:
    depends_on, rules = parse_dependencies("## Dependencies\n(nothing)\n")
    assert depends_on is None
    assert rules is None


def test_global_rules_slugs_extracts_from_single_file(tmp_path: Path) -> None:
    write_global_rules(tmp_path, "backend/01-architecture", "frontend/05-forms")
    assert global_rules_slugs(tmp_path) == {
        "backend/01-architecture",
        "frontend/05-forms",
    }


def test_valid_full_slice_with_global_rules_passes(tmp_path: Path) -> None:
    write_global_rules(tmp_path)
    write_slice(tmp_path, "save")
    write_e2e_test(tmp_path)

    assert validate_feature_memory(tmp_path) == []


def test_missing_dependencies_section_is_reported(tmp_path: Path) -> None:
    write_slice(tmp_path, "broken", body="## Status\nactive\n")

    findings = validate_feature_memory(tmp_path)

    messages = "\n".join(f.message for f in findings)
    assert "missing required section ## Request" in messages
    assert "missing required section ## Dependencies" in messages


def test_referenced_slug_must_exist_in_global_rules(tmp_path: Path) -> None:
    # Global rules exists but does not define the slug the slice references.
    write_global_rules(tmp_path, "backend/01-architecture")
    write_slice(tmp_path, "save")
    write_e2e_test(tmp_path)

    findings = validate_feature_memory(tmp_path)

    assert any("referenced rule slug not found" in f.message for f in findings)


def test_unknown_dependency_feature_is_reported(tmp_path: Path) -> None:
    write_global_rules(tmp_path)
    write_e2e_test(tmp_path)
    body = FULL_SLICE.replace(
        "- Depends on: none", "- Depends on: feature-memory/ghost-feature"
    )
    write_slice(tmp_path, "save", body=body)

    findings = validate_feature_memory(tmp_path)

    assert any("dependency feature not found" in f.message for f in findings)


def test_global_rules_missing_provenance_is_reported(tmp_path: Path) -> None:
    (tmp_path / "feature-memory").mkdir(parents=True)
    (tmp_path / "feature-memory" / "rules.md").write_text(
        "# Rules\n\n### backend\n- Always ...\n", encoding="utf-8"
    )

    findings = validate_feature_memory(tmp_path)

    assert any("global rules.md missing" in f.message for f in findings)


def test_category_split_rules_directory_is_reported(tmp_path: Path) -> None:
    write_global_rules(tmp_path)
    write_slice(tmp_path, "save")
    write_e2e_test(tmp_path)
    (tmp_path / "feature-memory" / "rules").mkdir(parents=True)

    findings = validate_feature_memory(tmp_path)

    assert any("not a category-split directory" in f.message for f in findings)


def test_stray_per_slice_rules_md_is_reported(tmp_path: Path) -> None:
    write_global_rules(tmp_path)
    slice_dir = write_slice(tmp_path, "save")
    write_e2e_test(tmp_path)
    (slice_dir / "rules.md").write_text(
        'Source: get_guideline("x")\n', encoding="utf-8"
    )

    findings = validate_feature_memory(tmp_path)

    assert any("rules are global" in f.message for f in findings)


def test_role_specific_memory_directory_is_reported(tmp_path: Path) -> None:
    write_global_rules(tmp_path)
    slice_dir = write_slice(tmp_path, "role-dir")
    write_e2e_test(tmp_path)
    (slice_dir / "backend").mkdir(parents=True)

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
    assert any(
        "compaction due" in finding.message for finding in validate_compaction(tmp_path)
    )


def test_compaction_ignores_history_and_non_approved_slices(tmp_path: Path) -> None:
    write_approved_slice(tmp_path, "one", "2026-01-01")
    write_approved_slice(tmp_path, "two", "2026-01-02")
    write_approved_slice(tmp_path, "three", "2026-01-03")
    history = tmp_path / "feature-memory" / "history" / "old"
    history.mkdir(parents=True)
    (history / "slice.md").write_text(
        "## Status\n- State: QA APPROVED\n", encoding="utf-8"
    )
    blocked = tmp_path / "feature-memory" / "blocked"
    blocked.mkdir(parents=True)
    (blocked / "slice.md").write_text(
        "## Status\n- State: QA BLOCKED\n", encoding="utf-8"
    )

    assert compaction_due_slices(tmp_path) == []
