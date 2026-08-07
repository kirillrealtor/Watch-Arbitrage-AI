# Frontend Phase F3 — Application Shell Plan

## Overview
This document outlines the implementation plan for Frontend Phase F3, establishing the static, responsive, and route-aware application shell for the ChronoArb web platform. F3 focuses entirely on layout architecture and navigation infrastructure without implementing real backend dependencies or product features.

## Status
READY FOR F3 IMPLEMENTATION

## Verified F3 Scope
- **APPROVED:** Authenticated-application visual shell structure (desktop and mobile).
- **APPROVED:** Route-aware active navigation using ChronoArb design tokens.
- **APPROVED:** Top application bar (mobile only) and page-header pattern.
- **APPROVED:** Navigation information architecture implementation via placeholders.
- **APPROVED:** Server/Client component boundary definitions.
- **EXCLUDED:** Real data, authentication, API calls, actual feature screens, notification functionality, active org-switcher functionality.

## Application Route Architecture
The application shell will be isolated within a Next.js Route Group to protect marketing/auth routes from inheriting the authenticated layout.

```
app/
├── (dashboard)/
│   ├── layout.tsx         # F3 Application Shell Layout
│   ├── opportunities/page.tsx  # Dev Placeholder
│   ├── watches/page.tsx        # Dev Placeholder
│   ├── alerts/page.tsx         # Dev Placeholder
│   ├── activity/page.tsx       # Dev Placeholder
│   └── settings/organization/page.tsx # Dev Placeholder
├── layout.tsx             # Root layout (F2 Providers)
└── page.tsx               # Root route (remains F2 preview until redirect is configured)
```

The root `/` route behavior will remain unchanged during F3.

## Navigation Information Architecture (IA)
Based on `docs/architecture/frontend-design.md`, the approved top-level dealer navigation is configured centrally in `apps/web/config/navigation.ts`:
1. **Opportunities** (`/opportunities`) — Icon: `RadarOutlined`
2. **Watches** (`/watches`) — Icon: `WatchOutlined`
3. **Alerts** (`/alerts`) — Icon: `NotificationsActiveOutlined`
4. **Activity** (`/activity`) — Icon: `HistoryOutlined`
5. **Settings** (`/settings/organization`) — Icon: `SettingsOutlined`

No admin areas or fake workflows will be built. 

## Active Route Matching
The navigation configuration will define exact prefix/section matching rules so that future detail pages (e.g., `/opportunities/[id]`) will correctly maintain the active selected state of the parent section. 

## Desktop Shell Strategy
- **Sidebar Width:** 256px (APPROVED FOR F3).
- **Left Navigation Rail (Sidebar):** Persistent `Drawer` (variant: permanent). Collapse behavior is deferred.
- **Desktop Top Bar:** NOT IMPLEMENTED IN F3. A global desktop top bar may be introduced in a later phase when real functionality (search, notifications, org-switcher) requires it.
- **Brand Identity:** Restrained ChronoArb text (Typography `h6`, bold, `text.primary`).
- **Main Content Pane:** Full available main width with consistent responsive gutters. Individual feature pages will control their own maximum width.
- **Scroll Ownership:** 
  - Outer shell: `height: 100dvh`, `overflow: hidden`. 
  - Main content: `min-width: 0`, `overflow-y: auto`. This creates one intentional application content scroll region without nested vertical scrollbars.

## Mobile Shell Strategy
- **Breakpoint:** Navigation transitions to mobile behavior below `lg` (1024px) (APPROVED FOR F3).
- **Navigation:** MUI `Drawer` (variant: temporary), triggered by an `IconButton` (MenuOutlined) in the Top Application Bar.
- **Top Application Bar:** Visible only on mobile/tablet `< lg` to host the hamburger menu and current route title. 
- **Drawer Behavior:** Standard MUI backdrop, escape dismissal, and focus management. Automatically closes on route change.

