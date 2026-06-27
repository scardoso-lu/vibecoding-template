# Full Feature Template Index

This file is intentionally small. Do not put category-specific template bodies here.

In Plan Mode, read `.codex/templates/template-routing.md` first, then load only the category templates required by the current slice.

Normal non-minimal feature memory still produces only:

```text
.codex/feature-memory/<slice>/
  slice.md
  rules.md
  e2e/report.md    # only when written by e2e-explorer
```

The category templates provide sections to compose into `slice.md` and `rules.md`; they are not separate output files.
