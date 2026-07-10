# Base Slice Template

Use for every non-minimal feature. Write one `slice.md` per business feature under
`memory/feature/<feature-slice>/`, and link the sibling features and global rule files it needs in
`## Dependencies`.

```md
# <feature>

## Status
- State: active | NEEDS-INPUT | BLOCKED | STAGED | E2E CLEAN | E2E BUGS FOUND | QA APPROVED | QA BLOCKED
- Current owner: product-owner | software-architect | business-challenger | technical-challenger | backend-developer | frontend-developer | qa-checker | qa-challenger
- Last updated:

`STAGED` = deliberately postponed because a dependency can't be tested in the current environment
(e.g. needs a live external system unavailable here). See `## Staging` below.

## Request
<Original user request or precise summary of this business feature.>

## Slice Boundary
- User outcome:
- In scope:
- Out of scope:

## Dependencies
- PRD: memory/PRD/<purpose>/prd.md
- ADR: memory/ADR/<purpose>/adr.md
- Depends on: memory/feature/<other-feature>, ... | none
- Rules: <slug>, <slug>, ... | none   # guideline slugs defined in the global memory/rules.md

Each field is a bare, comma-separated list of refs (wrapping onto indented
continuation lines is fine). Do not append explanatory parentheticals to a ref on
these lines (e.g. `adr.md (ADR-002 ...)`, `none (because ...)`) — put that context in
`## Request`, an ADR row, or `## Provenance` instead, since these lines are parsed by
the deterministic memory validator.

## Do Not Touch
- Files/directories:
- Behaviors:
- Data/contracts:

## Implementation Plan
| Step | Agent | Work | Reads | Do Not Touch | Stop Condition |
|---|---|---|---|---|---|

## Acceptance Criteria
- [ ] AC-001: <observable behavior>
- [ ] AC-002: <observable behavior>

## Test Coverage
Status legend: `done` (file exists and passes) | `in-progress` (being built) | `not-started`
(deliberately postponed - see `## Staging`). Missing Status = treated as started/enforced, so
never omit it for real gaps - only use `not-started` for genuinely deferred work.

| Criteria | Test Type | Test Location | Status |
|---|---|---|---|
| AC-001 | backend | `backend/test/<test_file>.py` | done |
| AC-002 | frontend-unit | `frontend/src/<feature>/<test_file>.test.tsx` | not-started |

## Staging
Only when any row above is `not-started`/`deferred`: name what's blocking it (usually an untestable
dependency - see CLAUDE.md rule 6) and when to revisit (a named prerequisite reaching QA, or the
next MVP checkpoint). Omit this section entirely when nothing is staged.

## Verification
- Run: <command that verifies the covered criteria> | covers: AC-001, AC-002
- Run: none [skip-verify: <reason>] | covers: AC-003

Machine-parsed contract, enforced by `python scripts/validate/cli.py verification`. One
`- Run:` row per verification command; the `covers:` union must span every AC-### above.
Each non-skip command must name the test file(s) its covered criteria map to in
`## Test Coverage`/`## E2E Test Stories` (full path, a path suffix, or the filename -
e.g. `test/test_<feature>.py`, `<feature>.spec.ts`), so a vacuous command cannot satisfy
the row. The deterministic gate
(`python scripts/validate/cli.py gate --root . --slice memory/feature/<feature-slice>/slice.md`)
executes every non-skip row and records it in `qa-evidence.json`; QA cannot pass while a
declared command is missing from that evidence, exited non-zero, or the evidence is stale
(its `code_state` digest no longer matches the app code). `[skip-verify: <reason>]` is
the only escape - explicit and grep-able, for criteria with no runnable surface yet
(docs-only, or staged per CLAUDE.md rule 6).

## Provenance
| Decision | Slug |
|---|---|
```
