# QA Sections

Include this section in every non-minimal `slice.md`.

```md
## QA Handoff
- Review focus:
- Blocking risks:
- Playwright story tests required: yes | no
- Focused Playwright command:
```

When `Playwright story tests required: yes`, the `Focused Playwright command:` value must
be non-empty and must match one of the slice's `## Verification` `- Run:` rows - the gate
runner executes the Run rows, and the verification validator blocks a focused command
that no Run row would actually execute.
