import { useQuery } from "@tanstack/react-query";

import { researchRunApi } from "../api";

export function useResearchRunDetail(runId: string | undefined) {
  return useQuery({
    queryKey: ["research-run-detail", runId],
    queryFn: () => researchRunApi.detail(runId!),
    enabled: Boolean(runId),
  });
}
