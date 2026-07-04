# Session Handoff

- Date: 2026-07-04
- Branch: `claude/hook-compact-review-d0nnse`
- Task: review the compact/reinject hook, add a 90%-context-usage handoff hook, and wire the
  next-session pickup flow (ask the user before injecting; on yes, continue the missing items).
- How this file is used: `.claude/hooks/resume-handoff.sh` announces it at session start and asks
  the user whether to inject it. `.claude/hooks/context-usage-watch.sh` regenerates/updates it
  whenever a session crosses ~90% context usage.

## Completed

- Reviewed `.claude/hooks/reinject-context.sh` (SessionStart, matcher `compact`). Verdict: correct
  and registered properly; the `State:` grep matches the template/validator contract
  (`scripts/validate/services/feature_memory.py`). Weaknesses found: it only listed feature
  slices (no PRD/ADR references), used a fragile literal-newline `printf`, and had no link to any
  session handoff.
- Extended `.claude/hooks/reinject-context.sh` (+ `.codex/hooks/` mirror): after compaction it now
  re-injects active **PRDs** (`memory/PRD/*/prd.md`), **ADRs** (`memory/ADR/*/adr.md`), and
  **feature slices** (`memory/feature/*/slice.md`) with their `State:` lines, and points at
  `SESSION-HANDOFF.md` when one exists.
- Added `.claude/hooks/context-usage-watch.sh` (+ `.codex/hooks/` mirror): `PostToolUse` on all
  tools; tail-reads the transcript, sums the newest assistant `usage` record, and at
  `CONTEXT_HANDOFF_THRESHOLD_PCT` (default 90%) of `CONTEXT_WINDOW_TOKENS` (default 200000)
  injects `additionalContext` instructing the model to write this file (Completed / Missing /
  References / Next steps). Fires once per session via a temp-dir sentinel; fails open.
- Added `.claude/hooks/resume-handoff.sh` (+ `.codex/hooks/` mirror): `SessionStart` matcher
  `startup|resume`; when `SESSION-HANDOFF.md` exists it instructs the model to **ask the user**
  whether to inject before any other work, and only then implement the missing items.
- Registered both hooks in `.claude/settings.json` and `.codex/hooks.json` (registration + file-set
  parity is enforced by `scripts/validate/services/harness.py`).
- Updated `.claude/hooks/README.md` and `.codex/hooks/README.md` (table rows + "Closing the gap"
  section, count updated to seven).
- Wrote this handoff file (doubles as the first live artifact of the new workflow).

## Missing / Not Completed

- [ ] `EXPECTED_HOOKS` in `scripts/validate/services/hook_registration.py` does not yet require
      `context-usage-watch.sh` / `resume-handoff.sh`, so `doctor` would not fail if a fork removed
      their registration. Add them (and adjust `scripts/test_validate/test_validate_hook_registration.py`
      fixtures accordingly).
- [ ] No unit tests for the new hooks (e.g. a transcript fixture above/below the threshold for
      `context-usage-watch.sh`; presence/absence of `SESSION-HANDOFF.md` for `resume-handoff.sh`).
- [ ] The window size is a static default (200000). For 1M-context models set
      `CONTEXT_WINDOW_TOKENS` in the environment; auto-detecting from the transcript model id was
      not implemented.
- [ ] The watch fires once per session and never re-warns if the user keeps working past 90%
      without compacting; decide whether a re-warn (e.g. every +5%) is wanted.
- [ ] `CLAUDE.md` / `AGENTS.md` do not yet mention the handoff workflow in the Deterministic
      Enforcement section; add one line each if it should be a documented contract.
- [ ] End-to-end verification in a real long session (the 90% trigger and the compact reinjection
      were only verified with synthetic hook input, see `.claude/hooks/README.md` testing section).

## References

The template's memory is empty on this branch — no product work has produced artifacts yet.
When resuming, link the real artifacts here:

- PRD: none yet (`memory/PRD/<purpose>/prd.md`)
- ADR: none yet (`memory/ADR/<purpose>/adr.md`)
- Feature slices: none yet (`memory/feature/<feature>/slice.md`)
- Rules: none yet (`memory/rules.md`, one block per guideline slug)

The changes in this session are workflow infrastructure (hooks), which per CLAUDE.md routes as
docs/config work, not a product feature slice.

## Next steps

1. Ask the user which of the Missing items to tackle (validator coverage first is recommended:
   `EXPECTED_HOOKS` + tests keep the new hooks from silently unregistering).
2. Add `context-usage-watch.sh` and `resume-handoff.sh` to `EXPECTED_HOOKS` and extend
   `scripts/test_validate/test_validate_hook_registration.py`.
3. Add hook unit tests with a synthetic transcript fixture.
4. Decide on re-warn behaviour and document `CONTEXT_WINDOW_TOKENS` /
   `CONTEXT_HANDOFF_THRESHOLD_PCT` in `.env.example` or CLAUDE.md if made configurable per-project.
5. Update this file (or delete it) once the list is empty.
