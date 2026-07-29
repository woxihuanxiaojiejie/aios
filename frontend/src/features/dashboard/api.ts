import { apiClient } from "../../infrastructure/api/client";
import type { DashboardSummary } from "./types";

export const dashboardApi = {
  summary() {
    return apiClient.get<DashboardSummary>("/dashboard/summary");
  },
};
