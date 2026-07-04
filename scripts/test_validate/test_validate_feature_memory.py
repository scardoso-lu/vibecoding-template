from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts.validate.services.feature_memory import (
    global_rules_slugs,
    parse_dependencies,
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
- PRD: memory/PRD/save/prd.md
- ADR: memory/ADR/save/adr.md
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
    (root / "memory").mkdir(parents=True, exist_ok=True)
    (root / "memory" / "rules.md").write_text(body, encoding="utf-8")


def write_prd_adr(root: Path, name: str = "save") -> None:
    prd_dir = root / "memory" / "PRD" / name
    adr_dir = root / "memory" / "ADR" / name
    prd_dir.mkdir(parents=True, exist_ok=True)
    adr_dir.mkdir(parents=True, exist_ok=True)
    (prd_dir / "prd.md").write_text("# PRD\n", encoding="utf-8")
    (adr_dir / "adr.md").write_text("# ADR\n", encoding="utf-8")


def write_slice(root: Path, name: str, body: str = FULL_SLICE) -> Path:
    write_prd_adr(root)
    slice_dir = root / "memory" / "feature" / name
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
    prd, adr, depends_on, rules = parse_dependencies(FULL_SLICE)
    assert prd == ["memory/PRD/save/prd.md"]
    assert adr == ["memory/ADR/save/adr.md"]
    assert depends_on == []  # "none"
    assert rules == [SLUG]


def test_parse_dependencies_missing_lines_return_none() -> None:
    prd, adr, depends_on, rules = parse_dependencies("## Dependencies\n(nothing)\n")
    assert prd is None
    assert adr is None
    assert depends_on is None
    assert rules is None


def test_parse_dependencies_joins_wrapped_continuation_lines() -> None:
    # A long `Rules:` list commonly wraps across several indented physical lines;
    # every slug on every physical line must still be parsed, not just the first line.
    text = """## Dependencies
- PRD: memory/PRD/save/prd.md
- ADR: memory/ADR/save/adr.md
- Depends on: none
- Rules: backend/01-a, backend/02-b,
  backend/03-c, backend/04-d,
  backend/05-e
## Do Not Touch
"""
    prd, adr, depends_on, rules = parse_dependencies(text)
    assert prd == ["memory/PRD/save/prd.md"]
    assert adr == ["memory/ADR/save/adr.md"]
    assert depends_on == []
    assert rules == [
        "backend/01-a",
        "backend/02-b",
        "backend/03-c",
        "backend/04-d",
        "backend/05-e",
    ]


def test_parse_dependencies_tolerates_inline_parenthetical_annotations() -> None:
    # An architect may annotate an ADR ref with the decision IDs it bundles, and
    # explain why `Depends on:` is none. The parser must still resolve the bare ref
    # rather than treating the annotation's commas as extra, invalid refs.
    text = """## Dependencies
- PRD: memory/PRD/save/prd.md
- ADR: memory/ADR/save/adr.md (ADR-001 foundation, ADR-002 capture
  architecture, ADR-003 access control)
- Depends on: none (single self-contained feature; foundation bootstrapped in
  Step 1 of this slice)
- Rules: backend/01-a
## Do Not Touch
"""
    prd, adr, depends_on, rules = parse_dependencies(text)
    assert prd == ["memory/PRD/save/prd.md"]
    assert adr == ["memory/ADR/save/adr.md"]
    assert depends_on == []
    assert rules == ["backend/01-a"]


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


def test_legacy_feature_memory_root_is_reported(tmp_path: Path) -> None:
    (tmp_path / "feature-memory" / "old").mkdir(parents=True)
    (tmp_path / "feature-memory" / "old" / "slice.md").write_text(
        "## Status\nactive\n", encoding="utf-8"
    )

    findings = validate_feature_memory(tmp_path)

    assert any("legacy feature-memory directory" in f.message for f in findings)


def test_slice_outside_memory_feature_is_reported(tmp_path: Path) -> None:
    (tmp_path / "memory" / "loose").mkdir(parents=True)
    (tmp_path / "memory" / "loose" / "slice.md").write_text(
        "## Status\nactive\n", encoding="utf-8"
    )

    findings = validate_feature_memory(tmp_path)

    assert any("memory/feature/<feature>/slice.md" in f.message for f in findings)


def test_memory_rejects_unknown_top_level_entries(tmp_path: Path) -> None:
    (tmp_path / "memory" / "backend").mkdir(parents=True)

    findings = validate_feature_memory(tmp_path)

    assert any("memory may only contain" in f.message for f in findings)


def test_prd_and_adr_dependencies_must_use_grouped_memory_paths(
    tmp_path: Path,
) -> None:
    write_global_rules(tmp_path)
    body = FULL_SLICE.replace(
        "memory/PRD/save/prd.md", "memory/feature/save/prd.md"
    ).replace("memory/ADR/save/adr.md", "memory/feature/save/adr.md")
    write_slice(tmp_path, "save", body=body)
    write_e2e_test(tmp_path)

    findings = validate_feature_memory(tmp_path)
    messages = "\n".join(f.message for f in findings)

    assert "PRD dependency must use memory/PRD/<purpose>/prd.md" in messages
    assert "ADR dependency must use memory/ADR/<purpose>/adr.md" in messages


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
        "- Depends on: none", "- Depends on: memory/feature/ghost-feature"
    )
    write_slice(tmp_path, "save", body=body)

    findings = validate_feature_memory(tmp_path)

    assert any("dependency feature not found" in f.message for f in findings)


def test_global_rules_missing_provenance_is_reported(tmp_path: Path) -> None:
    (tmp_path / "memory").mkdir(parents=True)
    (tmp_path / "memory" / "rules.md").write_text(
        "# Rules\n\n### backend\n- Always ...\n", encoding="utf-8"
    )

    findings = validate_feature_memory(tmp_path)

    assert any("global rules.md missing" in f.message for f in findings)


def test_category_split_rules_directory_is_reported(tmp_path: Path) -> None:
    write_global_rules(tmp_path)
    write_slice(tmp_path, "save")
    write_e2e_test(tmp_path)
    (tmp_path / "memory" / "rules").mkdir(parents=True)

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

    assert any("role-specific memory directory" in f.message for f in findings)


