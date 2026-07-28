# Frontend Architecture

This document defines the long-term frontend architecture for AIOS. The current
Milestone establishes rules and structure only; it does not start frontend page
development.

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
