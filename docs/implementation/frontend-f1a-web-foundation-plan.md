# Frontend Phase F1A — Web Application Foundation Plan

**Document type:** Implementation Plan
**Date:** 2026-08-07
**Workstream:** Frontend (Antigravity AI)
**Status:** READY FOR F1A IMPLEMENTATION

## 1. Objective
Produce the implementation plan for the smallest production-quality Next.js web foundation that can support later ChronoArb frontend phases. This plan establishes a working frontend shell and development environment without prematurely building product features.

## 2. Application Creation
We will create the Next.js web application inside `apps/web/` using the approved versions from the architecture baseline:
- Next.js: `16.x`
- React: `19.x`
- TypeScript: `5.x`
- Tailwind CSS: `4.x`

**Dependency Version Discipline:**
During implementation, we will resolve and record the exact compatible package versions. We will not use arbitrary floating versions or silently upgrade to a new major version. We will adhere strictly to the `package.json` package manager and version policies already defined in the repository root.

**Runtime Prerequisite:**
Next.js 16 requires a minimum Node.js version. The root `package.json` specifies Node `>=22.0.0`. We must verify the runtime requirement by executing:
```bash
node --version
```
before dependency installation. We will not modify the root Node configuration unless explicitly required and coordinated with the backend developer.

## 3. Next.js Structure
The minimum initial App Router structure will be established with foundational files only:
- `apps/web/app/layout.tsx` (Root layout with HTML/Body structure)
- `apps/web/app/page.tsx` (Root placeholder page)
- `apps/web/app/globals.css` (Tailwind and global styling)
- `apps/web/next.config.ts` (Next.js configuration)
- `apps/web/tsconfig.json` (TypeScript configuration, extending root if applicable)
- `apps/web/package.json` (Web app dependencies and scripts)
- `apps/web/eslint.config.mjs` (Next.js flat ESLint configuration)
- `apps/web/postcss.config.mjs` (Tailwind v4 PostCSS configuration)

No feature routes or complex folder structures will be created yet.

## 4. Root Page Purpose
The `apps/web/app/page.tsx` will serve as a development-safe placeholder screen. 
- It will explicitly identify **ChronoArb** and indicate that the "Frontend Application Foundation is running".
- It will NOT contain fake dashboards, fake business metrics, or pretend that product functionality exists.

## 5. Styling Foundation
We will set up Tailwind CSS v4 according to the approved PostCSS architecture approach.
- We will configure `postcss.config.mjs`.
- In `apps/web/app/globals.css`, we will use the Tailwind v4 import approach:
  ```css
  @import "tailwindcss";
  ```
- We will NOT create a Tailwind v3-style `tailwind.config.ts` unless a verified ChronoArb requirement actually requires it.
- We will NOT introduce shadcn/ui, Material UI, Chakra, or any other CSS framework.
- We will NOT create the full ChronoArb design system (colors, elaborate typography, shadows) in this phase.
- We will establish foundational global visual styling in `globals.css` including:
  - Sensible document background and text rendering.
  - `box-sizing: border-box` defaults.
  - Universal focus visibility outline foundation for accessibility.
  - `prefers-reduced-motion` awareness.

## 6. Accessibility Foundation
The foundation will target the WCAG 2.2 AA direction by establishing:
- Semantic HTML tags (`<main>`, `<header>`, etc.) in the layout.
- Proper document language (`<html lang="en">`).
- Page title and basic metadata in `layout.tsx`.
- Keyboard navigation compatibility (visible focus states globally).
- Reduced-motion compatibility basics.
*(Note: Full accessibility compliance cannot be claimed from foundation work alone).*

## 7. Responsive Baseline
Since the permanent viewport matrix belongs to the design-system planning phase, we will use temporary generic verification widths for F1A to ensure the shell doesn't break:
- **Narrow mobile:** `320px` to `480px`
- **Common tablet:** `768px` to `1024px`
- **Common desktop:** `1280px`+

These are temporary verification widths only; no permanent layout breakpoints will be hardcoded beyond Tailwind's standard generic defaults.

## 8. Workspace Integration
We will review shared root files:
- `pnpm-workspace.yaml`: **UNCHANGED**. It already includes `apps/*`, which automatically picks up `apps/web`.
- `turbo.json`: **UNCHANGED**. It already defines `dev`, `build`, `lint`, and `typecheck` pipelines which perfectly map to our web app scripts.
- `package.json` (Root): **UNCHANGED**. The root scripts (`turbo run dev`, etc.) are already sufficient.
- `pnpm-lock.yaml`: **EXPECTED MODIFICATION**. The addition of `apps/web` updates the root lockfile securely with strictly the required frontend dependencies.

By keeping the primary workspace configuration files unchanged, we guarantee minimal impact on the active backend development. The `pnpm-lock.yaml` change is a standard, expected consequence of adding a new workspace package.

## 9. Development Scripts
The `apps/web/package.json` will implement the standard Next.js scripts that map to the turbo pipeline. Note that `next lint` has been removed in Next.js 16, so linting is executed directly via ESLint:
- `"dev": "next dev"`
- `"build": "next build"`
- `"start": "next start"`
- `"lint": "eslint ."`
- `"typecheck": "tsc --noEmit"`

**Linting Note:** `next build` must not be treated as proof that linting passed. Linting is an explicit separate verification step.

