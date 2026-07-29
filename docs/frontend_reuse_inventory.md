# Frontend Reuse Inventory

Record reviewed frontend component reuse here.

Phase 2 copied no external source files. It reused only npm dependencies and
current repository code, including the existing API client, Refine data provider,
Ant Design baseline, ResearchWorkbench, Watchlist page, and shared loading/error
display patterns.

| Component | Original Location | New Location | License | Reuse Method | Modifications | Status |
| -- | ---- | --- | --- | ---- | ---- | -- |
| API client and error normalization | `frontend/src/infrastructure/api/client.ts` | unchanged | repository code | direct reuse | none | reused |
| Refine data provider | `frontend/src/infrastructure/refine/dataProvider.ts` | unchanged | repository code | extended existing resource map | added `research-runs` collection path | reused |
| ResearchWorkbench | `frontend/src/features/research/ResearchWorkbench.tsx` | `/research/new` route | repository code | moved by routing, not rewritten | added optional success callback for real `run_id` navigation | reused |
| Watchlist manual run flow | `frontend/src/features/watchlist/WatchlistPage.tsx` | unchanged | repository code | direct reuse | routes to real Research Run detail after run success | reused |
| Ant Design components | npm package `antd` | direct imports | MIT | npm dependency reuse | no source copied | reused |
| External source files | none | none | n/a | none | n/a | not reused |

## Execution & Settlement Explorer

This milestone copied no external source files and introduced no new UI
framework. It reused the existing Vite/React application, React Router,
Refine data provider, API client, ApiError handling, Ant Design components,
TanStack Query, and shared Research display helpers.

| Component | Original Location | New Location | License | Reuse Method | Modifications | Status |
| -- | ---- | --- | --- | ---- | ---- | -- |
| API client and ApiError | `frontend/src/infrastructure/api/client.ts` | unchanged | repository code | direct reuse | none | reused |
| Refine data provider | `frontend/src/infrastructure/refine/dataProvider.ts` | unchanged | repository code | extended existing resource map | added `simulated-executions`, `settlements`, and `learnings` paths | reused |
| React Router app shell | `frontend/src/app/App.tsx` | unchanged | repository code | extended existing lazy route pattern | added explorer routes only | reused |
| Application navigation | `frontend/src/app/layout.tsx` | unchanged | repository code | extended existing Ant Design Menu | added Research, Executions, Settlements, Learning Proposals nav entries | reused |
| Loading, empty, error, status, time, percent display | `frontend/src/shared/researchDisplay.tsx` | unchanged | repository code | direct reuse | none | reused |
| Research Run detail layout | `frontend/src/features/research/pages/ResearchRunDetailPage.tsx` | unchanged | repository code | extended in place | added downstream explorer section after Trade Plan | reused |
| Ant Design components | npm package `antd` | direct imports | MIT | npm dependency reuse | no source copied | reused |
| Refine | npm package `@refinedev/core` | direct imports | MIT | npm dependency reuse | no source copied | reused |
| React Router | npm package `react-router-dom` | direct imports | MIT | npm dependency reuse | no source copied | reused |
| TanStack Query | npm package `@tanstack/react-query` | direct imports | MIT | npm dependency reuse | no source copied | reused |

## AIOS Results Home & Core Detail Completeness

This milestone copied no external source files and introduced no charting,
market-data, news, or professional行情 UI dependencies. It reused the existing
React Router lazy-route pattern, API client, ApiError handling, Ant Design,
TanStack Query, shared display helpers, and the backend-linked
ExecutionSettlementExplorer detail model.

| Component | Original Location | New Location | License | Reuse Method | Modifications | Status |
| -- | ---- | --- | --- | ---- | ---- | -- |
| API client and ApiError | `frontend/src/infrastructure/api/client.ts` | unchanged | repository code | direct reuse | added Dashboard feature API wrapper only | reused |
| React Router app shell | `frontend/src/app/App.tsx` | unchanged | repository code | extended existing lazy route pattern | added `/dashboard`; `/` redirects to `/dashboard` | reused |
| Application navigation | `frontend/src/app/layout.tsx` | unchanged | repository code | extended existing Ant Design Menu | ordered Dashboard, Research, Executions, Settlements, Learning Proposals | reused |
| Loading, empty, error, status, time, percent display | `frontend/src/shared/researchDisplay.tsx` | unchanged | repository code | direct reuse | none | reused |
| Explorer chain sections | `frontend/src/features/explorer/pages/common.tsx` | unchanged | repository code | expanded in place | added full Decision, Trade Plan, Execution, Settlement, Evaluation, Review, Learning fields | reused |
| Research Run detail page | `frontend/src/features/research/pages/ResearchRunDetailPage.tsx` | unchanged | repository code | expanded in place | added missing Evidence, Skill Report, Hypothesis, Discussion, Decision, Trade Plan fields | reused |
| Ant Design components | npm package `antd` | direct imports | MIT | npm dependency reuse | no source copied | reused |
| Chart dependencies | `echarts`, `lightweight-charts` | removed | upstream package licenses | no runtime reuse | removed unused isolated chart dependencies and unused `CandlestickChart.tsx` | removed |

