from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts.validate.playwright_stories import validate_playwright_stories


def write_slice(tmp_path: Path, table_header: str, row_location: str) -> Path:
    slice_dir = tmp_path / "feature-memory" / "story"
    slice_dir.mkdir(parents=True)
    (slice_dir / "slice.md").write_text(
        f"""# Slice

## E2E Test Stories
| Story ID | User Story | Criteria | {table_header} | Seed/Setup | Assertions | Slugs |
|---|---|---|---|---|---|---|
| e2e-001 | As a user, I want save, so data persists. | AC-001 | {row_location} | fixture | visible | frontend/13-e2e-playwright |

## QA Handoff
- Playwright story tests required: yes
- Focused Playwright command: pnpm e2e -- save
""",
        encoding="utf-8",
    )
    return slice_dir / "slice.md"


def test_valid_story_location_and_comment_pass(tmp_path: Path) -> None:
    write_slice(tmp_path, "Test Location", "frontend/e2e/save.spec.ts::save")
    test_file = tmp_path / "frontend" / "e2e" / "save.spec.ts"
    test_file.parent.mkdir(parents=True)
    test_file.write_text(
        "import { test } from '@playwright/test';\n"
        "// Story: As a user, I want save, so data persists.\n"
        "test('save', async () => {\n"
        "  // 1) open page\n"
        "  // 2) click save\n"
        "});\n",
        encoding="utf-8",
    )

    assert validate_playwright_stories(tmp_path) == []


def test_stale_spec_file_header_is_reported(tmp_path: Path) -> None:
    write_slice(tmp_path, "Spec File", "frontend/e2e/save.spec.ts")

    findings = validate_playwright_stories(tmp_path)

    assert any("Test Location, not Spec File" in f.message for f in findings)


def test_missing_story_comment_is_reported(tmp_path: Path) -> None:
    write_slice(tmp_path, "Test Location", "frontend/e2e/save.spec.ts::save")
    test_file = tmp_path / "frontend" / "e2e" / "save.spec.ts"
    test_file.parent.mkdir(parents=True)
    test_file.write_text("test('save', async () => {});\n", encoding="utf-8")

    findings = validate_playwright_stories(tmp_path)

    assert any("missing // Story:" in f.message for f in findings)


def test_test_location_must_be_under_frontend_e2e(tmp_path: Path) -> None:
    write_slice(tmp_path, "Test Location", "tests/save.spec.ts::save")

    findings = validate_playwright_stories(tmp_path)

    assert any("under frontend/e2e" in f.message for f in findings)


def test_missing_step_comments_is_reported(tmp_path: Path) -> None:
    write_slice(tmp_path, "Test Location", "frontend/e2e/save.spec.ts::save")
    test_file = tmp_path / "frontend" / "e2e" / "save.spec.ts"
    test_file.parent.mkdir(parents=True)
    test_file.write_text(
        "// Story: As a user, I want save, so data persists.\n"
        "test('save', async () => {});\n",
        encoding="utf-8",
    )

    findings = validate_playwright_stories(tmp_path)

    assert any("missing numbered step comments" in f.message for f in findings)


def test_non_sequential_step_comments_is_reported(tmp_path: Path) -> None:
    write_slice(tmp_path, "Test Location", "frontend/e2e/save.spec.ts::save")
    test_file = tmp_path / "frontend" / "e2e" / "save.spec.ts"
    test_file.parent.mkdir(parents=True)
    test_file.write_text(
        "// Story: As a user, I want save, so data persists.\n"
        "test('save', async () => {\n"
        "  // 1) open page\n"
        "  // 3) click save\n"
        "});\n",
        encoding="utf-8",
    )

    findings = validate_playwright_stories(tmp_path)

    assert any("must be sequential starting at 1" in f.message for f in findings)


def test_step_comments_are_scoped_to_the_named_test_in_a_grouped_spec_file(
    tmp_path: Path,
) -> None:
    write_slice(tmp_path, "Test Location", "frontend/e2e/save.spec.ts::save")
    test_file = tmp_path / "frontend" / "e2e" / "save.spec.ts"
    test_file.parent.mkdir(parents=True)
    test_file.write_text(
        "// Story: As a user, I want load, so data is restored.\n"
        "test('load', async () => {\n"
        "  // 1) open page\n"
        "  // 2) load save\n"
        "});\n"
        "\n"
        "// Story: As a user, I want save, so data persists.\n"
        "test('save', async () => {\n"
        "  // 1) open page\n"
        "  // 2) click save\n"
        "});\n",
        encoding="utf-8",
    )

    assert validate_playwright_stories(tmp_path) == []


def test_step_comments_missing_from_the_named_test_is_reported_even_if_another_test_has_them(
    tmp_path: Path,
) -> None:
    write_slice(tmp_path, "Test Location", "frontend/e2e/save.spec.ts::save")
    test_file = tmp_path / "frontend" / "e2e" / "save.spec.ts"
    test_file.parent.mkdir(parents=True)
    test_file.write_text(
        "// Story: As a user, I want load, so data is restored.\n"
        "test('load', async () => {\n"
        "  // 1) open page\n"
        "  // 2) load save\n"
        "});\n"
        "\n"
        "// Story: As a user, I want save, so data persists.\n"
        "test('save', async () => {});\n",
        encoding="utf-8",
    )

    findings = validate_playwright_stories(tmp_path)

    assert any("missing numbered step comments" in f.message for f in findings)
