import { apiClient } from "../../infrastructure/api/client";
import type { RuntimeResearchResponse } from "../../infrastructure/api/research";
import type {
  WatchlistCreateInput,
  WatchlistItem,
  WatchlistStatus,
  WatchlistUpdateInput,
} from "./types";

type ListResponse<T> = {
  items: T[];
  total: number;
  limit: number;
  offset: number;
};

export const watchlistApi = {
  list(status: WatchlistStatus = "active") {
    const query = status === "active" ? "" : `?status=${status}`;
    return apiClient.get<ListResponse<WatchlistItem>>(`/research/watchlist${query}`);
  },
  create(payload: WatchlistCreateInput) {
    return apiClient.post<WatchlistItem>("/research/watchlist", payload);
  },
  update(itemId: string, payload: WatchlistUpdateInput) {
    return apiClient.patch<WatchlistItem>(
      `/research/watchlist/${encodeURIComponent(itemId)}`,
      payload,
    );
  },
  archive(itemId: string) {
    return apiClient.post<WatchlistItem>(
      `/research/watchlist/${encodeURIComponent(itemId)}/archive`,
    );
  },
  restore(itemId: string) {
    return apiClient.post<WatchlistItem>(
      `/research/watchlist/${encodeURIComponent(itemId)}/restore`,
    );
  },
  run(itemId: string) {
    return apiClient.post<RuntimeResearchResponse>(
      `/research/watchlist/${encodeURIComponent(itemId)}/run`,
    );
  },
};
