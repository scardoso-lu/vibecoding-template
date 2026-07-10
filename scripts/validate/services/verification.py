"""Verification contract: a slice must name the commands that verify it.

Every `memory/feature/<slice>/slice.md` carries a `## Verification` section of
`- Run: <command> | covers: AC-###, ...` rows. The gate runner
(`scripts/validate/cli.py gate`) executes those commands and records them in
`qa-evidence.json`; this validator closes the loop deterministically:

- the section exists and every row parses (or is an explicit
  `- Run: none [skip-verify: <reason>]` escape - grep-able, never implicit);
- the rows' `covers:` union spans every AC-### the slice declares;
- a non-skip command actually names the mapped test files, so `Run: true`
  cannot satisfy the contract;
- when QA evidence exists, every declared command appears in `runs[]` with
  exit code 0 - declared-but-never-executed and executed-but-failed both block;
- the evidence's `code_state` digest still matches the working tree, so stale
  (pre-fix) evidence blocks until the gate is rerun.

The command *content* is judged by technical-challenger; this module only
enforces what can be checked without a model.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path

from scripts.validate.models import (
    Finding,
    acceptance_criteria_ids,
    app_code_state,
    has_heading,
    parse_md_table,
    read_text,
    row_is_started,
    section_text,
    split_ids,
)
from scripts.validate.services.feature_memory import feature_memory_roots

RUN_LINE_RE = re.compile(r"^\s*[-*]\s*Run:\s*(?P<value>.*)$")
COVERS_SPLIT_RE = re.compile(r"\|\s*covers:\s*(?P<ids>[^|]*)$", re.IGNORECASE)
SKIP_TOKEN_RE = re.compile(r"\[skip-verify:\s*(?P<reason>[^\]]*)\]")
SKIP_TOKEN_LOOSE_RE = re.compile(r"\[skip-verify\b[^\]]*\]|\[skip-verify\b")


@dataclass
class RunRow:
    command: str
    covers: set[str] = field(default_factory=set)
    skip: bool = False
    skip_reason: str = ""
    malformed: str = ""


def parse_verification_rows(text: str) -> list[RunRow]:
    """Parse `- Run:` rows out of a slice's ## Verification section."""
    rows: list[RunRow] = []
    for raw in section_text(text, "Verification").splitlines():
        match = RUN_LINE_RE.match(raw)
        if not match:
            continue
        value = match.group("value").strip()
        covers: set[str] = set()
        covers_match = COVERS_SPLIT_RE.search(value)
        if covers_match:
            covers = split_ids(covers_match.group("ids"))
            value = value[: covers_match.start()].strip()

        row = RunRow(command=value, covers=covers)
        skip_match = SKIP_TOKEN_RE.search(value)
        if skip_match:
            row.skip = True
            row.skip_reason = skip_match.group("reason").strip()
            remainder = SKIP_TOKEN_RE.sub("", value).strip().strip("`").lower()
            if not row.skip_reason:
                row.malformed = (
                    "skip-verify token must carry a reason: "
                    "`- Run: none [skip-verify: <reason>]`"
                )
            elif remainder not in ("", "none"):
                row.malformed = (
                    "a Run row is either a command or an explicit skip, not both; "
                    "use `- Run: none [skip-verify: <reason>]`"
                )
        elif SKIP_TOKEN_LOOSE_RE.search(value):
            row.skip = True
            row.malformed = (
                "malformed skip-verify token; use `- Run: none [skip-verify: <reason>]`"
            )
        elif not value or value.lower() == "none":
            row.malformed = (
                "Run row has no command; name a runnable command or use the explicit "
                "`- Run: none [skip-verify: <reason>]` escape"
            )
        row.command = value
        rows.append(row)
    return rows


def _started_locations_by_criterion(text: str) -> dict[str, set[str]]:
    """AC-### -> started Test Location paths from Test Coverage + E2E Test Stories."""
    locations: dict[str, set[str]] = {}
    for heading in ("Test Coverage", "E2E Test Stories"):
        for row in parse_md_table(text, heading):
            if not row_is_started(row):
                continue
            criteria_value = (
                row.get("Criteria")
                or row.get("Acceptance Criteria")
                or row.get("Criterion IDs")
                or ""
            )
            location = (row.get("Test Location") or row.get("Location") or "").strip(
                "`"
            )
            path_part = location.partition("::")[0].strip().replace("\\", "/")
            if not path_part:
                continue
            for criterion_id in split_ids(criteria_value):
                locations.setdefault(criterion_id, set()).add(path_part)
    return locations


def _command_names_location(command: str, location: str) -> bool:
    """True when the command names the test file - the full path, a multi-component
    suffix (`test/test_x.py` for `backend/test/test_x.py`), or the bare filename."""
    normalized = command.replace("\\", "/")
    parts = location.split("/")
    return any("/".join(parts[i:]) in normalized for i in range(len(parts)))


def _focused_playwright_command(text: str) -> str | None:
    """Value of the QA Handoff `Focused Playwright command:` line; None if absent."""
    match = re.search(r"Focused Playwright command:(?P<value>[^\n]*)", text)
    if not match:
        return None
    return match.group("value").strip().strip("`").strip()


