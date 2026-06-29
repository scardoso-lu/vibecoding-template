from __future__ import annotations

import re
from pathlib import Path

from scripts.validate.checks.common import Finding, acceptance_criteria_ids, has_heading, parse_md_table, read_text, split_ids

def feature_memory_roots(root: Path) -> list[Path]:
    path = root / "feature-memory"
    return [path] if path.exists() else []


def slice_state(slice_md: Path) -> str:
    text = read_text(slice_md)
    match = re.search(r"^\s*-?\s*State:\s*(.+?)\s*$", text, re.MULTILINE)
    return match.group(1).strip() if match else ""


def slice_qa_date(slice_md: Path) -> str:
    text = read_text(slice_md)
    match = re.search(r"^\s*-?\s*QA verdict date:\s*(.+?)\s*$", text, re.MULTILINE)
    return match.group(1).strip() if match else ""


def approved_active_slices(root: Path) -> list[Path]:
    approved: list[Path] = []
    for memory_root in feature_memory_roots(root):
        for slice_md in memory_root.rglob("slice.md"):
            relative_parts = slice_md.relative_to(memory_root).parts
            if "history" in relative_parts:
                continue
            if slice_state(slice_md).upper() == "QA APPROVED":
                approved.append(slice_md.parent)
    return sorted(
        approved,
        key=lambda path: (
            slice_qa_date(path / "slice.md") or "9999-99-99",
            path.stat().st_mtime,
            path.as_posix(),
        ),
    )


def compaction_due_slices(root: Path) -> list[Path]:
    approved = approved_active_slices(root)
    if len(approved) < 4:
        return []
    return approved[:3]


def validate_compaction(root: Path) -> list[Finding]:
    findings: list[Finding] = []
    due = compaction_due_slices(root)
    if due:
        names = ", ".join(path.relative_to(root).as_posix() for path in due)
        findings.append(
            Finding(
                "feature-memory",
                f"compaction due: move the three oldest QA-approved slices to feature-memory/history/: {names}",
            )
        )
    return findings


def validate_feature_memory(root: Path) -> list[Finding]:
    findings: list[Finding] = []
    required_sections = [
        "Status",
        "Request",
        "Slice Boundary",
        "Do Not Touch",
        "Implementation Plan",
        "Acceptance Criteria",
        "QA Handoff",
    ]
    for memory_root in feature_memory_roots(root):
        for slice_md in memory_root.rglob("slice.md"):
            if "history" in slice_md.relative_to(memory_root).parts:
                continue
            rel = slice_md.relative_to(root).as_posix()
            text = read_text(slice_md)
            is_minimal = "template-minimal" in text or "Minimal Slice" in text
            sections = ["Status", "Do Not Touch", "Acceptance Criteria", "QA Handoff"] if is_minimal else required_sections
            for section in sections:
                if not has_heading(text, section):
                    findings.append(Finding(rel, f"missing required section ## {section}"))
            if not is_minimal and "Provenance" not in text:
                findings.append(Finding(rel, "missing provenance section or markers"))
            if not is_minimal:
                criteria_ids, invalid_criteria = acceptance_criteria_ids(text)
                if invalid_criteria:
                    findings.append(Finding(rel, "acceptance criteria must include stable AC-### IDs"))
                if criteria_ids and not has_heading(text, "Test Coverage"):
                    findings.append(Finding(rel, "full slice with acceptance IDs must include ## Test Coverage"))
            if "user-facing" in text.lower() and not has_heading(text, "E2E Test Stories"):
                findings.append(Finding(rel, "user-facing slice missing ## E2E Test Stories"))
            for forbidden in ["00-shared", "backend", "frontend", "qa"]:
                if (slice_md.parent / forbidden).exists():
                    findings.append(Finding((slice_md.parent / forbidden).relative_to(root).as_posix(), "role-specific feature-memory directory is not allowed"))
            rules_md = slice_md.parent / "rules.md"
            if not is_minimal:
                if not rules_md.exists():
                    findings.append(Finding(rules_md.relative_to(root).as_posix(), "missing rules.md for full slice"))
                else:
                    rules_text = read_text(rules_md)
                    if 'Source: get_guideline("' not in rules_text:
                        findings.append(Finding(rules_md.relative_to(root).as_posix(), 'rules.md missing Source: get_guideline("<slug>") provenance'))
    return findings


def validate_test_coverage_mapping(root: Path) -> list[Finding]:
    findings: list[Finding] = []
    for memory_root in feature_memory_roots(root):
        for slice_md in memory_root.rglob("slice.md"):
            if "history" in slice_md.relative_to(memory_root).parts:
                continue
            rel = slice_md.relative_to(root).as_posix()
            text = read_text(slice_md)
            is_minimal = "template-minimal" in text or "Minimal Slice" in text
            if is_minimal:
                continue
            criteria_ids, invalid_criteria = acceptance_criteria_ids(text)
            if invalid_criteria or not criteria_ids:
                continue
            covered: set[str] = set()
            for row in parse_md_table(text, "E2E Test Stories"):
                criteria_value = row.get("Criteria") or row.get("Acceptance Criteria") or row.get("Criterion IDs") or ""
                row_ids = split_ids(criteria_value)
                if not row_ids:
                    findings.append(Finding(rel, f"E2E story {row.get('Story ID', '<unknown>')} must reference Criteria AC-### IDs"))
                unknown = row_ids - criteria_ids
                for criterion_id in sorted(unknown):
                    findings.append(Finding(rel, f"E2E story references unknown acceptance criterion {criterion_id}"))
                covered.update(row_ids & criteria_ids)
            coverage_rows = parse_md_table(text, "Test Coverage")
            if not coverage_rows:
                findings.append(Finding(rel, "Test Coverage table is missing or malformed"))
            for index, row in enumerate(coverage_rows, start=1):
                criteria_value = row.get("Criteria") or row.get("Criterion IDs") or row.get("Acceptance Criteria") or ""
                row_ids = split_ids(criteria_value)
                if not row_ids:
                    findings.append(Finding(rel, f"Test Coverage row {index} must reference Criteria AC-### IDs"))
                unknown = row_ids - criteria_ids
                for criterion_id in sorted(unknown):
                    findings.append(Finding(rel, f"Test Coverage references unknown acceptance criterion {criterion_id}"))
                covered.update(row_ids & criteria_ids)
                location = row.get("Test Location", "") or row.get("Location", "")
                if location:
                    path_part = location.strip("`").partition("::")[0]
                    if path_part and not (root / path_part).exists():
                        findings.append(Finding(path_part, f"missing test file for Test Coverage row {index}"))
                else:
                    findings.append(Finding(rel, f"Test Coverage row {index} missing Test Location"))
            for criterion_id in sorted(criteria_ids - covered):
                findings.append(Finding(rel, f"acceptance criterion {criterion_id} is not mapped to any test"))
    return findings

