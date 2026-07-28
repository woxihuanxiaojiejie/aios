import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";

import { ResearchWorkbench } from "../features/research/ResearchWorkbench";
import { WatchlistPage } from "../features/watchlist/WatchlistPage";
import { ErrorBoundary } from "./ErrorBoundary";
import { AppLayout } from "./layout";
import { AppProviders } from "./providers";

export function App() {
  return (
    <AppProviders>
      <BrowserRouter>
        <AppLayout>
          <ErrorBoundary>
            <Routes>
              <Route path="/" element={<Navigate to="/watchlist" replace />} />
              <Route path="/watchlist" element={<WatchlistPage />} />
              <Route path="/research" element={<ResearchWorkbench />} />
              <Route path="*" element={<Navigate to="/watchlist" replace />} />
            </Routes>
          </ErrorBoundary>
        </AppLayout>
      </BrowserRouter>
    </AppProviders>
  );
}
