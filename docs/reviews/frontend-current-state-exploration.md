# Frontend Current State Exploration

**Date:** 2026-08-07
**Workstream:** Frontend (Antigravity AI)

### 1. Executive summary
The ChronoArb frontend workstream is currently at a **NOT STARTED** baseline. There are zero frontend application files, directories, or packages present in the repository. The backend is operational through Phase 2. The immediate next step is to lay the frontend foundation (Next.js and Flutter shells) in isolation without depending on real backend data, as described in Phase F1 of the frontend-backend workstream plan.

### 2. Current frontend stack
Based on `docs/architecture/frontend-design.md`, the planned stack is:
- **Web App:** Next.js 16 (App Router), React 19, TypeScript, Tailwind CSS 4
- **Mobile App:** Flutter, Riverpod, go_router, dio, freezed
- **State Management:** TanStack Query (Web), Riverpod (Mobile)
- **API Client:** Generated from OpenAPI using `openapi-typescript` and `openapi-generator`
- **Testing:** Vitest, Playwright, Axe (Web); flutter_test, integration_test (Mobile)

### 3. Repository structure
Currently, the following directories are **absent** from the repository and need to be created:
- `apps/web/`
- `apps/mobile/`
- `packages/design-tokens/`
- `packages/api-client-ts/`
- `packages/api-client-dart/`

### 4. Existing frontend functionality
**None.** No functionality is currently implemented. 

### 5. Missing frontend functionality
**Everything.** This includes application shells, authentication screens, opportunity feeds, watchlists, alert rules, settings, and administration dashboards.

### 6. Product-flow status matrix
| Flow | Status |
|------|--------|
| Authentication (Login/Onboarding) | NOT IMPLEMENTED (Planned) |
| Dashboard/Application Shell | NOT IMPLEMENTED (Planned) |
| Opportunity Feed | NOT IMPLEMENTED (Planned) |
| Opportunity Detail/Evidence | NOT IMPLEMENTED (Planned) |
| Watchlists | NOT IMPLEMENTED (Planned) |
| Alert Rules | NOT IMPLEMENTED (Planned) |
| Feedback Actions | NOT IMPLEMENTED (Planned) |
| Trade Outcomes | NOT IMPLEMENTED (Planned) |
| Settings (Org, Integrations, Billing) | NOT IMPLEMENTED (Planned) |
| Subscriptions/Billing | NOT IMPLEMENTED (Planned) |

### 7. Existing design system
**Not started.** `packages/design-tokens/` does not exist. The planned design system involves shared design tokens for colors, typography, spacing, shadows, and responsive breakpoints, which will translate to Tailwind config (Web) and ThemeData (Flutter). No CSS framework has been initialized yet.

### 8. API/backend dependency matrix
| Frontend Area | Dependency Status |
|---------------|-------------------|
| F1: Foundation | C. Frontend-only implementation |
| F2: Design System | C. Frontend-only implementation |
| F3: App Shell | C. Frontend-only implementation |
| F4: Auth Screens | D. Must wait for backend work (Cognito User Pool config needed) |
| F5: Opportunity Feed | B. Approved API contract + mock data (Initially) |
| F6: Detail Page | B. Approved API contract + mock data (Initially) |
| F7: Watchlists | B. Approved API contract + mock data |
| F8: Alert Rules | B. Approved API contract + mock data |
| F9: Activity Feed | B. Approved API contract + mock data |
| F10: Settings | B. Approved API contract + mock data |

### 9. Authentication/frontend security status
**Not implemented.** The planned model uses AWS Cognito (OIDC), with React Context and Riverpod managing auth state in Web and Mobile, respectively. Access tokens will be passed as Bearer JWTs, and secure storage (Keychain/Keystore) will be used in mobile. The auth contract is pending agreement between workstreams.

### 10. Testing and tooling status
**Not implemented.** No testing frameworks or UI development tools (like Storybook) have been initialized for the frontend. The `turbo.json` and `package.json` exist but frontend pipeline steps have no code to act upon.

### 11. Build/runtime verification
No commands were successfully run for the frontend because it does not exist.
- `pnpm install`: Works for existing backend packages, but no frontend `package.json` exists.
- `pnpm dev` / `flutter run`: Could not be executed.
- Typecheck, lint, test, build: Not executed due to missing source files.

### 12. Accessibility baseline
**Not implemented.** Expected target is WCAG 2.2 AA. The foundation phase will need to establish semantic HTML, keyboard support, and screen-reader testability patterns.

### 13. Responsive-design baseline
**Not implemented.** Expected to be mobile-first using Tailwind breakpoints for Web and responsive layout widgets for Flutter. Specific viewport matrices are a pending unresolved planning decision and should be addressed during Phase F2.

### 14. Technical debt and known issues
- There is no technical debt in the frontend codebase since it doesn't exist.
- Known issue: The viewport matrix for responsive design is not explicitly documented.

### 15. Frontend/backend coordination requirements
- **Authentication:** Need to agree on the OIDC contract, JWT format, and token refresh flow before implementing Phase F4.
- **API Contracts:** Must define and agree on the `opportunity` endpoints before transitioning Phase F5 from mocks to real data.
- **Shared Workspace:** Any additions to `pnpm-workspace.yaml`, `package.json`, or `turbo.json` must be done carefully to not break the backend's CI/CD.

### 16. Recommended first frontend phase
**Phase F1: Frontend Foundation**
Initialize the minimal Next.js app shell with a placeholder page, the minimal Flutter app, and the `design-tokens` and `api-client-ts` packages. This requires zero backend dependencies.

### 17. Explicit non-goals
- Do not implement real API calls.
- Do not implement real authentication flows.
- Do not introduce UI frameworks beyond the approved Next.js/React/Tailwind and Flutter stacks.
- Do not implement business logic or models.

### 18. Files likely involved in the first phase
- `apps/web/app/layout.tsx`, `apps/web/app/page.tsx`
- `apps/web/next.config.ts`, `apps/web/tailwind.config.ts`
- `apps/web/package.json`
- `apps/mobile/lib/main.dart`, `apps/mobile/pubspec.yaml`
- `packages/design-tokens/tokens/colors.ts`, `packages/design-tokens/package.json`
- `packages/api-client-ts/src/index.ts`, `packages/api-client-ts/package.json`
- `pnpm-workspace.yaml` (to add the new workspaces)

### 19. Risks and unresolved decisions
- **Unresolved Decision:** The specific viewport matrix for responsive design needs to be defined.
- **Risk:** Implementing mocked UI before the API contract is strictly finalized could lead to rework.
- **Risk:** Authentication implementation is blocked pending backend AWS Cognito configuration.