def validate_verification(root: Path) -> list[Finding]:
    findings: list[Finding] = []
    for memory_root in feature_memory_roots(root):
        for slice_md in memory_root.rglob("slice.md"):
            if "history" in slice_md.relative_to(memory_root).parts:
                continue
            rel = slice_md.relative_to(root).as_posix()
            text = read_text(slice_md)

            if not has_heading(text, "Verification"):
                findings.append(
                    Finding(
                        rel,
                        "missing required section ## Verification: list the "
                        "`- Run: <command> | covers: AC-###` rows that verify this "
                        "slice, or an explicit `- Run: none [skip-verify: <reason>]`",
                    )
                )
                continue

            rows = parse_verification_rows(text)
            if not rows:
                findings.append(
                    Finding(
                        rel,
                        "## Verification must contain at least one `- Run:` row "
                        "(or the explicit `- Run: none [skip-verify: <reason>]` escape)",
                    )
                )
                continue

            for row in rows:
                if row.malformed:
                    findings.append(Finding(rel, row.malformed))

            criteria_ids, _ = acceptance_criteria_ids(text)
            if criteria_ids:
                covered: set[str] = set()
                for row in rows:
                    unknown = row.covers - criteria_ids
                    for criterion_id in sorted(unknown):
                        findings.append(
                            Finding(
                                rel,
                                "Verification Run row covers unknown acceptance "
                                f"criterion {criterion_id}",
                            )
                        )
                    covered.update(row.covers & criteria_ids)
                for criterion_id in sorted(criteria_ids - covered):
                    findings.append(
                        Finding(
                            rel,
                            f"acceptance criterion {criterion_id} is not covered by "
                            "any ## Verification Run row",
                        )
                    )

                locations = _started_locations_by_criterion(text)
                for row in rows:
                    if row.skip or row.malformed:
                        continue
                    mapped = sorted(
                        location
                        for criterion_id in row.covers
                        for location in locations.get(criterion_id, set())
                    )
                    if not mapped:
                        # Every covered AC's test rows are still not-started; there
                        # is no test file for the command to name yet (rule 6).
                        continue
                    if not any(
                        _command_names_location(row.command, location)
                        for location in mapped
                    ):
                        findings.append(
                            Finding(
                                rel,
                                f"Verification Run command {row.command!r} does not "
                                "name any test file mapped to its covered criteria "
                                f"(expected one of: {', '.join(mapped)})",
                            )
                        )

            if "Playwright story tests required: yes" in text:
                focused = _focused_playwright_command(text)
                if focused is not None and not focused:
                    findings.append(
                        Finding(
                            rel,
                            "QA Handoff `Focused Playwright command:` must not be "
                            "empty when Playwright story tests are required",
                        )
                    )
                elif focused and not any(
                    focused in row.command for row in rows if not row.skip
                ):
                    findings.append(
                        Finding(
                            rel,
                            "QA Handoff `Focused Playwright command:` must match one "
                            "of the ## Verification Run rows so the gate executes it",
                        )
                    )

            findings.extend(_cross_check_evidence(root, slice_md, rows))
    return findings


def _cross_check_evidence(
    root: Path, slice_md: Path, rows: list[RunRow]
) -> list[Finding]:
    """Declared Run commands must have been executed by the gate and passed, and
    the evidence must still describe the current app-code state."""
    findings: list[Finding] = []
    evidence_json = slice_md.parent / "qa-evidence.json"
    if not evidence_json.exists():
        # validate_qa_evidence owns whether the evidence file is required at all.
        return findings
    evidence_rel = evidence_json.relative_to(root).as_posix()
    try:
        data = json.loads(read_text(evidence_json))
    except json.JSONDecodeError:
        # validate_qa_evidence reports the parse error.
        return findings
    if not isinstance(data, dict):
        return findings

    runs = data.get("runs")
    runs_by_command: dict[str, list[dict[str, object]]] = {}
    if isinstance(runs, list):
        for run in runs:
            if isinstance(run, dict):
                command = str(run.get("command", "")).strip()
                runs_by_command.setdefault(command, []).append(run)

    for row in rows:
        if row.skip or row.malformed:
            continue
        matching = runs_by_command.get(row.command.strip(), [])
        if not matching:
            findings.append(
                Finding(
                    evidence_rel,
                    f"declared verification command {row.command!r} was never "
                    "executed by the gate; rerun `python scripts/validate/cli.py "
                    "gate --root . --slice "
                    f"{slice_md.relative_to(root).as_posix()}`",
                )
            )
            continue
        if all(run.get("exit_code") != 0 for run in matching):
            findings.append(
                Finding(
                    evidence_rel,
                    f"declared verification command {row.command!r} did not pass "
                    "(non-zero exit code in every recorded run)",
                )
            )

    current_state = app_code_state(root)
    if current_state is not None:
        recorded_state = data.get("code_state")
        if not isinstance(recorded_state, dict):
            findings.append(
                Finding(
                    evidence_rel,
                    "qa-evidence.json missing code_state; regenerate it with "
                    "`python scripts/validate/cli.py gate` so evidence is bound to "
                    "the app-code state it verified",
                )
            )
        elif recorded_state.get("app_digest") != current_state.get(
            "app_digest"
        ) or recorded_state.get("head") != current_state.get("head"):
            findings.append(
                Finding(
                    evidence_rel,
                    "qa-evidence.json is stale relative to the app code "
                    "(code_state digest mismatch); rerun the gate so QA judges "
                    "evidence for the code that will actually ship",
                )
            )
    return findings
