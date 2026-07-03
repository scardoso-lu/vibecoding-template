from __future__ import annotations

import re
from pathlib import Path

from scripts.validate.models import (
    Finding,
    acceptance_criteria_ids,
    has_heading,
    parse_md_table,
    read_text,
    section_text,
    split_ids,
)

GLOBAL_RULES_FILE = "rules.md"


def feature_memory_roots(root: Path) -> list[Path]:
    path = root / "feature-memory"
    return [path] if path.exists() else []


def global_rules_path(root: Path) -> Path:
    return root / "feature-memory" / GLOBAL_RULES_FILE


def global_rules_slugs(root: Path) -> set[str]:
    path = global_rules_path(root)
    if not path.exists():
        return set()
    return set(re.findall(r'get_guideline\("([^"]+)"\)', read_text(path)))


def _ref_list(value: str) -> list[str]:
    refs: list[str] = []
    for part in re.split(r"[,\n]", value):
        token = part.strip().strip("`").strip()
        if token and token.lower() != "none":
            refs.append(token.replace("\\", "/"))
    return refs


def parse_dependencies(text: str) -> tuple[list[str] | None, list[str] | None]:
    """Return (depends_on, rules) ref lists from the ## Dependencies section.

    A value of None means the corresponding line is absent entirely (a defect for
    full slices); an empty list means the line is present but resolves to `none`.
    """
    block = section_text(text, "Dependencies")
    depends_on: list[str] | None = None
    rules: list[str] | None = None
    for raw in block.splitlines():
        line = raw.strip().lstrip("-*").strip()
        lowered = line.lower()
        if lowered.startswith("depends on:"):
            depends_on = _ref_list(line.split(":", 1)[1])
        elif lowered.startswith("rules:"):
            rules = _ref_list(line.split(":", 1)[1])
    return depends_on, rules


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
        "Dependencies",
        "Do Not Touch",
        "Implementation Plan",
        "Acceptance Criteria",
        "QA Handoff",
    ]

    # Rules are one global file, feature-memory/rules.md, shared across every feature.
    # It must cite the guideline slugs it summarizes, and it is never split by category.
    rules_file = global_rules_path(root)
    if rules_file.exists() and 'Source: get_guideline("' not in read_text(rules_file):
        findings.append(
            Finding(
                rules_file.relative_to(root).as_posix(),
                'global rules.md missing Source: get_guideline("<slug>") provenance',
            )
        )
    if (root / "feature-memory" / "rules").is_dir():
        findings.append(
            Finding(
                "feature-memory/rules",
                "rules must be a single global feature-memory/rules.md, not a category-split directory",
            )
        )
    known_slugs = global_rules_slugs(root)

    for memory_root in feature_memory_roots(root):
        for slice_md in memory_root.rglob("slice.md"):
            relative_parts = slice_md.relative_to(memory_root).parts
            if "history" in relative_parts:
                continue
            if relative_parts and relative_parts[0] == "rules":
                # Reserved global rules area, not a feature slice.
                continue
            rel = slice_md.relative_to(root).as_posix()
            text = read_text(slice_md)
            is_minimal = "template-minimal" in text or "Minimal Slice" in text
            sections = (
                ["Status", "Do Not Touch", "Acceptance Criteria", "QA Handoff"]
                if is_minimal
                else required_sections
            )
            for section in sections:
                if not has_heading(text, section):
                    findings.append(
                        Finding(rel, f"missing required section ## {section}")
                    )
            if not is_minimal and "Provenance" not in text:
                findings.append(Finding(rel, "missing provenance section or markers"))
            if not is_minimal:
                criteria_ids, invalid_criteria = acceptance_criteria_ids(text)
                if invalid_criteria:
                    findings.append(
                        Finding(
                            rel, "acceptance criteria must include stable AC-### IDs"
                        )
                    )
                if criteria_ids and not has_heading(text, "Test Coverage"):
                    findings.append(
                        Finding(
                            rel,
                            "full slice with acceptance IDs must include ## Test Coverage",
                        )
                    )
            if "user-facing" in text.lower() and not has_heading(
                text, "E2E Test Stories"
            ):
                findings.append(
                    Finding(rel, "user-facing slice missing ## E2E Test Stories")
                )
            for forbidden in ["00-shared", "backend", "frontend", "qa"]:
                if (slice_md.parent / forbidden).exists():
                    findings.append(
                        Finding(
                            (slice_md.parent / forbidden).relative_to(root).as_posix(),
                            "role-specific feature-memory directory is not allowed",
                        )
                    )
            # Rules are one global file; a per-slice rules.md is a leftover from the old contract.
            stray_rules = slice_md.parent / "rules.md"
            if stray_rules.exists():
                findings.append(
                    Finding(
                        stray_rules.relative_to(root).as_posix(),
                        "rules are global; keep them in feature-memory/rules.md and link the slugs from the slice ## Dependencies",
                    )
                )

            if not is_minimal:
                depends_on, rules_refs = parse_dependencies(text)
                if depends_on is None:
                    findings.append(
                        Finding(
                            rel,
                            "## Dependencies must list a `Depends on:` line (other feature slices or none)",
                        )
                    )
                if rules_refs is None:
                    findings.append(
                        Finding(
                            rel,
                            "## Dependencies must list a `Rules:` line of guideline slugs from feature-memory/rules.md (or none)",
                        )
                    )
                for slug in rules_refs or []:
                    if slug not in known_slugs:
                        findings.append(
                            Finding(
                                rel,
                                f"referenced rule slug not found in feature-memory/rules.md: {slug}",
                            )
                        )
                for ref in depends_on or []:
                    dep_dir = (root / ref) if not Path(ref).is_absolute() else Path(ref)
                    if not (dep_dir / "slice.md").exists():
                        findings.append(
                            Finding(
                                rel,
                                f"dependency feature not found (no slice.md): {ref}",
                            )
                        )
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
                criteria_value = (
                    row.get("Criteria")
                    or row.get("Acceptance Criteria")
                    or row.get("Criterion IDs")
                    or ""
                )
                row_ids = split_ids(criteria_value)
                if not row_ids:
                    findings.append(
                        Finding(
                            rel,
                            f"E2E story {row.get('Story ID', '<unknown>')} must reference Criteria AC-### IDs",
                        )
                    )
                unknown = row_ids - criteria_ids
                for criterion_id in sorted(unknown):
                    findings.append(
                        Finding(
                            rel,
                            f"E2E story references unknown acceptance criterion {criterion_id}",
                        )
                    )
                covered.update(row_ids & criteria_ids)
            coverage_rows = parse_md_table(text, "Test Coverage")
            if not coverage_rows:
                findings.append(
                    Finding(rel, "Test Coverage table is missing or malformed")
                )
            for index, row in enumerate(coverage_rows, start=1):
                criteria_value = (
                    row.get("Criteria")
                    or row.get("Criterion IDs")
                    or row.get("Acceptance Criteria")
                    or ""
                )
                row_ids = split_ids(criteria_value)
                if not row_ids:
                    findings.append(
                        Finding(
                            rel,
                            f"Test Coverage row {index} must reference Criteria AC-### IDs",
                        )
                    )
                unknown = row_ids - criteria_ids
                for criterion_id in sorted(unknown):
                    findings.append(
                        Finding(
                            rel,
                            f"Test Coverage references unknown acceptance criterion {criterion_id}",
                        )
                    )
                covered.update(row_ids & criteria_ids)
                location = row.get("Test Location", "") or row.get("Location", "")
                if location:
                    path_part = location.strip("`").partition("::")[0]
                    if path_part and not (root / path_part).exists():
                        findings.append(
                            Finding(
                                path_part,
                                f"missing test file for Test Coverage row {index}",
                            )
                        )
                else:
                    findings.append(
                        Finding(rel, f"Test Coverage row {index} missing Test Location")
                    )
            for criterion_id in sorted(criteria_ids - covered):
                findings.append(
                    Finding(
                        rel,
                        f"acceptance criterion {criterion_id} is not mapped to any test",
                    )
                )
    return findings