## Server/Client Boundary
To minimize client JS payload, the shell is split into structural (Server) and interactive (Client) components:
- **Server Components:** `(dashboard)/layout.tsx`, `AppShell.tsx`, `AppSidebar.tsx`, `PageHeader.tsx`.
- **Client Components:** `MobileNavigation.tsx` (manages drawer state and mobile AppBar), `NavLinks.tsx` (uses `usePathname()` to evaluate active route).

## Shell Component Architecture
```
apps/web/components/shell/
├── AppShell.tsx         # Server: Composes sidebar, top bar, and main content
├── AppSidebar.tsx       # Server: Desktop permanent drawer wrapping NavLinks
├── MobileNavigation.tsx # Client: State for temporary drawer, AppBar, and current route title
├── NavLinks.tsx         # Client: Renders ListItemButton and handles usePathname
└── PageHeader.tsx       # Server: Reusable pattern for page titles/actions
```

## Page-Header Strategy
`PageHeader.tsx` provides a consistent container:
- **Anatomy:** `Title` (H1), `Description` (optional subtitle), and `Actions` (ReactNode for future buttons). No breadcrumbs or fake actions.
- **Styling:** Standardized bottom margin and padding to establish page rhythm, aligning with content gutters.

## MUI Component Usage
MUI owns component visuals and interaction states.
- `Drawer`: For both persistent desktop sidebar and temporary mobile menu.
- `AppBar` / `Toolbar`: For the mobile top bar.
- `List` / `ListItemButton` / `ListItemIcon` / `ListItemText`: For navigation links.
- `IconButton`: For the mobile menu trigger.
- `Typography`: For branding and headers.
- `Box`: For structural grouping where MUI context is strictly required.

## Tailwind Usage
Tailwind owns macro-layout composition.
- `flex`, `grid`, `w-64`, `w-full`.
- `h-[100dvh]`, `overflow-hidden`, `overflow-y-auto` for scroll ownership.
- Responsive display (`hidden lg:flex`, `flex lg:hidden`).
- `px-4 sm:px-6 lg:px-8` for content gutters.
No Tailwind color/background/border utilities will restyle MUI navigation controls outside the theme.

## Breakpoint Strategy
- `< 1024px` (`lg`): Mobile shell (TopBar + Temporary Drawer).
- `>= 1024px` (`lg`): Desktop shell (Persistent Sidebar + TopBar hidden).
Verification will explicitly include the `1023px` and `1024px` boundary.

## Accessibility Strategy
- **Skip Link:** Accessible "Skip to main content" link (first focusable element, visually hidden until focused, targeting `id="main-content"`).
- **Landmarks:** Proper landmark roles (`<nav>`, `<main>`, `<header>`).
- **Active Route:** `aria-current="page"` applied to the active `ListItemButton`.
- **Selected Semantics:** Uses MUI's `selected` prop augmented with semantic background, text/icon treatment, and subtle font weight differences.

## Testing Recommendation
**APPROVED:** Introduce `@playwright/test` for web E2E testing.
Vitest/Testing Library is explicitly deferred for F3 as no standalone component/business logic justifies them yet.

### Playwright E2E Coverage Strategy
Files: `apps/web/playwright.config.ts`, `apps/web/tests/e2e/app-shell.spec.ts`.
Script: `"test:e2e": "playwright test"`.
Browsers: Chromium, Firefox, WebKit. No visual regression.
Coverage:
1. `/opportunities` loads inside shell.
2. All shell navigation destinations resolve successfully.
3. Clicking navigation changes route.
4. Active route receives current-page semantics.
5. Desktop persistent navigation exists at desktop width.
6. Mobile navigation trigger exists below the shell breakpoint.
7. Temporary Drawer opens.
8. Drawer navigation works.
9. Drawer closes after route change.
10. Escape closes the Drawer.
11. Skip link works.
12. No horizontal overflow at representative widths.

## Exact Proposed File Manifest

