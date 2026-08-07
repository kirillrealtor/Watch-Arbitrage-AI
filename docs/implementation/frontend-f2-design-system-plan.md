# Frontend Phase F2 — Design System Foundation Plan

**Date:** 2026-08-08
**Workstream:** Frontend (Antigravity AI)

## Goal
Establish the shared ChronoArb design-system foundation (Phase F2) adopting **MUI Material** as the primary component system. This plan defines the visual primitives, UI infrastructure, and integration rules for MUI alongside Tailwind CSS 4, tailored for a premium, analytical B2B luxury-watch platform.

---

## 1. UI System Decision (Architecture Decision Record)

**Primary component system:** MUI Material
**Primary icon system:** MUI Icons (@mui/icons-material)
**Future data grid:** MUI X Data Grid Community (by default)
**Layout utility layer:** Tailwind CSS 4
**Brand/design source:** ChronoArb semantic design tokens

**Rule:** MUI owns components; Tailwind owns layout; ChronoArb tokens own visual identity.

**Rationale:**
- MUI provides stability, mature accessibility behavior, and easier debugging.
- Documented APIs, predictable TypeScript support, and faster product development for data-heavy components.
- Reduced maintenance burden compared to building custom interactive primitives from scratch.

**Tradeoffs:**
- Larger dependency footprint.
- Requires explicit management of MUI and Tailwind CSS precedence.
- Strict theme discipline is required to avoid the default "Material" consumer app appearance.
- Advanced MUI X Data Grid features may require paid licensing in the future.

---

## 2. Clear MUI vs Tailwind Responsibility
We will explicitly separate concerns to avoid creating two competing component systems.

**MUI owns:**
- Interactive components (Button, IconButton, Select, TextField, Autocomplete, Tabs, etc.)
- Component behavior and accessibility-heavy primitives
- Form controls and validation states
- Overlays (Menu, Tooltip, Popover, Dialog, Snackbar)
- Component-level visual states, variants, and theming

**Tailwind CSS 4 owns primarily:**
- Page layout, flex, and grid
- Responsive composition
- Width/height and container positioning
- Lightweight structural utilities (margin, padding for layout)

**ChronoArb Design Tokens own:**
- Colors, typography, spacing philosophy
- Radii, elevation, and semantic states
- Breakpoints and product visual identity

> [!WARNING]
> **Anti-Pattern Prevention:** Tailwind utilities must not be used to recreate MUI components (no custom Tailwind buttons, selects, or dialogs when MUI already provides them). Avoid parallel implementations of the same primitive.

---

## 3. Token Source of Truth & MUI Theme Mapping
To ensure a single source of truth and avoid duplicating raw values, the architecture will be structured as follows:

```text
packages/design-tokens/
  package.json
  tsconfig.json
  src/
    colors.ts
    typography.ts
    spacing.ts
    radii.ts
    shadows.ts
    breakpoints.ts
    index.ts
```
These export framework-neutral semantic ChronoArb token constants.

Then, the web application maps these tokens into the MUI theme:
```text
apps/web/theme/
  create-chronoarb-theme.ts
```

**MUI CSS Variables:**
The MUI theme will be configured to use MUI's CSS-variable theme functionality (e.g., `cssVariables: true`), producing stable CSS variables. A ChronoArb-specific CSS variable prefix may be configured to avoid global naming collisions (e.g. `--chronoarb-palette-primary-main`).
Tailwind will consume aliases/references to these resulting semantic CSS variables where practical, rather than independently redefining the visual system.

*Note: No elaborate token compiler or Flutter token generator will be introduced in F2.*

---

## 4. Next.js App Router & Server/Client Boundary
We will use MUI's official Next.js App Router integration package (e.g. `@mui/material-nextjs`).

**Integration Strategy:**
- Use `AppRouterCacheProvider` (or equivalent based on exact version docs) in `apps/web/app/layout.tsx` to handle SSR style injection and prevent hydration mismatches or emotion cache ordering bugs.
- **Server/Client Boundary:** Do not arbitrarily add `"use client"` to `layout.tsx` or `page.tsx`.
- Because the `ThemeProvider` requires client execution, it will be encapsulated in a narrowly scoped `ThemeRegistry` or `Providers` client component, which is then imported into the Server Component `layout.tsx`.

