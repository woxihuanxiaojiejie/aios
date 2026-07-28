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
