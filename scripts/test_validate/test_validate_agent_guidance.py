from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts.validate.agent_guidance import validate_agent_guidance


def test_detects_stale_agent_guidance_terms(tmp_path: Path) -> None:
    (tmp_path / "AGENTS.md").write_text("Use e2e-explorer and e2e/report.md\n", encoding="utf-8")
    (tmp_path / "CLAUDE.md").write_text("Use e2e-explorer and e2e/report.md\n", encoding="utf-8")
    agent_dir = tmp_path / ".claude" / "agents"
    agent_dir.mkdir(parents=True)
    (agent_dir / "qa.md").write_text("Use Spec File and story specs\n", encoding="utf-8")

    findings = validate_agent_guidance(tmp_path)

    messages = "\n".join(f.message for f in findings)
    assert "e2e-explorer" in messages
    assert "e2e/report.md" in messages
    assert "Spec File" in messages
    assert "story specs" in messages


def test_clean_guidance_has_no_stale_term_findings(tmp_path: Path) -> None:
    for rel in [
        "AGENTS.md",
        "CLAUDE.md",
        ".claude/agents/orchestrator.md",
        ".codex/agents/orchestrator.toml",
        ".claude/agents/qa.md",
        ".codex/agents/qa.toml",
        ".claude/templates/categories/e2e.md",
        ".codex/templates/categories/e2e.md",
        ".claude/templates/categories/qa.md",
        ".codex/templates/categories/qa.md",
    ]:
        path = tmp_path / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("E2E Test Stories\nTest Location\nPlaywright story tests\n", encoding="utf-8")

    assert validate_agent_guidance(tmp_path) == []


def test_detects_root_guidance_similarity_drift(tmp_path: Path) -> None:
    (tmp_path / "AGENTS.md").write_text("A short Codex rule set\n", encoding="utf-8")
    (tmp_path / "CLAUDE.md").write_text("Completely different Claude text " * 40, encoding="utf-8")

    findings = validate_agent_guidance(tmp_path)

    assert any("similarity" in finding.message for finding in findings)


def test_detects_mojibake_in_guidance(tmp_path: Path) -> None:
    (tmp_path / "AGENTS.md").write_text("broken ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â text\n", encoding="utf-8")
    (tmp_path / "CLAUDE.md").write_text("broken ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â text\n", encoding="utf-8")

    findings = validate_agent_guidance(tmp_path)

    assert any("mojibake" in finding.message for finding in findings)



