from __future__ import annotations

import json
import re
from pathlib import Path

from scripts.validate.checks.common import (
    Finding,
    acceptance_criteria_ids,
    has_heading,
    line_number,
    parse_md_table,
    read_text,
    split_ids,
)
from scripts.validate.checks.feature_memory import feature_memory_roots


def validate_playwright_stories(root: Path) -> list[Finding]:
    findings: list[Finding] = []
    for memory_root in feature_memory_roots(root):
        for slice_md in memory_root.rglob("slice.md"):
            if "history" in slice_md.relative_to(memory_root).parts:
                continue
            rel = slice_md.relative_to(root).as_posix()
            text = read_text(slice_md)
            if "Spec File" in text:
                findings.append(
                    Finding(
                        rel,
                        "E2E Test Stories must use Test Location, not Spec File",
                        line_number(text, text.index("Spec File")),
                    )
                )
            if not has_heading(text, "E2E Test Stories"):
                continue
            rows = parse_md_table(text, "E2E Test Stories")
            if not rows:
                findings.append(
                    Finding(rel, "E2E Test Stories table is missing or malformed")
                )
                continue
            for index, row in enumerate(rows, start=1):
                for column in [
                    "Story ID",
                    "User Story",
                    "Test Location",
                    "Seed/Setup",
                    "Assertions",
                    "Slugs",
                ]:
                    if not row.get(column):
                        findings.append(
                            Finding(
                                rel, f"E2E Test Stories row {index} missing {column}"
                            )
                        )
                criteria_ids, _ = acceptance_criteria_ids(text)
                if criteria_ids and not split_ids(row.get("Criteria", "")):
                    findings.append(
                        Finding(
                            rel,
                            f"E2E Test Stories row {index} missing Criteria AC-### reference",
                        )
                    )
                story = row.get("User Story", "")
                if not re.search(r"\bAs a\b.+\bI want\b.+\bso\b", story, re.IGNORECASE):
                    findings.append(
                        Finding(
                            rel,
                            f"E2E Test Stories row {index} has non-standard user story shape",
                        )
                    )
                location = row.get("Test Location", "")
                if location and not location.startswith("frontend/e2e/"):
                    findings.append(
                        Finding(
                            rel,
                            f"E2E Test Stories row {index} test location must be under frontend/e2e/**",
                        )
                    )
                if location.startswith("frontend/e2e/"):
                    path_part, _, test_name = location.partition("::")
                    test_file = root / path_part
                    if not test_file.exists():
                        findings.append(
                            Finding(
                                path_part,
                                f"missing Playwright test file for story row {index}",
                            )
                        )
                    else:
                        test_text = read_text(test_file)
                        if "// Story:" not in test_text:
                            findings.append(
                                Finding(
                                    path_part,
                                    f"missing // Story: comment for story row {index}",
                                )
                            )
                        elif test_name and test_name not in test_text:
                            findings.append(
                                Finding(
                                    path_part,
                                    f"test name {test_name!r} not found for story row {index}",
                                )
                            )
            if (
                "Playwright story tests required: yes" in text
                and "Focused Playwright command:" not in text
            ):
                findings.append(
                    Finding(rel, "QA Handoff requires a focused Playwright command")
                )
    return findings


