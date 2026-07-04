"""Recompute a business/technical-challenger verdict's acceptance score.

An LLM's self-reported "Acceptance: N%" line is a claim, not evidence - the same
"correctness beats compactness ... unsupported ... must be marked BLOCKED, not guessed"
rule in CLAUDE.md applies to a challenger grading its own persona panel. This module
recomputes accepted/total straight from the ### Persona Votes table and flags any
mismatch, missing vote, or malformed row so the SubagentStop gate can hard-block it.
"""

from __future__ import annotations

import re

from scripts.validate.models import Finding, parse_md_table

_ACCEPTANCE_RE = re.compile(
    r"Acceptance:\s*(\d+)%\s*\(\s*(\d+)\s*/\s*(\d+)\s*personas?\s*\)",
    re.IGNORECASE,
)


def validate_challenge_verdict(text: str) -> list[Finding]:
    label = "challenge-scoring"
    findings: list[Finding] = []

    rows = parse_md_table(text, "Persona Votes")
    if not rows:
        findings.append(Finding(label, "verdict is missing a ### Persona Votes table"))
        return findings

    accepted = 0
    total = 0
    for index, row in enumerate(rows, start=1):
        vote = (row.get("Vote") or "").strip().lower()
        persona = row.get("Persona") or f"row {index}"
        if vote not in ("accept", "reject"):
            findings.append(
                Finding(
                    label,
                    f"persona '{persona}' has a missing/malformed vote "
                    f"({vote or '<empty>'!r}); must be exactly 'accept' or 'reject'",
                )
            )
            continue
        total += 1
        if vote == "accept":
            accepted += 1

    if total == 0:
        findings.append(Finding(label, "Persona Votes table has no valid accept/reject rows"))
        return findings

    computed_pct = round(accepted * 100 / total)

    match = _ACCEPTANCE_RE.search(text)
    if not match:
        findings.append(
            Finding(
                label,
                "verdict is missing a '- Acceptance: <N>% (<accepted>/<total> personas)' line",
            )
        )
        return findings

    stated_pct, stated_accepted, stated_total = (int(match.group(i)) for i in (1, 2, 3))

    if stated_total != total:
        findings.append(
            Finding(
                label,
                f"stated total ({stated_total}) does not match the {total} persona "
                "rows found in the table",
            )
        )
    if stated_accepted != accepted:
        findings.append(
            Finding(
                label,
                f"stated accepted count ({stated_accepted}) does not match the "
                f"{accepted} 'accept' votes found in the table",
            )
        )
    if stated_pct != computed_pct:
        findings.append(
            Finding(
                label,
                f"stated acceptance ({stated_pct}%) does not match the recomputed "
                f"{computed_pct}% ({accepted}/{total})",
            )
        )

    return findings
