# <feature-slice-name>

## Status
- State: active | QA APPROVED | QA BLOCKED | superseded
- QA verdict date:
- Approved by:

## Request
<Original user request or precise summary.>

## Do Not Touch
- Files/directories:
- Behaviors:
- Data/contracts:

## Acceptance Criteria
- [ ] <observable behavior>

## Verification
- Run: none [skip-verify: <why no runnable check applies, e.g. docs-only>]

If the change does have a runnable check, name it instead:
`- Run: <command>`. The skip token is the only exemption and must carry a reason.

## QA Handoff
- Review focus:
- Blocking risks:

> No validator list: `validate-tools` and other deterministic checks run as hooks, not as a QA
> step. QA makes the judgment call only.
