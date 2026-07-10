# Code-First Playwright QA Sections

Include these sections in `slice.md` only for user-facing slices. QA generates or heals
deterministic Playwright story tests. E2E coverage is tracked in `memory/feature/<slice>/e2e-coverage.json`;
do not create or route a separate prose E2E report artifact.

The example below is the only pattern to follow. Keep the table shape, keep the `// Story:`
header comment, and number every action as a sequential `// N)` step comment starting at 1.
`validate_playwright_stories` enforces the `// Story:` comment and rejects a referenced spec
file that is missing numbered step comments or has non-sequential step numbers.

Status legend: `done` (file exists and passes) | `in-progress` (being built) | `not-started`
(deliberately postponed - see `## Staging` in the base slice). Missing Status = treated as
started/enforced.

```md
## E2E Test Stories
| Story ID | User Story | Criteria | Test Location | Seed/Setup | Assertions | Slugs | Status |
|---|---|---|---|---|---|---|---|
| e2e-001 | As a client, I want to buy informatics products, so that I can find and purchase the item I need. | AC-001 | `frontend/e2e/product-search.spec.ts::filters informatics products and shows priced grid` | seed catalog with an "Informatics" category and priced products | product grid renders filtered results with visible pricing | `<slug>` | done |

## Playwright Setup
- Launch backend:
- Launch frontend:
- Seed data / credentials:
- Focused command:
- CLI generation/debug procedure: `.claude/skills/playwright-cli/references/spec-driven-testing.md`
```

The focused command must also appear as a `## Verification` `- Run:` row (and as the QA
Handoff `Focused Playwright command:`), covering the story's AC-### ids - the gate runner
executes Run rows into `qa-evidence.json`, and the verification validator blocks a
focused command the gate never ran.

```ts
// Story: e2e-001 covers US-001
test("filters informatics products and shows priced grid", async ({ page }) => {
  await page.goto("/");                                              // 1) open home page
  await page.getByRole("searchbox", { name: /search/i }).click();    // 2) client clicks search
  await page.getByRole("link", { name: "Informatics" }).click();     // 3) filter by informatics
  await page.getByRole("searchbox", { name: /search/i }).fill("keyboard"); // 4) type product name
  await page.getByRole("searchbox", { name: /search/i }).press("Enter");  // 5) press enter
  await expect(page.getByTestId("product-grid")).toBeVisible();      // 6) wait for products to load
  await expect(page.getByTestId("product-price").first()).toBeVisible(); // 7) view product grid with pricing
});
```

This exact spec was run against a live demo page with a real Chromium browser and passed
(`npx playwright test`, and separately via the `--debug=cli` / `playwright-cli attach` / `resume`
flow). On Windows, macOS, or a plain local Linux box, `npx playwright install` is all you need.
Only if the browser fails to launch inside a sandboxed Linux CI/cloud container with a
pre-installed browser at a fixed path, see the "Sandboxed/pre-installed browser environments" note
in `spec-driven-testing.md` section 1.1 for the `executablePath`/`--no-sandbox` fix.

Also write `memory/feature/<slice>/e2e-coverage.json`:

```json
{
  "schema_version": 1,
  "source": "initial user prompt",
  "user_stories": [
    {"id": "US-001", "prompt_text": "As a client, I want to buy informatics products.", "covered_by": ["e2e-001"]}
  ],
  "tests": [
    {"id": "e2e-001", "location": "frontend/e2e/product-search.spec.ts::filters informatics products and shows priced grid", "covers": ["US-001"], "status": "done"}
  ]
}
```

Each test entry's `status` is `done` | `in-progress` | `not-started`, matching its `## E2E Test
Stories` row - a `not-started` entry's `location` is a planned future path and is not checked
against the filesystem until its status changes.