**CREATE:**
- `apps/web/app/(dashboard)/layout.tsx`
- `apps/web/app/(dashboard)/opportunities/page.tsx`
- `apps/web/app/(dashboard)/watches/page.tsx`
- `apps/web/app/(dashboard)/alerts/page.tsx`
- `apps/web/app/(dashboard)/activity/page.tsx`
- `apps/web/app/(dashboard)/settings/organization/page.tsx`
- `apps/web/components/shell/AppShell.tsx`
- `apps/web/components/shell/AppSidebar.tsx`
- `apps/web/components/shell/MobileNavigation.tsx`
- `apps/web/components/shell/NavLinks.tsx`
- `apps/web/components/shell/PageHeader.tsx`
- `apps/web/config/navigation.ts`
- `apps/web/playwright.config.ts`
- `apps/web/tests/e2e/app-shell.spec.ts`

**MODIFY:**
- `apps/web/package.json` (Add `@playwright/test` to devDependencies, add `"test:e2e"` script)
- `pnpm-lock.yaml` (Automatically via pnpm install)
- `apps/web/app/globals.css` (Only if required for skip link styling)

**UNCHANGED:**
- `apps/web/app/layout.tsx` (Root providers)
- `apps/web/theme/**`
- `packages/design-tokens/**`
- `root package.json`
- `pnpm-workspace.yaml`
- `turbo.json`
- `tsconfig.base.json`

## Acceptance Criteria
1. `(dashboard)` route-group shell exists.
2. Root F2 provider architecture remains intact.
3. Opportunities placeholder resolves.
4. Watches placeholder resolves.
5. Alerts placeholder resolves.
6. Activity placeholder resolves.
7. Settings/organization placeholder resolves.
8. No clickable shell navigation leads to a 404.
9. Desktop persistent sidebar works at >=1024px.
10. Mobile AppBar/Drawer works below 1024px.
11. 1023/1024 transition is verified.
12. Active route is visually indicated.
13. Active route exposes accessible current-page semantics.
14. Prefix/section matching behavior is correct.
15. Drawer opens by keyboard/click.
16. Escape closes temporary Drawer.
17. Drawer closes after navigation.
18. Focus management is correct.
19. Skip-to-main link works.
20. Main content has correct landmark/ID.
21. No accidental nested vertical scrollbar.
22. No horizontal overflow at supported widths.
23. Shell retains Server Components where possible.
24. Client boundary is limited to navigation interaction.
25. MUI owns component visuals.
26. Tailwind remains structural.
27. ChronoArb design tokens are reused.
28. No hard-coded shell palette values are introduced.
29. Playwright E2E passes.
30. Lint passes.
31. Typecheck passes.
32. Production build passes.
33. Production runtime is exercised.
34. No hydration errors.
35. Browser console is clean.
36. No API calls introduced.
37. No authentication implemented.
38. No backend files modified.
39. No fake product controls introduced.
40. No competing UI/icon library introduced.

## Phase F4 — Authentication Screens and Protected-Route Integration
F3 hands F4:
- `(dashboard)` shell boundary;
- responsive navigation;
- application content layout;
- page-header pattern;
- accessible shell;
- route-aware navigation.

F4 owns:
- login/onboarding UI within the approved `(auth)` route group;
- authentication/session integration;
- protected-route enforcement at the trusted/server boundary;
- auth redirects;
- client auth context only where useful for UI state.

## Dependencies Proposed
- `@playwright/test` (devDependency): To automate visual and navigation testing for responsive breakpoints. Note that browser installation commands (e.g., `pnpm exec playwright install`) will be required outside of standard dependency installation.

## Rollback Strategy
Bounded rollback is possible by reverting git commits. F3 rollback must account for:
- dashboard route-group files
- shell components
- navigation config
- Playwright configuration/tests
- `package.json` devDependency changes
- `pnpm-lock.yaml`
No destructive rollback commands will be used during implementation.
