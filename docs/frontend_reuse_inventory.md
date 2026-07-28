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
