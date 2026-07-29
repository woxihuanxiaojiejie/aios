import { apiClient } from "../../infrastructure/api/client";
import type { SystemStatusSummary } from "./types";

export const systemApi = {
  status() {
    return apiClient.get<SystemStatusSummary>("/system/status");
  },
};
