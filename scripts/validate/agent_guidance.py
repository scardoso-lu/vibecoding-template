from __future__ import annotations

import difflib
import re
import tomllib
from pathlib import Path

from scripts.validate.common import Finding, iter_text_files, line_number, read_text

STALE_TERMS: dict[str, str] = {
    "e2e-explorer": "standalone E2E role was merged into QA",
    "E2E_BUGS_FOUND": "QA now returns BLOCKED with Playwright output",
    "e2e/report.md": "use Playwright runner output instead of a prose report",
    "Spec File": "use Test Location for one story test, not one spec file",
    "one Playwright spec": "use one Playwright test(...) per small user story",
    "story specs": "use story tests",
    "ÃƒÆ’": "mojibake or mis-decoded UTF-8 text",
    "ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬": "mojibake or mis-decoded UTF-8 text",
    "ÃƒÂ¢Ã¢â€šÂ¬": "mojibake or mis-decoded UTF-8 text",
}

def normalize_runtime_text(text: str) -> str:
    replacements = {
        "claude": "runtime",
        "codex": "runtime",
        ".claude": ".runtime",
        ".codex": ".runtime",
        "claude.ai/code": "runtime",
    }
    normalized = text.lower()
    for source, target in replacements.items():
        normalized = normalized.replace(source, target)
    normalized = re.sub(r"\s+", " ", normalized)
    return normalized.strip()


def comparable_guidance_text(path: Path) -> str:
    text = read_text(path)
    if path.suffix == ".toml":
        try:
            data = tomllib.loads(text)
        except tomllib.TOMLDecodeError:
            return text
        if isinstance(data.get("developer_instructions"), str):
            return data["developer_instructions"]
        return text
    if text.startswith("---\n"):
        parts = text.split("---", 2)
        if len(parts) == 3:
            return parts[2]
    return text


def similarity(left: str, right: str) -> float:
    return difflib.SequenceMatcher(None, normalize_runtime_text(left), normalize_runtime_text(right)).ratio()


def validate_agent_guidance(root: Path) -> list[Finding]:
    findings: list[Finding] = []
    scan_paths = [
        "AGENTS.md",
        "CLAUDE.md",
        ".claude/agents",
        ".codex/agents",
        ".claude/templates",
        ".codex/templates",
        ".claude/hooks",
        ".codex/hooks",
    ]
    for path in iter_text_files(root, scan_paths):
        text = read_text(path)
        rel = path.relative_to(root).as_posix()
        for term, hint in STALE_TERMS.items():
            for match in re.finditer(re.escape(term), text):
                findings.append(Finding(rel, f"stale workflow term {term!r}: {hint}", line_number(text, match.start())))

    if (root / "AGENTS.md").exists() and (root / "CLAUDE.md").exists():
        score = similarity(read_text(root / "AGENTS.md"), read_text(root / "CLAUDE.md"))
        if score < 0.90:
            findings.append(Finding("AGENTS.md", f"AGENTS.md and CLAUDE.md similarity is {score:.2%}; expected at least 90%"))

    mirror_pairs = [
        (".claude/agents/backend-developer.md", ".codex/agents/backend-developer.toml"),
        (".claude/agents/frontend-developer.md", ".codex/agents/frontend-developer.toml"),
        (".claude/agents/orchestrator.md", ".codex/agents/orchestrator.toml"),
        (".claude/agents/qa.md", ".codex/agents/qa.toml"),
        (".claude/guideline-routing.md", ".codex/guideline-routing.md"),
        (".claude/templates/template-routing.md", ".codex/templates/template-routing.md"),
        (".claude/templates/template-minimal.md", ".codex/templates/template-minimal.md"),
        (".claude/hooks/README.md", ".codex/hooks/README.md"),
    ]
    for left, right in mirror_pairs:
        left_path = root / left
        right_path = root / right
        if left_path.exists() != right_path.exists():
            missing = left if not left_path.exists() else right
            findings.append(Finding(missing, "missing mirrored Claude/Codex artifact"))
            continue
        if not left_path.exists():
            continue
        score = similarity(comparable_guidance_text(left_path), comparable_guidance_text(right_path))
        if score < 0.65:
            findings.append(Finding(left, f"mirrored artifact similarity with {right} is {score:.2%}; review drift"))

    for rel in [
        ".claude/agents/orchestrator.md",
        ".codex/agents/orchestrator.toml",
        ".claude/agents/qa.md",
        ".codex/agents/qa.toml",
        ".claude/templates/categories/e2e.md",
        ".codex/templates/categories/e2e.md",
    ]:
        if not (root / rel).exists():
            findings.append(Finding(rel, "missing mirrored workflow artifact"))

    for left, right in [
        ("AGENTS.md", "CLAUDE.md"),
        (".claude/templates/categories/e2e.md", ".codex/templates/categories/e2e.md"),
        (".claude/templates/categories/qa.md", ".codex/templates/categories/qa.md"),
    ]:
        if (root / left).exists() and (root / right).exists():
            ltext = read_text(root / left)
            rtext = read_text(root / right)
            if "E2E Test Stories" in ltext and "E2E Test Stories" not in rtext:
                findings.append(Finding(right, f"missing E2E Test Stories language mirrored from {left}"))
            if "E2E Test Stories" in rtext and "E2E Test Stories" not in ltext:
                findings.append(Finding(left, f"missing E2E Test Stories language mirrored from {right}"))

    return findings

