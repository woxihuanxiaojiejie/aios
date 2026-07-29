import { apiClient } from "../../../infrastructure/api/client";
import type { ResearchRunDetail } from "../types";

export const researchRunApi = {
  detail(runId: string) {
    return apiClient.get<ResearchRunDetail>(
      `/research/runs/${encodeURIComponent(runId)}/detail`,
    );
  },
};
