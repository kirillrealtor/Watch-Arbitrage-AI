# ChronoArb — Frontend Design

**Document type:** Web and mobile frontend architecture
**Source:** ChronoArb_MVP_SRS_v1.0 §8-9, AI-Agent Engineering Playbook §9-10
**Date:** 2026-08-03

---

## 1. Web Application (Next.js)

### 1.1 Architecture

```
apps/web/
├── app/                          # App Router pages
│   ├── layout.tsx                # Root layout (auth guard, providers)
│   ├── (auth)/
│   │   ├── login/page.tsx
│   │   └── onboarding/page.tsx
│   ├── (dashboard)/
│   │   ├── layout.tsx            # Dashboard shell (sidebar, org context)
│   │   ├── opportunities/
│   │   │   ├── page.tsx          # Feed
│   │   │   └── [id]/page.tsx     # Detail
│   │   ├── watches/
│   │   │   ├── page.tsx
│   │   │   └── [id]/page.tsx
│   │   ├── alerts/page.tsx
│   │   ├── activity/page.tsx
│   │   └── settings/
│   │       ├── organization/page.tsx
│   │       ├── integrations/page.tsx
│   │       └── billing/page.tsx
│   └── admin/
│       └── (admin routes)
├── components/
│   ├── ui/                       # Design system primitives
│   ├── features/                 # Feature-specific components
│   │   ├── opportunities/
│   │   ├── watches/
│   │   ├── alerts/
│   │   └── activity/
│   └── shared/                   # Cross-feature components
├── hooks/                        # Custom hooks (TanStack Query wrappers)
├── lib/
│   ├── api/                      # Generated API client + utilities
│   ├── auth/                     # Auth context, token management
│   └── utils/                    # Formatters, helpers
└── styles/

packages/
├── api-client-ts/                # Generated TypeScript client
└── design-tokens/                # CSS variables, Tailwind config, icons
```

### 1.2 Rendering Strategy

| Route | Strategy | Rationale |
|-------|----------|-----------|
| Login/onboarding | Server Components | Static shell, form interactions are client-side |
| Dashboard shell | Server Components | Stable layout, auth guard |
| Opportunity feed | Client Components + TanStack Query | Highly interactive, real-time updates |
| Opportunity detail | Client Components + TanStack Query | Cost waterfall, comps, real-time data |
| Settings | Client Components | Form-intensive |
| Admin | Client Components | Operational tools need live data |

Rule: Add `"use client"` only at the smallest interactive boundary. Server Components for stable shells and initial data.

### 1.3 State Management

| State Type | Solution |
|-----------|----------|
| Server state (opportunities, alerts, activity) | TanStack Query v5 with cursor pagination, background refresh, optimistic mutations |
| Auth state | React Context (token, user, organization, role) |
| UI state (filters, tabs, modals) | React `useState` / `useReducer` — no global store |
| Real-time updates | WebSocket integration that invalidates/patch TanStack Query cache |
| Forms | React Hook Form + Zod (schemas shared with API when practical) |
| Feature flags | Server-resolved; passed through route tree; never used for auth decisions |

### 1.4 Component Patterns

```
// Feature component = presentation only; data comes from hooks
// Feature hook = TanStack Query + business logic
// API module = generated client wrappers
// Domain functions = pure view-model transforms

// Example:
// components/features/opportunities/OpportunityFeed.tsx
//   → hooks/useOpportunityFeed.ts        (TanStack Query)
//     → lib/api/opportunities.ts          (generated client)
//       → /api/v1/opportunities            (FastAPI)
```

### 1.5 State Handling

Every async screen implements:

| State | Behavior |
|-------|----------|
| Loading | Skeleton/spinner with accessible label |
| Empty | Contextual message with next action |
| Error | Trace ID, retry guidance, safe error message |
| Stale | Background refresh indicator |
| Success | Data rendered |
| Permission denied | 403 with explanation |

### 1.6 Route Map

| Route | Purpose | Primary Components |
|-------|---------|-------------------|
| `/login` | OIDC entry and recovery | Hosted auth redirect, support links |
| `/onboarding` | Organization setup, references, assumptions, channels | Stepper with saved progress |
| `/opportunities` | Ranked live feed | Filter bar, sortable table/cards, saved views |
| `/opportunities/[id]` | Full deal analysis | Cost waterfall, comps, risks, history, actions |
| `/watches` | Supported catalog and watch lists | Search, reference cards, tracked status |
| `/watches/[id]` | Market detail | Valuation bands, comps, price history |
| `/alerts` | Alert rule management | Rule builder, channel preview, test notification |
| `/activity` | Decisions and outcomes | Team activity, purchased/dismissed |
| `/settings/organization` | Assumptions and tenant settings | Currency, timezone, fees, roles |
| `/settings/integrations` | Telegram and device connections | Link, revoke, delivery test |
| `/settings/billing` | Plan and invoices | Checkout/portal launch, entitlement status |
| `/admin/*` | Operations console | Sources, jobs, unmatched, duplicates, flags |

### 1.7 Accessibility

- Target WCAG 2.2 AA for customer and operations surfaces.
- Full keyboard support for feed, filters, dialogs, and actions.
- Visible focus indicators and logical tab order.
- Charts provide text summaries and tabular alternatives.
- Semantic HTML: `<table>`, `<nav>`, `<main>`, `<dialog>`, proper heading hierarchy.
- Axe automated checks in CI; manual keyboard/screen-reader review.

### 1.8 Performance