def validate_e2e_coverage(root: Path) -> list[Finding]:
    findings: list[Finding] = []
    for memory_root in feature_memory_roots(root):
        for slice_md in memory_root.rglob("slice.md"):
            if "history" in slice_md.relative_to(memory_root).parts:
                continue
            rel = slice_md.parent.relative_to(root).as_posix()
            text = read_text(slice_md)
            is_user_facing = "user-facing" in text.lower() or has_heading(
                text, "E2E Test Stories"
            )
            coverage_path = slice_md.parent / "e2e-coverage.json"
            if not coverage_path.exists():
                if is_user_facing:
                    findings.append(
                        Finding(
                            f"{rel}/e2e-coverage.json",
                            "full user-facing slice must track initial-prompt E2E coverage",
                        )
                    )
                continue
            try:
                data = json.loads(read_text(coverage_path))
            except json.JSONDecodeError as exc:
                findings.append(
                    Finding(
                        coverage_path.relative_to(root).as_posix(),
                        f"invalid E2E coverage JSON: {exc}",
                    )
                )
                continue
            stories = data.get("user_stories") if isinstance(data, dict) else None
            tests = data.get("tests") if isinstance(data, dict) else None
            if not isinstance(stories, list) or not stories:
                findings.append(
                    Finding(
                        coverage_path.relative_to(root).as_posix(),
                        "E2E coverage JSON must contain user_stories[] from the initial prompt",
                    )
                )
                continue
            if not isinstance(tests, list) or not tests:
                findings.append(
                    Finding(
                        coverage_path.relative_to(root).as_posix(),
                        "E2E coverage JSON must contain tests[]",
                    )
                )
                continue
            test_ids = {str(test.get("id")) for test in tests if isinstance(test, dict)}
            covered_story_ids: set[str] = set()
            for index, story in enumerate(stories, start=1):
                if not isinstance(story, dict):
                    findings.append(
                        Finding(
                            coverage_path.relative_to(root).as_posix(),
                            f"user_stories entry {index} must be an object",
                        )
                    )
                    continue
                story_id = str(story.get("id", ""))
                if not re.fullmatch(r"US-\d{3}", story_id):
                    findings.append(
                        Finding(
                            coverage_path.relative_to(root).as_posix(),
                            f"user_stories entry {index} must use US-### id",
                        )
                    )
                if not story.get("prompt_text"):
                    findings.append(
                        Finding(
                            coverage_path.relative_to(root).as_posix(),
                            f"user story {story_id or index} missing prompt_text",
                        )
                    )
                covered_by = story.get("covered_by")
                if not isinstance(covered_by, list) or not covered_by:
                    findings.append(
                        Finding(
                            coverage_path.relative_to(root).as_posix(),
                            f"user story {story_id or index} is not covered by any E2E test",
                        )
                    )
                    continue
                for test_id in covered_by:
                    if str(test_id) not in test_ids:
                        findings.append(
                            Finding(
                                coverage_path.relative_to(root).as_posix(),
                                f"user story {story_id} references unknown E2E test {test_id}",
                            )
                        )
                covered_story_ids.add(story_id)
            known_story_ids = {
                str(story.get("id")) for story in stories if isinstance(story, dict)
            }
            for index, test in enumerate(tests, start=1):
                if not isinstance(test, dict):
                    findings.append(
                        Finding(
                            coverage_path.relative_to(root).as_posix(),
                            f"tests entry {index} must be an object",
                        )
                    )
                    continue
                test_id = str(test.get("id", ""))
                location = str(test.get("location", ""))
                covers = test.get("covers")
                if not test_id:
                    findings.append(
                        Finding(
                            coverage_path.relative_to(root).as_posix(),
                            f"tests entry {index} missing id",
                        )
                    )
                if not isinstance(covers, list) or not covers:
                    findings.append(
                        Finding(
                            coverage_path.relative_to(root).as_posix(),
                            f"E2E test {test_id or index} must list covered US-### ids",
                        )
                    )
                else:
                    for story_id in covers:
                        if str(story_id) not in known_story_ids:
                            findings.append(
                                Finding(
                                    coverage_path.relative_to(root).as_posix(),
                                    f"E2E test {test_id} references unknown user story {story_id}",
                                )
                            )
                path_part, _, test_name = location.partition("::")
                if not path_part:
                    findings.append(
                        Finding(
                            coverage_path.relative_to(root).as_posix(),
                            f"E2E test {test_id or index} missing location",
                        )
                    )
                    continue
                test_file = root / path_part
                if not test_file.exists():
                    findings.append(
                        Finding(
                            path_part,
                            f"missing E2E test file for coverage test {test_id or index}",
                        )
                    )
                    continue
                test_text = read_text(test_file)
                if test_id and test_id not in test_text:
                    findings.append(
                        Finding(
                            path_part, f"E2E test file missing test id marker {test_id}"
                        )
                    )
                for story_id in covers if isinstance(covers, list) else []:
                    if str(story_id) not in test_text:
                        findings.append(
                            Finding(
                                path_part,
                                f"E2E test {test_id or index} missing coverage marker for {story_id}",
                            )
                        )
                if test_name and test_name not in test_text:
                    findings.append(
                        Finding(path_part, f"E2E test name {test_name!r} not found")
                    )
            for story_id in sorted(known_story_ids - covered_story_ids):
                findings.append(
                    Finding(
                        coverage_path.relative_to(root).as_posix(),
                        f"initial prompt user story {story_id} is not covered",
                    )
                )
    return findings


def validate_qa_contract(root: Path) -> list[Finding]:
    findings = validate_playwright_stories(root)
    from scripts.validate.checks.feature_memory import validate_test_coverage_mapping

    findings.extend(validate_test_coverage_mapping(root))
    findings.extend(validate_e2e_coverage(root))
    frontend_root = root / "frontend"
    if frontend_root.exists() and not (frontend_root / "e2e").exists():
        findings.append(
            Finding("frontend/e2e", "QA needs the frontend/e2e Playwright test folder")
        )
    return findings
