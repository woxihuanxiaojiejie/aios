import { apiClient } from "../../infrastructure/api/client";
import type { Learning, ListResponse } from "../../infrastructure/api/research";
import type { LearningDetail } from "./types";

export const learningApi = {
  list(params: { includeTestData?: boolean } = {}) {
    const search = new URLSearchParams();
    if (params.includeTestData) search.set("include_test_data", "true");
    const suffix = search.toString();
    return apiClient.get<ListResponse<Learning>>(
      suffix ? `/learnings?${suffix}` : "/learnings",
    );
  },
  detail(learningId: string) {
    return apiClient.get<LearningDetail>(
      `/learnings/${encodeURIComponent(learningId)}/detail`,
    );
  },
  approve(learningId: string) {
    return apiClient.post<Learning>(
      `/learnings/${encodeURIComponent(learningId)}/approve`,
      {},
    );
  },
  reject(learningId: string) {
    return apiClient.post<Learning>(
      `/learnings/${encodeURIComponent(learningId)}/reject`,
      {},
    );
  },
  defer(learningId: string) {
    return apiClient.post<Learning>(
      `/learnings/${encodeURIComponent(learningId)}/defer`,
      {},
    );
  },
};