---

## 5. CSS Layer Strategy
To coexist cleanly with Tailwind CSS 4, we will explicitly define CSS cascade-layer ordering.

**Precedence Order:**
1. Tailwind base / normalize styles
2. ChronoArb global styles
3. MUI Component styles
4. Tailwind utility classes (highest precedence for structural overrides)

By ensuring Tailwind's utility layer has precedence over MUI's default styles, developers can reliably use Tailwind for margins, positioning, or layout wrapping without fighting specificity battles.

---

## 6. Theme Structure Details

### A. Palette
- **Semantic Roles:** `background.default`, `background.paper`, `text.primary`, `text.secondary`, `divider`, `primary`, `success`, `warning`, `error`, `info`.
- **Custom Roles:** Extensions for `opportunity.positive`, `opportunity.risk`.
- The visual language must be professional, analytical, restrained, and dense.

### B. Typography
- **Font Selection:** `Inter` (via `next/font/google` self-hosted, no extra dependency).
- **Scale:** H1: 24px, H2: 20px, H3: 18px, Body: 14px, Metadata: 12px.
- **Financial Values:** Explicitly support `font-variant-numeric: tabular-nums` in the MUI theme or through specific class assignments for financial data; do not assume the font automatically applies it.

### C. Spacing
- ChronoArb uses a compact **4px layout rhythm**.
- The MUI theme will configure its spacing multiplier to align with this grid.
- Intended control sizing is compact/default suitable for dense B2B dealer workflows.

### D. Radius / Shape
- **Restrained Radii:** 2px, 4px (default), 8px, and full (for pills).
- We will override MUI's default rounded-card styling if it is too bubbly.

### E. Elevation
- **Border-led Design:** Most information surfaces (cards, panels) will rely on borders with little to no shadow.
- Menus, popovers, and dialogs will use restrained elevation shadows.

### F. MUI Component Defaults
- Disable excessive elevation globally.
- Consistent focus-visible behavior (restrained rings).
- Inherit typography correctly.
- *Note: We will not heavily override every individual component in F2; F3 will introduce component-specific variants as needed.*

---

## 7. Status Semantics & Financials
Visual semantics combine text/label meaning and secondary color reinforcement.
- **Statuses:** `published`, `viewed`, `dismissed`, `purchased`, `contacted`, `pending`, `sent`, `failed`, `suppressed`, `active`, `inactive`.
- **Financials:** Right-aligned in tabular contexts, tabular numerals, explicit `+`/`-`.
- **Rule:** Color alone must not communicate critical status or meaning. Confidence is not inherently positive/negative. Currency formatting is deferred.

---

## 8. Responsive Architecture
We will use one synchronized breakpoint definition for both Tailwind and MUI. MUI's theme breakpoints will be configured to match Tailwind's structural breakpoints.

**Synchronized Layout Breakpoints:**
- `sm`: 640px
- `md`: 768px
- `lg`: 1024px
- `xl`: 1280px
- `2xl`: 1536px

**Browser Verification Widths:**
320px (compact), 390px (mobile), 640px (sm boundary), 768px (md/tablet), 1024px (lg/laptop), 1280px (xl/desktop), 1536px (2xl/wide).

---

## 9. MUI Icons Strategy
- **Standard Source:** `@mui/icons-material` is formally established as the primary icon system.
- **Visual Direction:** Outlined icons by default (e.g., `SearchOutlined`, `SettingsOutlined`) because they are lighter and fit dense analytical interfaces.
- **Performance:** Direct imports (e.g., `import SearchOutlined from '@mui/icons-material/SearchOutlined';`) will be used to ensure predictable bundling.
- **Accessibility:** Meaningful icons require `aria-label`; decorative icons must be hidden from assistive technology.

---

## 10. MUI X Data Grid
- **Formal Approval:** MUI X Data Grid Community is approved as the default first-choice grid for future data-heavy screens.
- **F2 Implementation:** It will **NOT** be installed in F2. It will be added when a real grid feature is built. Pro/Premium require explicit future approval due to licensing.

---

## 11. Dark Mode
- **Recommendation:** Light theme only for MVP.
- MUI theme architecture will be semantic and CSS-variable-based, making it inherently future-compatible with dark mode.
- We will NOT implement a dark theme, toggle, `ThemeMode` state, or `localStorage` preference in F2.

