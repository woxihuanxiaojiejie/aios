import { apiClient } from "../../infrastructure/api/client";
import { explorerApi } from "../explorer/api";
import type { ReviewDetail, ReviewSummaryResponse } from "./types";

export const reviewsApi = {
  summary(params: { page: number; pageSize: number; includeTestData?: boolean }) {
    const search = new URLSearchParams({
      page: String(params.page),
      page_size: String(params.pageSize),
    });
    if (params.includeTestData) search.set("include_test_data", "true");
    return apiClient.get<ReviewSummaryResponse>(`/reviews/summary?${search}`);
  },
  detail(settlementId: string): Promise<ReviewDetail> {
    return explorerApi.settlementDetail(settlementId);
  },
};
