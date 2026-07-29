import { lazy, Suspense } from "react";
import { BrowserRouter, Navigate, Route, Routes, useParams } from "react-router-dom";

import { LoadingState } from "../shared/researchDisplay";
import { ErrorBoundary } from "./ErrorBoundary";
import { AppLayout } from "./layout";
import { AppProviders } from "./providers";

const DashboardPage = lazy(() =>
  import("../features/dashboard/DashboardPage").then((module) => ({
    default: module.DashboardPage,
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
const DecisionsPage = lazy(() =>
  import("../features/decisions/pages/DecisionsPage").then((module) => ({
    default: module.DecisionsPage,
  })),
);
const ReviewsPage = lazy(() =>
  import("../features/reviews/pages/ReviewsPage").then((module) => ({
    default: module.ReviewsPage,
  })),
);
const ReviewDetailPage = lazy(() =>
  import("../features/reviews/pages/ReviewDetailPage").then((module) => ({
    default: module.ReviewDetailPage,
  })),
);
const LearningPage = lazy(() =>
  import("../features/learning/pages/LearningPage").then((module) => ({
    default: module.LearningPage,
  })),
);
const LearningDetailPage = lazy(() =>
  import("../features/learning/pages/LearningDetailPage").then((module) => ({
    default: module.LearningDetailPage,
  })),
);
const ExecutionDetailPage = lazy(() =>
  import("../features/explorer/pages/ExecutionDetailPage").then((module) => ({
    default: module.ExecutionDetailPage,
  })),
);
const SystemStatusPage = lazy(() =>
  import("../features/system/pages/SystemStatusPage").then((module) => ({
    default: module.SystemStatusPage,
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
                <Route path="/" element={<Navigate to="/dashboard" replace />} />
                <Route path="/dashboard" element={<DashboardPage />} />
                <Route path="/research" element={<ResearchRunsPage />} />
                <Route path="/research/new" element={<ResearchNewPage />} />
                <Route path="/research/:runId" element={<ResearchRunDetailPage />} />
                <Route path="/decisions" element={<DecisionsPage />} />
                <Route path="/reviews" element={<ReviewsPage />} />
                <Route path="/reviews/:settlementId" element={<ReviewDetailPage />} />
                <Route path="/learning" element={<LearningPage />} />
                <Route path="/learning/:learningId" element={<LearningDetailPage />} />
                <Route path="/executions" element={<Navigate to="/reviews" replace />} />
                <Route path="/executions/:executionId" element={<ExecutionDetailPage />} />
                <Route path="/settlements" element={<Navigate to="/reviews" replace />} />
                <Route
                  path="/settlements/:settlementId"
                  element={<NavigateSettlementToReview />}
                />
                <Route path="/learning-proposals" element={<Navigate to="/learning" replace />} />
                <Route path="/system" element={<SystemStatusPage />} />
                <Route path="*" element={<Navigate to="/dashboard" replace />} />
              </Routes>
            </Suspense>
          </ErrorBoundary>
        </AppLayout>
      </BrowserRouter>
    </AppProviders>
  );
}

function NavigateSettlementToReview() {
  const { settlementId } = useParams();
  return (
    <Navigate
      to={`/reviews/${encodeURIComponent(settlementId ?? "")}`}
      replace
    />
  );
}