---

## 12. Accessibility & Contrast Verification
- **Target:** WCAG 2.2 AA.
- **Verification:** Actual semantic combinations used in the preview must be measured at development time (foreground, background, ratio, requirement, PASS/FAIL). No assumed contrast passes.
- **Motion:** No motion library will be added. Rely on MUI intrinsic transitions; respect `prefers-reduced-motion`.
- *Note: Using MUI does not automatically guarantee full product compliance; custom implementations must be validated.*

---

## 13. Design-System Development Preview
The `/` route (`apps/web/app/page.tsx`) will be a labeled **"ChronoArb Design System Foundation Development Preview"**.
It will validate the MUI architecture using a VERY SMALL set of MUI elements:
- Typography, Paper, Chip, Button, and one or two Icons (to verify correct package setup and sizing).
- Tailwind will be used exclusively for page-level composition (flex, gap, container) of this preview.
- **Goal:** Prove MUI + Tailwind coexist predictably, theme variables resolve, and SSR hydration succeeds.

---

## 14. Dependencies & Files
**Proposed Packages to verify for Next.js 16.3 / React 19.2 compatibility:**
- `@mui/material`
- `@mui/icons-material`
- `@emotion/react`
- `@emotion/styled`
- `@mui/material-nextjs`

*Note: No extra UI libraries (Lucide, Radix, shadcn/ui, Bootstrap) will be added. Tailwind CSS 4 is retained purely for structural layout.*

**Exact Proposed File Manifest:**
- `packages/design-tokens/package.json` & `tsconfig.json`
- `packages/design-tokens/src/colors.ts`, `typography.ts`, `spacing.ts`, `radii.ts`, `shadows.ts`, `breakpoints.ts`, `index.ts`
- `apps/web/theme/create-chronoarb-theme.ts`
- `apps/web/app/Providers.tsx` (narrowly scoped client provider wrapper)
- `apps/web/app/layout.tsx` (integrate Providers, fonts, SSR cache)
- `apps/web/app/page.tsx` (MUI preview)
- `apps/web/app/globals.css` (CSS layer definitions and Tailwind import)
- `apps/web/package.json` (new dependencies)

*Root workspace configs (`turbo.json`, `pnpm-workspace.yaml`, etc.) remain unchanged.*

---

## 15. Testing & Rollback
- **Verification:** `pnpm --filter @chronoarb/web run typecheck`, `lint`, and `build`.
- **Validation:** SSR/hydration success (no mismatched styles), MUI CSS variable generation, MUI + Tailwind coexistence, real browser preview, contrast measurements.
- **Rollback:** Reverting `apps/web` changes, deleting `packages/design-tokens`, and running `pnpm install` restores the lockfile seamlessly.

---

## 16. Acceptance Criteria
1. ChronoArb design-token package architecture defined.
2. MUI formally established as primary component system.
3. MUI Icons formally established as primary icon system.
4. MUI X Community approved for future grid use.
5. Tailwind role narrowed to layout/structural utilities.
6. MUI and Tailwind responsibilities documented.
7. MUI-compatible semantic palette defined.
8. MUI typography strategy defined.
9. spacing/radius/elevation strategy defined.
10. MUI CSS-variable strategy defined.
11. Tailwind semantic integration strategy defined.
12. MUI/Tailwind breakpoint synchronization defined.
13. Next.js App Router integration defined.
14. server/client boundary defined.
15. SSR/style insertion strategy defined.
16. accessibility/contrast verification defined.
17. dependency manifest defined.
18. exact file manifest defined.
19. no backend changes planned.
20. no product screens planned.
21. no competing icon/component library introduced.
22. F3 handoff clearly defined.

---

## 17. Architecture Non-goals
F2 does NOT include dashboard, real navigation, authentication, API integration, feed/detail screens, watchlists, billing, production data grid, Flutter implementation, or backend changes.

---

## 18. F3 Boundary
After F2, F3 should be able to build the ChronoArb Application Shell using the configured MUI theme, approved MUI component system, MUI Icons, Tailwind structural utilities, synchronized responsive breakpoints, and shared ChronoArb semantic tokens.
