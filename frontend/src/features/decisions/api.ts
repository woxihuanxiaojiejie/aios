import { apiClient } from "../../infrastructure/api/client";
import type { DecisionSummaryResponse } from "./types";

export const decisionsApi = {
  summary(params: { page: number; pageSize: number; includeTestData?: boolean }) {
    const search = new URLSearchParams({
      page: String(params.page),
      page_size: String(params.pageSize),
    });
    if (params.includeTestData) search.set("include_test_data", "true");
    return apiClient.get<DecisionSummaryResponse>(`/decisions/summary?${search}`);
  },
};