## 10. Testing Scope
Automated verification for F1A will strictly cover:
- TypeScript compilation (`pnpm run typecheck`).
- Linting (`pnpm run lint`).
- Production build success (`pnpm run build`).

**Deferred:** Vitest (unit testing) and Playwright (E2E) frameworks are explicitly deferred to a later dedicated frontend testing foundation phase to avoid bootstrapping a massive test stack for a single placeholder page.

## 11. Verification Plan
The implementation phase must verify the real rendered result using observable runtime evidence, not code inspection alone. We will verify:
1. Node runtime requirement (`node --version`)
2. Dependency installation (`pnpm install`)
3. `pnpm run typecheck`
4. `pnpm run lint`
5. `pnpm run build`
6. `pnpm run start` after production build
7. Real browser rendering (application starts successfully and root page loads)
8. Browser console errors (must contain no unexplained errors)
9. Hydration errors (must contain no hydration errors)
10. Narrow viewport overflow (no horizontal overflow)
11. Tablet rendering
12. Desktop rendering
13. Keyboard navigation/focus behavior

We will not claim visual or accessibility compliance based solely on compilation.

## 12. Security Baseline
We will ensure that:
- No secrets are bundled client-side.
- No access token storage is introduced.
- No localStorage authentication design is introduced.
- No backend credentials are added.
- Environment variables (if any) follow strict Next.js public (`NEXT_PUBLIC_`) and private semantics. Authentication remains entirely out of scope.

## 13. Dependency Discipline

| Dependency | Purpose | Approved / Provided By |
|------------|---------|-----------------------|
| `next` (v16.x) | Core application framework | Architecturally approved |
| `react`, `react-dom` (v19.x) | UI library | Architecturally approved |
| `tailwindcss` (v4.x) | Styling framework | Architecturally approved |
| `@tailwindcss/postcss` | Tailwind v4 PostCSS plugin | Provided by Tailwind ecosystem |
| `postcss` | CSS processor for Tailwind | Provided by Tailwind ecosystem |
| `typescript` (v5.x) | Static typing | Architecturally approved |
| `@types/react`, `@types/react-dom`, `@types/node` | Type definitions | Standard TypeScript necessity |
| `eslint` (v9.x) | Core linting engine | Architecturally approved |
| `eslint-config-next` | Next.js linting configuration | Standard Next.js tooling |

No convenience libraries (e.g., date formatting, state management, complex animation libraries) or unapproved linting tools (e.g., Biome) will be added.

## 14. Expected Files (Manifest)

**CREATE:**
- `apps/web/package.json`
- `apps/web/tsconfig.json`
- `apps/web/next.config.ts`
- `apps/web/eslint.config.mjs`
- `apps/web/postcss.config.mjs`
- `apps/web/app/layout.tsx`
- `apps/web/app/page.tsx`
- `apps/web/app/globals.css`

**MODIFY:**
- None.

**UNCHANGED (Shared Root Files):**
- `pnpm-workspace.yaml`
- `package.json`
- `turbo.json`
- `tsconfig.base.json`

**MODIFIED (Shared Root Files):**
- `pnpm-lock.yaml`

## 15. Acceptance Criteria
1. `apps/web` directory exists with Next.js skeleton.
2. Next.js application boots successfully without crashing.
3. Root page renders identifying "ChronoArb" and "Frontend Application Foundation".
4. TypeScript compilation (`typecheck`) passes.
5. Linting (`lint`) passes.
6. Production build (`build`) passes.
7. Browser console contains no unexplained errors and no hydration errors.
8. Basic narrow, tablet, and desktop rendering works without horizontal overflow.
9. **No backend code is modified.**
10. **No real API calls exist.**
11. **No authentication implementation exists.**
12. **No product features are prematurely implemented.**

## 16. Non-Goals
This phase explicitly **DOES NOT** include:
- Mobile application (Flutter).
- Design-token package (`packages/design-tokens`).
- Generated API clients.
- Backend modifications.
- Authentication implementation.
- Real API calls.
- Opportunity UI.
- Watchlists, alerts, settings, or subscriptions.
- Speculative component libraries.
- Root workspace restructuring.
- Test frameworks not required for F1A (Vitest, Playwright).
- Extra UI libraries.

## 17. Risks
- **Next.js 16 / Tailwind 4 compatibility:** Being modern/upcoming versions, the specific config syntax (e.g. postcss setup) must be exact. We will use their standard documented approaches.
- **pnpm workspace impact:** Minimized by avoiding root config changes, but we must ensure `apps/web` cleanly resolves `@types`.
- **Turbo impact:** Handled seamlessly as `turbo.json` already defines the required tasks.
- **Root config impact on backend developer:** Zero, as we are leaving root configs unchanged.
- **Version drift:** Acknowledged. We are strictly adhering to the mandated versions.
- **Premature architecture choices:** Prevented by keeping the root page as a pure placeholder and deferring state-management/testing tools to later phases.

## 18. Rollback
If F1A needs to be reverted, it can be done safely by:
1. Deleting the `apps/web` directory:
```bash
rm -rf apps/web
```
2. Restoring the lockfile state consistently via Git:
```bash
git checkout HEAD -- pnpm-lock.yaml
```
or re-running `pnpm install` after removing the directory to clean up the workspace lockfile.