- Initial authenticated shell: p75 LCP < 2.5 seconds (broadband).
- Interaction latency < 200 ms for local controls.
- Route-level code splitting; admin code excluded from customer bundles.
- Image optimization only for permitted listing thumbnails (never proxy/retain beyond source rights).
- Virtualized tables only when row counts justify it.

---

## 2. Mobile Application (Flutter)

### 2.1 Architecture

```
apps/mobile/
├── lib/
│   ├── app/
│   │   ├── bootstrap.dart        # App initialization
│   │   ├── router.dart           # go_router configuration
│   │   └── theme.dart            # Design token integration
│   ├── core/
│   │   ├── api/                  # Dio client, auth interceptor, generated DTOs
│   │   ├── auth/                 # OIDC/PKCE session management
│   │   ├── storage/              # flutter_secure_storage + encrypted Drift
│   │   ├── notifications/        # FCM/APNs, local display, deep links
│   │   └── telemetry/            # Sentry, analytics (PII scrubbed)
│   ├── features/
│   │   ├── onboarding/
│   │   ├── opportunities/
│   │   │   ├── presentation/     # Widgets, screens
│   │   │   ├── application/      # Riverpod providers, controllers
│   │   │   ├── domain/           # Models, use cases
│   │   │   └── data/             # Repositories, DTOs
│   │   ├── watches/
│   │   ├── alerts/
│   │   ├── activity/
│   │   └── settings/
│   ├── shared/
│   │   ├── widgets/              # Design system widgets
│   │   ├── models/               # Shared domain models
│   │   └── formatters/           # Currency, date, reference formatters
│   └── main.dart
├── test/
└── integration_test/
```

### 2.2 Layer Responsibilities

```
Presentation (Widgets/Screens)     ← Renders state, dispatches user actions
    │ depends on
Application (Providers/Controllers) ← Orchestrates use cases, manages state
    │ depends on
Domain (Models/Use Cases)          ← Pure business logic, immutable models
    │ depends on
Data (Repositories/DTOs)           ← API calls, local cache, persistence
```

- Widgets NEVER call Dio, Drift, secure storage, or repositories directly.
- Transport DTOs are mapped to domain models before reaching UI.
- Riverpod providers expose dependencies and state.
- All state uses immutable models and exhaustive sealed states.

### 2.3 Package Baseline

| Concern | Package |
|---------|---------|
| State/DI | flutter_riverpod + riverpod_annotation |
| Routing | go_router (typed/declarative, auth redirects, deep links) |
| Networking | dio (interceptors, cancellation, timeouts, structured errors) |
| Serialization | freezed + json_serializable |
| Secure storage | flutter_secure_storage (Keychain/Keystore) |
| Offline cache | drift with encryption |
| Push | firebase_messaging + platform APNs |
| Local notifications | flutter_local_notifications |
| Deep links | app_links |
| Charts | fl_chart |
| Telemetry | sentry_flutter |

### 2.4 Navigation

- Bottom navigation: Opportunities, Watches, Activity, Settings.
- Alert rules accessible from Opportunities and Settings.
- Notification inbox from app bar.
- Deep link `/opportunities/:id` opens after auth + organization resolution.
- Small devices: cost breakdown uses progressive disclosure.

### 2.5 Push Notification Flow

1. Backend sends minimal payload: `{ notification_id, opportunity_id, title, summary, route }`.
2. App records open, fetches current opportunity (never trusts stale payload values).
3. Foreground: updates provider state, optional in-app banner.
4. Background/terminated: routes through pending-link coordinator after session restore.
5. Device token rotation synced to backend; logout revokes registration.

### 2.6 Offline Behavior

| Data | Offline Behavior |
|------|-----------------|
| Opportunity feed | Cache last successful pages; read-only |
| Opportunity detail | Cache recently viewed; never cache raw HTML |
| Feedback | Queue with client-generated idempotency key; sync in order |
| Trade outcomes | Local draft; submit after confirmation + connectivity |
| Settings/alert rules | Cached read; edits require connectivity |
| Authentication | No offline access after session expiry |

### 2.7 Accessibility

- VoiceOver/TalkBack semantics on all interactive elements.
- Dynamic text support throughout.
- Adequate touch targets (≥44pt).
- Semantic structure for screen readers.

---

## 3. Shared Design Tokens

```
packages/design-tokens/
├── tokens/
│   ├── colors.ts         # Color palette
│   ├── typography.ts     # Font scales
│   ├── spacing.ts        # Spacing scale
│   ├── shadows.ts        # Elevation shadows
│   └── breakpoints.ts    # Responsive breakpoints
├── icons/                # SVG/icon font
└── themes/
    ├── light.ts
    └── dark.ts
```

Shared between web (Tailwind config) and mobile (Flutter ThemeData). Single source of truth for visual identity.

---

## 4. Testing Strategy

### 4.1 Web

| Level | Tool | Scope |
|-------|------|-------|
| Unit/Component | Vitest + Testing Library | Hooks, utility functions, presentational components |
| E2E | Playwright | Chromium, WebKit, Firefox — critical user journeys |
| Accessibility | Axe | Automated in CI + manual keyboard/screen-reader review |
| Visual | Snapshot/golden tests | Opportunity, cost waterfall, alert builder, error states |

### 4.2 Mobile

| Level | Tool | Scope |
|-------|------|-------|
| Unit | flutter_test | Domain models, controllers, repositories |
| Widget | flutter_test + mocktail | Widget behavior, state rendering |
| Integration | integration_test | Critical user journeys on emulator/simulator |
| Golden | golden_toolkit | Visual regression for critical states |
