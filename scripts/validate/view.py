"""View layer: render check results as text or JSON."""

from __future__ import annotations

import json

from scripts.validate.models import Finding


def render(results: dict[str, list[Finding]], *, as_json: bool) -> tuple[str, bool]:
    """Return (rendered_text, has_findings)."""
    has_findings = any(results.values())
    if as_json:
        payload = {
            name: [finding.__dict__ for finding in findings]
            for name, findings in results.items()
        }
        return json.dumps(payload, indent=2), has_findings

    lines: list[str] = []
    for name, findings in results.items():
        if findings:
            lines.append(f"{name}: {len(findings)} finding(s)")
            lines.extend(f"  {finding.format()}" for finding in findings)
        else:
            lines.append(f"{name}: ok")
    return "\n".join(lines), has_findings
