import { apiClient } from "../../infrastructure/api/client";
import type { ExplorerDetail, ExplorerListResponse, SettlementListItem } from "./types";
import type { ExecutionListItem } from "./types";

export const explorerApi = {
  executionDetail(executionId: string) {
    return apiClient.get<ExplorerDetail>(
      `/simulated-executions/${encodeURIComponent(executionId)}`,
    );
  },
  settlementDetail(settlementId: string) {
    return apiClient.get<ExplorerDetail>(
      `/settlements/${encodeURIComponent(settlementId)}`,
    );
  },
  listExecutions(query: string) {
    return apiClient.get<ExplorerListResponse<ExecutionListItem>>(
      `/simulated-executions${query}`,
    );
  },
  listSettlements(query: string) {
    return apiClient.get<ExplorerListResponse<SettlementListItem>>(
      `/settlements${query}`,
    );
  },
};
