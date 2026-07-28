# Frontend Architecture

This document defines the long-term frontend architecture for AIOS.

## Locked Technical Stack

- Vite + React + TypeScript
- Refine Core
- React Router
- TanStack Query
- Ant Design
- Ant Design Pro Components, used only when needed
- ECharts
- Controlled reuse of existing Vibe-Trading components

## Single Frontend Project

AIOS uses one frontend project only:

```text
frontend/
```

Do not create a second frontend project.

## Target Source Layout

```text
frontend/src/
├── app/
├── infrastructure/
├── features/
├── shared/
├── reused/
└── styles/
```

Responsibilities:

- `app`: entry point, providers, routing, layout, and global error boundaries.
- `infrastructure`: API client, Refine Data Provider, error normalization, SSE,
  and other external adapters.
- `features`: AIOS business modules such as `watchlist`, `research`,
  `evidence`, `execution`, `settlement`, `learning`, and `system`.
- `shared`: generic components, utilities, and types without AIOS business
  meaning.
- `reused`: reviewed external or original-project generic components.

## Dependency Direction

Allowed direction:

```text
app -> features -> infrastructure -> shared
```

Forbidden directions:

```text
shared -> features
infrastructure -> features
reused -> features
```

## API Request Flow

All API requests must follow this path:

```text
Page
-> feature hook / feature api
-> Refine Data Provider or infrastructure API
-> infrastructure/api/client
-> AIOS Backend
```

Pages must not hard-code API URLs and must not call `fetch` directly.

The API base URL must be read from:

```text
VITE_API_BASE_URL
```

## UI Rules

- Ant Design is the only primary UI component system.
- Do not introduce Material UI, Chakra UI, Mantine, or shadcn/ui.
- Do not copy Ant Design Pro in full.
- ECharts remains a normal charting library.
- Do not build a professional K-line terminal in the current phase.

## Vibe-Trading Reuse Rules

- Do not copy the full Vibe-Trading frontend.
- Only reviewed generic capabilities may be reused, such as Markdown, JSON
  Viewer, ECharts, Run Status, SSE, Loading, Error, and Toast components.
- Reused code must not depend on Vibe-Trading business routes, business models,
  or original APIs.
- Every reused item must record its source, license, and modification history.

## Backend Business Boundary

The frontend must not recalculate or generate:

- Evidence analysis
- Skill reasoning
- Hypothesis
- Discussion
- Decision
- Trade Plan
- Simulated Execution
- Settlement
- Evaluation
- Review
- Learning Proposal
- Skill weights
- Return settlement

The frontend is responsible only for display, issuing backend-supported
commands, and pure UI formatting.

## Research Routes

Phase 2 adds the read-only Research Run explorer:

```text
/research        Research Runs list
/research/new    Existing ResearchWorkbench manual run page
/research/:runId Research Run aggregate detail through Trade Plan
```

The route modules are page-level lazy loaded, including `/watchlist`,
`/research`, `/research/new`, and `/research/:runId`.

## Research Data Flow

Research list data uses the existing Refine resource/data-provider path:

```text
ResearchRunsPage
-> Refine dataProvider resource research-runs
-> infrastructure/api/client
-> GET /api/v1/research/runs
```

Research detail data uses one centralized feature query hook because the backend
returns an aggregate document:

```text
ResearchRunDetailPage
-> features/research/hooks/useResearchRunDetail
-> features/research/api/researchRunApi.detail
-> infrastructure/api/client
-> GET /api/v1/research/runs/{run_id}/detail
```

The detail response contains only persisted backend data:

```text
run
watchlist_item
session
evidence
skill_reports
hypotheses
discussion
decision
trade_plan
```

Missing nodes are returned as empty arrays or `null`. The frontend does not
generate lifecycle results, infer Evidence references from text, or create
default `no_trade` decisions.

## Research UI Structure

Research feature code lives under:

```text
frontend/src/features/research/
├── api/
├── hooks/
├── pages/
├── types/
└── ResearchWorkbench.tsx
```

Shared display helpers remain generic in `frontend/src/shared/researchDisplay.tsx`.
Research-specific types stay in `features/research/types` and infrastructure API
types stay in `infrastructure/api/research.ts`.

The Research Run detail page is split into these sections:

- Research Run overview
- Evidence
- Skill Reports
- Hypothesis
- Discussion, separated into blind report and review/revision phases
- Decision
- Trade Plan

`ResearchWorkbench` remains the real manual research submission UI at
`/research/new`. When the backend returns a real `run.run_id`, the page routes to
`/research/:runId`; it does not guess the latest run from a symbol.

Watchlist manual runs call the existing watchlist run endpoint. On success, the
Watchlist page reads the real backend `run.run_id` and routes to the Research Run
detail page.

## Dependency Audit

`npm audit` currently reports seven high severity findings:

| Package | Severity | Dependency kind | Runtime scope | Chain | Compatible fix | Phase 2 handling |
| -- | -- | -- | -- | -- | -- | -- |
| `react-router` | high | transitive via `react-router-dom` | production | `react-router-dom -> react-router` | No non-force compatible patch reported by npm audit; suggested fix force-installs `react-router-dom@7.11.0` | Deferred to avoid forced downgrade/breaking router change in this phase |
| `react-router-dom` | high | direct | production | direct dependency on vulnerable `react-router` | No non-force compatible patch reported by npm audit | Deferred with `react-router` item |
| `brace-expansion` | high | transitive | dev | `eslint -> minimatch -> brace-expansion` and ESLint config packages | No compatible non-force fix reported; suggested fix force-installs `eslint@10.8.0` | Deferred as dev-tool-only transitive issue |
| `minimatch` | high | transitive | dev | ESLint and ESLint config packages | No compatible non-force fix reported | Deferred with `brace-expansion` |
| `@eslint/config-array` | high | transitive | dev | `eslint -> @eslint/config-array -> minimatch` | No compatible non-force fix reported | Deferred with `brace-expansion` |
| `@eslint/eslintrc` | high | transitive | dev | `eslint -> @eslint/eslintrc -> minimatch` | No compatible non-force fix reported | Deferred with `brace-expansion` |
| `eslint` | high | direct dev tool | dev | direct dev dependency | Suggested fix is force upgrade to prerelease/breaking path | Deferred to avoid architecture churn |

`npm audit --omit=dev` reports two high severity production findings, both in
the React Router chain. No `npm audit fix --force` or forced major/downgrade was
run.

## Bundle Status

Vite build completes. After page-level lazy loading, the emitted chunks include:

```text
ResearchRunsPage-*.js        ~4.40 kB
ResearchNewPage-*.js        ~29.78 kB
WatchlistPage-*.js          ~30.43 kB
ResearchRunDetailPage-*.js  ~62.74 kB
Table-*.js                 ~347.85 kB
index-*.js                 ~796.16 kB
```

The chunk-size warning remains for the shared `index-*.js` chunk. Phase 2 did
not apply aggressive `manualChunks` splitting or change the UI/build stack.
