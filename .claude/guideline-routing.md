# Guideline Routing

Use this file only from orchestrator Plan Mode when feature memory lacks guideline slug context. Do not pass this file to backend, frontend, tester, or QA agents.

Fetch targeted MCP guideline details when a rule is unclear. Do not copy full guideline text into feature memory; summarize only the slice-specific rule.

## Backend Slug Map

| Task | Required slugs |
|---|---|
| Any new use case | `backend/02-domain-layer`, `backend/03-application-layer` |
| New endpoint / route | `backend/05-presentation-layer`, `backend/08-security` |
| Database read/write | `backend/04-infrastructure-layer`, `backend/28-database-session`, `backend/14-database-design` |
| State change that must be audited | `backend/19-audit-on-write` |
| Auth / login / session | `backend/08-security`, `backend/13-owasp-top10` |
| RBAC / permissions | `backend/26-rbac-permissions`, `backend/13-owasp-top10` |
| Async task / email / webhook | `backend/11-async-patterns`, `backend/22-idempotency` |
| Config / env / feature flags | `backend/24-configuration-layers` |
| Reference data / dropdowns | `backend/25-reference-data` |
| Pagination / list endpoint | `backend/21-api-pagination` |
| Migration | `backend/29-alembic-migrations`, `backend/23-safe-migrations` |
| Error handling | `backend/20-error-handling` |
| Tests | `backend/09-testing` |
| Logging / observability | `backend/18-observability-logging` |
| New feature | `backend/27-feature-discipline` |
| Bug fix / targeted edit | `backend/16-rework-clean`, `backend/10-tech-debt` |
| Service / adapter / design | `backend/15-design-patterns`, `backend/06-solid-principles` |
| Extracting abstraction | `backend/07-dry-kiss-yagni` |
| Tech debt / refactor | `backend/10-tech-debt` |
| AI-generated code review | `backend/12-vibecoding-traps` |
| Project setup / Docker / uv | `backend/17-project-setup` |
| New dependency | `architecture/01-technology-selection` |

## Frontend Slug Map

| Task | Required slugs |
|---|---|
| Any new page or route | `frontend/02-server-vs-client`, `frontend/03-data-fetching`, `frontend/14-loading-error-empty-states` |
| Form with validation | `frontend/04-forms-validation`, `frontend/16-server-actions` |
| Auth UI / login / session | `frontend/05-authentication`, `frontend/16-server-actions` |
| RBAC / hide UI by role | `frontend/19-rbac-permissions` |
| Data list / search / filter | `frontend/03-data-fetching`, `frontend/14-loading-error-empty-states` |
| File upload UI | `frontend/04-forms-validation`, `frontend/16-server-actions` |
| Server Action mutation | `frontend/16-server-actions` |
| Accessibility / responsive | `frontend/15-accessibility` |
| Performance / slow page | `frontend/18-performance` |
| Component tests | `frontend/17-component-testing` |
| E2E tests | `frontend/13-e2e-playwright` |
| Project structure / new feature scaffold | `frontend/01-project-structure`, `frontend/20-feature-discipline` |
| Refactor / cleanup | `frontend/11-rework-clean` |
| OWASP / XSS / security | `frontend/07-owasp-top10` |
| State management decision | `frontend/06-state-management` |
| Compound / multi-part UI | `frontend/09-design-patterns` |
| Component / hook design | `frontend/10-solid-dry-kiss` |
| Adding new npm package | `frontend/08-supply-chain`, `architecture/01-technology-selection` |
| Docker / Node.js setup | `frontend/12-project-setup` |