## System Runtime Status

This milestone copied no external source files and introduced no charting,
monitoring, logging, provider editing, or service-control UI dependencies. It
reused the existing React Router lazy-route pattern, API client, ApiError
handling, Ant Design, TanStack Query, and shared loading/error/time display
helpers.

| Component | Original Location | New Location | License | Reuse Method | Modifications | Status |
| -- | ---- | --- | --- | ---- | ---- | -- |
| API client and ApiError | `frontend/src/infrastructure/api/client.ts` | unchanged | repository code | direct reuse | added System feature API wrapper only | reused |
| React Router app shell | `frontend/src/app/App.tsx` | unchanged | repository code | extended existing lazy route pattern | added `/system`; `/` still redirects to `/dashboard` | reused |
| Application navigation | `frontend/src/app/layout.tsx` | unchanged | repository code | extended existing Ant Design Menu | appended System after Learning Proposals | reused |
| Loading, empty, error, time display | `frontend/src/shared/researchDisplay.tsx` | unchanged | repository code | direct reuse | none | reused |
| Ant Design components | npm package `antd` | direct imports | MIT | npm dependency reuse | no source copied | reused |
| TanStack Query | npm package `@tanstack/react-query` | direct imports | MIT | npm dependency reuse | no source copied | reused |

## AIOS Chinese Business Workbench

This milestone copied no external source files and introduced no charting,
market-data, broker, provider-editing, or monitoring UI dependencies. It reused
the existing Vite/React app, React Router lazy routes, API client, Refine data
provider, Ant Design, TanStack Query, and the existing backend lifecycle data.

| Component | Original Location | New Location | License | Reuse Method | Modifications | Status |
| -- | ---- | --- | --- | ---- | ---- | -- |
| API client and ApiError | `frontend/src/infrastructure/api/client.ts` | unchanged | repository code | direct reuse | added typed business API wrappers only | reused |
| Refine data provider | `frontend/src/infrastructure/refine/dataProvider.ts` | unchanged | repository code | reused existing provider | resource metadata now points to business pages: decisions, reviews, learning | reused |
| React Router app shell | `frontend/src/app/App.tsx` | unchanged | repository code | extended existing lazy route pattern | added `/decisions`, `/reviews`, `/learning`; legacy entity routes redirect to business pages | reused |
| Application navigation | `frontend/src/app/layout.tsx` | unchanged | repository code | reused existing Ant Design Menu | fixed Chinese navigation order: 首页、研究、决策、复盘、学习、系统 | reused |
| Chinese display mappings | `frontend/src/shared/displayMappings.ts` | unchanged | repository code | shared display layer | centralizes page, status, stage, action, direction, trigger, learning, provider mappings | reused |
| Business display components | `frontend/src/shared/businessComponents.tsx` | unchanged | repository code | shared component layer | added status tag, technical details, copyable ID, long text, empty state, readable error | reused |
| Dashboard page | `frontend/src/features/dashboard/DashboardPage.tsx` | unchanged | repository code | rebuilt in place | changed from database-count home to business home: 今日待办、最新研究、异常、复盘 | reused |
| Research pages | `frontend/src/features/research/pages/*` | unchanged | repository code | rebuilt in place | list and detail now follow the AIOS lifecycle from evidence to learning proposal | reused |
| Decision pages | `frontend/src/features/decisions/*` | new feature folder | repository code | new thin UI over backend summary API | lists final decisions with Chinese action/status display | added |
| Review pages | `frontend/src/features/reviews/*` | new feature folder | repository code | new thin UI over backend summary/detail APIs | combines simulated execution, settlement, evaluation, review, and learning | added |
| Learning pages | `frontend/src/features/learning/*` | new feature folder | repository code | new thin UI over backend learning APIs | readable proposals and proposal-only manual approve/reject/defer actions | added |
| System status page | `frontend/src/features/system/pages/SystemStatusPage.tsx` | unchanged | repository code | rebuilt display layer only | localized runtime status and moves raw messages to technical details | reused |
