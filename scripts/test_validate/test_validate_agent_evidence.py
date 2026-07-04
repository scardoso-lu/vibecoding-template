from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts.validate.services.agent_evidence import (
    apply_hashes,
    validate_agent_evidence,
)


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


SLICE = """# Slice

## Status
- State: BLOCKED

## Implementation Plan
| Step | Agent | Work |
|---|---|---|
| 1 | product-owner | PRD |
| 2 | qa-challenger | Review |
"""


def evidence() -> dict:
    return {
        "schema_version": 1,
        "slices": ["memory/feature/example/slice.md"],
        "source_prompt": {
            "text": "Create an example feature.",
            "received_at": "2026-07-03T21:00:00Z",
        },
        "records": [
            {
                "agent": agent,
                "phase": agent,
                "started_at": "2026-07-03T21:00:00Z",
                "finished_at": "2026-07-03T21:00:01Z",
                "prompt_interpretation": f"{agent} interpreted the prompt.",
                "output_paths": ["memory/feature/example/slice.md"],
                "decisions": ["planning only"],
            }
            for agent in [
                "orchestrator",
                "product-owner",
                "business-challenger",
                "software-architect",
                "technical-challenger",
                "qa-challenger",
            ]
        ],
    }


def test_hashed_agent_evidence_passes(tmp_path: Path) -> None:
    write(tmp_path / "memory/feature/example/slice.md", SLICE)
    write(
        tmp_path / "agent-evidence/prompt-1/agent-evidence.json",
        json.dumps(apply_hashes(evidence()), indent=2),
    )

    assert validate_agent_evidence(tmp_path) == []


def test_missing_agent_evidence_is_reported(tmp_path: Path) -> None:
    write(tmp_path / "memory/feature/example/slice.md", SLICE)

    findings = validate_agent_evidence(tmp_path)

    assert any("prompt interpretation evidence" in finding.message for finding in findings)


def test_stale_agent_evidence_hash_is_reported(tmp_path: Path) -> None:
    write(tmp_path / "memory/feature/example/slice.md", SLICE)
    data = apply_hashes(evidence())
    data["records"][0]["prompt_interpretation"] = "mutated after hash"
    write(
        tmp_path / "agent-evidence/prompt-1/agent-evidence.json",
        json.dumps(data, indent=2),
    )

    findings = validate_agent_evidence(tmp_path)

    assert any("hash is stale" in finding.message for finding in findings)


def test_x_request_id_must_propagate_to_prompt_and_records(tmp_path: Path) -> None:
    write(tmp_path / "memory/feature/example/slice.md", SLICE)
    data = apply_hashes(evidence())
    data["records"][0]["x_request_id"] = "wrong"
    write(
        tmp_path / "agent-evidence/prompt-1/agent-evidence.json",
        json.dumps(data, indent=2),
    )

    findings = validate_agent_evidence(tmp_path)

    assert any("x_request_id must match" in finding.message for finding in findings)


def test_prompt_directories_must_increment_without_gaps(tmp_path: Path) -> None:
    write(tmp_path / "memory/feature/example/slice.md", SLICE)
    write(
        tmp_path / "agent-evidence/prompt-2/agent-evidence.json",
        json.dumps(apply_hashes(evidence()), indent=2),
    )

    findings = validate_agent_evidence(tmp_path)

    assert any("increment by 1 without gaps" in finding.message for finding in findings)
