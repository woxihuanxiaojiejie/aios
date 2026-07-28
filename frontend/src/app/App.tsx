import { lazy, Suspense } from "react";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";

import { LoadingState } from "../shared/researchDisplay";
import { ErrorBoundary } from "./ErrorBoundary";
import { AppLayout } from "./layout";
import { AppProviders } from "./providers";

const WatchlistPage = lazy(() =>
  import("../features/watchlist/WatchlistPage").then((module) => ({
    default: module.WatchlistPage,
  })),
);
const ResearchRunsPage = lazy(() =>
  import("../features/research/pages/ResearchRunsPage").then((module) => ({
    default: module.ResearchRunsPage,
  })),
);
const ResearchNewPage = lazy(() =>
  import("../features/research/pages/ResearchNewPage").then((module) => ({
    default: module.ResearchNewPage,
  })),
);
const ResearchRunDetailPage = lazy(() =>
  import("../features/research/pages/ResearchRunDetailPage").then((module) => ({
    default: module.ResearchRunDetailPage,
  })),
);

export function App() {
  return (
    <AppProviders>
      <BrowserRouter>
        <AppLayout>
          <ErrorBoundary>
            <Suspense fallback={<LoadingState />}>
              <Routes>
                <Route path="/" element={<Navigate to="/watchlist" replace />} />
                <Route path="/watchlist" element={<WatchlistPage />} />
                <Route path="/research" element={<ResearchRunsPage />} />
                <Route path="/research/new" element={<ResearchNewPage />} />
                <Route path="/research/:runId" element={<ResearchRunDetailPage />} />
                <Route path="*" element={<Navigate to="/watchlist" replace />} />
              </Routes>
            </Suspense>
          </ErrorBoundary>
        </AppLayout>
      </BrowserRouter>
    </AppProviders>
  );
}
