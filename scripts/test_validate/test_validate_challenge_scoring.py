from __future__ import annotations

from scripts.validate.services.challenge_scoring import validate_challenge_verdict

GOOD_VERDICT_6 = """## Business Challenge Verdict

- Acceptance: 83% (5/6 personas)
- Decision: REVISE (< 90%)

### Persona Votes
| Persona | Vote |
|---|---|
| Problem Skeptic | accept |
| Journey Mapper | accept |
| MVP Minimalist | accept |
| Outcome Auditor | accept |
| Scope Hawk | reject |
| Risk Owner | accept |
"""

GOOD_VERDICT_8 = """## Technical Challenge Verdict

- Acceptance: 100% (8/8 personas)
- Decision: PASS (>= 90%)

### Persona Votes
| Persona | Vote |
|---|---|
| ADR Auditor | accept |
| Provenance Auditor | accept |
| Component Split Reviewer | accept |
| Contract Reviewer | accept |
| Coverage Skeptic | accept |
| Security & Data Risk | accept |
| Operations Reviewer | accept |
| Coding Practices Auditor | accept |
"""


def test_matching_score_has_no_findings() -> None:
    assert validate_challenge_verdict(GOOD_VERDICT_6) == []
    assert validate_challenge_verdict(GOOD_VERDICT_8) == []


def test_wrong_percentage_is_reported() -> None:
    bad = GOOD_VERDICT_6.replace("Acceptance: 83%", "Acceptance: 90%")
    findings = validate_challenge_verdict(bad)
    assert any("recomputed 83%" in f.message for f in findings)


def test_wrong_accepted_count_is_reported() -> None:
    bad = GOOD_VERDICT_6.replace("(5/6 personas)", "(6/6 personas)")
    findings = validate_challenge_verdict(bad)
    assert any("does not match the 5 'accept' votes" in f.message for f in findings)


def test_wrong_total_is_reported() -> None:
    bad = GOOD_VERDICT_6.replace("(5/6 personas)", "(5/7 personas)")
    findings = validate_challenge_verdict(bad)
    assert any("does not match the 6 persona rows" in f.message for f in findings)


def test_missing_table_is_reported() -> None:
    findings = validate_challenge_verdict("## Verdict\n- Acceptance: 100% (1/1 personas)\n")
    assert any("missing a ### Persona Votes table" in f.message for f in findings)


def test_missing_acceptance_line_is_reported() -> None:
    text = """## Verdict

### Persona Votes
| Persona | Vote |
|---|---|
| A | accept |
"""
    findings = validate_challenge_verdict(text)
    assert any("missing a '- Acceptance:" in f.message for f in findings)


def test_malformed_vote_is_reported() -> None:
    bad = GOOD_VERDICT_6.replace("| Scope Hawk | reject |", "| Scope Hawk | maybe |")
    findings = validate_challenge_verdict(bad)
    assert any("malformed vote" in f.message for f in findings)
