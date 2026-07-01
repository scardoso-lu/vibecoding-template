# Code-First Playwright QA Sections

Include these sections in `slice.md` only for user-facing slices. QA generates or heals
deterministic Playwright story tests. E2E coverage is tracked in `feature-memory/<slice>/e2e-coverage.json`;
do not create or route a separate prose E2E report artifact.

```md
## E2E Test Stories
| Story ID | User Story | Criteria | Test Location | Seed/Setup | Assertions | Slugs |
|---|---|---|---|---|---|---|
| e2e-001 | As a <user>, I want <capability>, so <outcome>. | AC-001 | `frontend/e2e/<feature>.spec.ts::<test name>` | <fixture/API seed> | <observable assertions> | `<slug>` |

## Playwright Setup
- Launch backend:
- Launch frontend:
- Seed data / credentials:
- Focused command:
- CLI generation/debug procedure: `.codex/skills/playwright-cli/references/spec-driven-testing.md`
```

Also write `feature-memory/<slice>/e2e-coverage.json`:

```json
{
  "schema_version": 1,
  "source": "initial user prompt",
  "user_stories": [
    {"id": "US-001", "prompt_text": "<prompt user story>", "covered_by": ["e2e-001"]}
  ],
  "tests": [
    {"id": "e2e-001", "location": "frontend/e2e/<feature>.spec.ts::<test name>", "covers": ["US-001"]}
  ]
}
```

## Worked Example

| Story ID | User Story | Criteria | Test Location | Seed/Setup | Assertions | Slugs |
|---|---|---|---|---|---|---|
| e2e-001 | As a client, I want to buy informatics products, so that I can find and purchase the item I need. | AC-001 | `frontend/e2e/product-search.spec.ts::filters informatics products and shows priced grid` | seed catalog with an "Informatics" category and priced products | product grid renders filtered results with visible pricing | `<slug>` |

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

```json
{
  "schema_version": 1,
  "source": "initial user prompt",
  "user_stories": [
    {"id": "US-001", "prompt_text": "As a client, I want to buy informatics products.", "covered_by": ["e2e-001"]}
  ],
  "tests": [
    {"id": "e2e-001", "location": "frontend/e2e/product-search.spec.ts::filters informatics products and shows priced grid", "covers": ["US-001"]}
  ]
}
```
