from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from pathlib import Path
from typing import Any

from scripts.validate.models import Finding, parse_md_table, read_text
from scripts.validate.services.feature_memory import feature_memory_roots

BASELINE_AGENTS = {
    "orchestrator",
    "product-owner",
    "business-challenger",
    "software-architect",
    "technical-challenger",
    # qa-challenger always makes the final merge call, like the old combined "qa" role;
    # qa-checker is conditional (only when Playwright work is needed), like the developers,
    # so it is not baseline - it is added via the slice's Implementation Plan table instead.
    "qa-challenger",
}

AGENT_EVIDENCE_ROOT = "agent-evidence"
AGENT_EVIDENCE_FILE = "agent-evidence.json"


def canonical_hash(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _without_keys(value: Any, keys: set[str]) -> Any:
    if isinstance(value, dict):
        return {
            key: _without_keys(item, keys)
            for key, item in sorted(value.items())
            if key not in keys
        }
    if isinstance(value, list):
        return [_without_keys(item, keys) for item in value]
    return value


def apply_hashes(data: dict[str, Any]) -> dict[str, Any]:
    result = deepcopy(data)
    source_prompt = result.get("source_prompt")
    if isinstance(source_prompt, dict) and isinstance(source_prompt.get("text"), str):
        prompt_hash = hashlib.sha256(
            source_prompt["text"].encode("utf-8")
        ).hexdigest()
        source_prompt["sha256"] = prompt_hash
        result.setdefault("x_request_id", f"xreq-{prompt_hash[:16]}")
        source_prompt["x_request_id"] = result["x_request_id"]
    records = result.get("records")
    if isinstance(records, list):
        for record in records:
            if isinstance(record, dict):
                if result.get("x_request_id"):
                    record["x_request_id"] = result["x_request_id"]
                record["record_hash"] = canonical_hash(
                    _without_keys(record, {"record_hash"})
                )
    result["evidence_hash"] = canonical_hash(_without_keys(result, {"evidence_hash"}))
    return result


def write_hashed_evidence(path: Path) -> None:
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(data, dict):
        raise ValueError("agent evidence root must be an object")
    hashed = apply_hashes(data)
    path.write_text(json.dumps(hashed, indent=2) + "\n", encoding="utf-8")


def _expected_agents(slice_text: str, slice_md: Path) -> set[str]:
    agents = set(BASELINE_AGENTS)
    for row in parse_md_table(slice_text, "Implementation Plan"):
        agent = (row.get("Agent") or "").strip()
        if agent:
            agents.add(agent)
    # qa-challenger reviews qa-checker's evidence, so it can't have run yet if qa-checker
    # hasn't produced qa-evidence.json - expecting its record before QA has even started
    # would just be noise on a slice that legitimately hasn't reached QA yet.
    if not (slice_md.parent / "qa-evidence.json").exists():
        agents.discard("qa-challenger")
    return agents


def _evidence_files(root: Path) -> tuple[list[Path], list[Finding]]:
    findings: list[Finding] = []
    evidence_root = root / AGENT_EVIDENCE_ROOT
    if not evidence_root.exists():
        return [], findings
    prompt_dirs = sorted(
        path for path in evidence_root.iterdir() if path.is_dir() and path.name.startswith("prompt-")
    )
    numbers: list[int] = []
    for prompt_dir in prompt_dirs:
        suffix = prompt_dir.name.removeprefix("prompt-")
        if not suffix.isdigit() or int(suffix) < 1:
            findings.append(
                Finding(
                    prompt_dir.relative_to(root).as_posix(),
                    "agent evidence prompt directories must be named prompt-N with N >= 1",
                )
            )
            continue
        numbers.append(int(suffix))
    if numbers:
        expected = list(range(1, max(numbers) + 1))
        if sorted(numbers) != expected:
            findings.append(
                Finding(
                    AGENT_EVIDENCE_ROOT,
                    f"agent evidence prompt directories must increment by 1 without gaps, expected {expected}",
                )
            )
    return [path / AGENT_EVIDENCE_FILE for path in prompt_dirs], findings


def _data_slices(data: dict[str, Any]) -> set[str]:
    slices = data.get("slices")
    if isinstance(slices, list):
        return {str(item).replace("\\", "/") for item in slices}
    slice_path = data.get("slice")
    if isinstance(slice_path, str):
        return {slice_path.replace("\\", "/")}
    return set()


def validate_agent_evidence(root: Path) -> list[Finding]:
    findings: list[Finding] = []
    evidence_by_slice: dict[str, tuple[Path, dict[str, Any]]] = {}
    evidence_files, prompt_findings = _evidence_files(root)
    findings.extend(prompt_findings)
    for evidence_path in evidence_files:
        if not evidence_path.exists():
            findings.append(
                Finding(
                    evidence_path.relative_to(root).as_posix(),
                    "agent evidence prompt directory must contain agent-evidence.json",
                )
            )
            continue
        try:
            data = json.loads(read_text(evidence_path))
        except json.JSONDecodeError as exc:
            findings.append(
                Finding(
                    evidence_path.relative_to(root).as_posix(),
                    f"invalid agent evidence JSON: {exc}",
                )
            )
            continue
        if not isinstance(data, dict):
            findings.append(
                Finding(
                    evidence_path.relative_to(root).as_posix(),
                    "agent evidence root must be an object",
                )
            )
            continue
        for slice_ref in _data_slices(data):
            if slice_ref in evidence_by_slice:
                findings.append(
                    Finding(
                        evidence_path.relative_to(root).as_posix(),
                        f"duplicate agent evidence for slice {slice_ref}",
                    )
                )
            evidence_by_slice[slice_ref] = (evidence_path, data)

    for memory_root in feature_memory_roots(root):
        for slice_md in memory_root.rglob("slice.md"):
            if "history" in slice_md.relative_to(memory_root).parts:
                continue
            slice_text = read_text(slice_md)
            if "template-minimal" in slice_text or "Minimal Slice" in slice_text:
                continue
            slice_rel = slice_md.relative_to(root).as_posix()
            evidence_entry = evidence_by_slice.get(slice_rel)
            if evidence_entry is None:
                findings.append(
                    Finding(
                        f"{AGENT_EVIDENCE_ROOT}/prompt-N/{AGENT_EVIDENCE_FILE}",
                        f"full slice must be covered by prompt interpretation evidence: {slice_rel}",
                    )
                )
                continue
            evidence_path, data = evidence_entry
            if data.get("schema_version") != 1:
                findings.append(
                    Finding(
                        evidence_path.relative_to(root).as_posix(),
                        "agent evidence schema_version must be 1",
                    )
                )
            if slice_rel not in _data_slices(data):
                findings.append(
                    Finding(
                        evidence_path.relative_to(root).as_posix(),
                        "agent evidence slices[] must include its slice.md path",
                    )
                )
            x_request_id = data.get("x_request_id")
            if not isinstance(x_request_id, str) or not x_request_id:
                findings.append(
                    Finding(
                        evidence_path.relative_to(root).as_posix(),
                        "agent evidence must include x_request_id",
                    )
                )
            source_prompt = data.get("source_prompt")
            if not isinstance(source_prompt, dict) or not source_prompt.get("text"):
                findings.append(
                    Finding(
                        evidence_path.relative_to(root).as_posix(),
                        "agent evidence must include source_prompt.text",
                    )
                )
            elif hashlib.sha256(str(source_prompt.get("text")).encode("utf-8")).hexdigest() != source_prompt.get("sha256"):
                findings.append(
                    Finding(
                        evidence_path.relative_to(root).as_posix(),
                        "source_prompt.sha256 does not match source_prompt.text",
                    )
                )
            if isinstance(source_prompt, dict) and source_prompt.get("x_request_id") != x_request_id:
                findings.append(
                    Finding(
                        evidence_path.relative_to(root).as_posix(),
                        "source_prompt.x_request_id must match root x_request_id",
                    )
                )
            records = data.get("records")
            if not isinstance(records, list) or not records:
                findings.append(
                    Finding(
                        evidence_path.relative_to(root).as_posix(),
                        "agent evidence must include non-empty records[]",
                    )
                )
                continue
            seen_agents: set[str] = set()
            for index, record in enumerate(records, start=1):
                if not isinstance(record, dict):
                    findings.append(
                        Finding(
                            evidence_path.relative_to(root).as_posix(),
                            f"agent evidence record {index} must be an object",
                        )
                    )
                    continue
                agent = str(record.get("agent", ""))
                if agent:
                    seen_agents.add(agent)
                for key in [
                    "agent",
                    "phase",
                    "started_at",
                    "finished_at",
                    "prompt_interpretation",
                    "output_paths",
                    "record_hash",
                ]:
                    if not record.get(key):
                        findings.append(
                            Finding(
                                evidence_path.relative_to(root).as_posix(),
                                f"agent evidence record {index} missing {key}",
                            )
                        )
                if not isinstance(record.get("output_paths"), list):
                    findings.append(
                        Finding(
                            evidence_path.relative_to(root).as_posix(),
                            f"agent evidence record {index} output_paths must be a list",
                        )
                    )
                if record.get("x_request_id") != x_request_id:
                    findings.append(
                        Finding(
                            evidence_path.relative_to(root).as_posix(),
                            f"agent evidence record {index} x_request_id must match root x_request_id",
                        )
                    )
                expected_record_hash = canonical_hash(
                    _without_keys(record, {"record_hash"})
                )
                if record.get("record_hash") != expected_record_hash:
                    findings.append(
                        Finding(
                            evidence_path.relative_to(root).as_posix(),
                            f"agent evidence record {index} hash is stale or was not generated by scripts/validate/cli.py agent-evidence-hash",
                        )
                    )
            missing_agents = sorted(_expected_agents(slice_text, slice_md) - seen_agents)
            for agent in missing_agents:
                findings.append(
                    Finding(
                        evidence_path.relative_to(root).as_posix(),
                        f"missing agent evidence record for {agent}",
                    )
                )
            expected_evidence_hash = canonical_hash(
                _without_keys(data, {"evidence_hash"})
            )
            if data.get("evidence_hash") != expected_evidence_hash:
                findings.append(
                    Finding(
                        evidence_path.relative_to(root).as_posix(),
                        "agent evidence_hash is stale or was not generated by scripts/validate/cli.py agent-evidence-hash",
                    )
                )
    return findings
