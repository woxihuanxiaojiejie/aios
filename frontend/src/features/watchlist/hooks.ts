import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { watchlistApi } from "./api";
import type {
  WatchlistCreateInput,
  WatchlistStatus,
  WatchlistUpdateInput,
} from "./types";

export function useWatchlist(status: WatchlistStatus) {
  return useQuery({
    queryKey: ["watchlist", status],
    queryFn: () => watchlistApi.list(status),
  });
}

export function useWatchlistMutations() {
  const queryClient = useQueryClient();
  const invalidate = () =>
    queryClient.invalidateQueries({ queryKey: ["watchlist"] });

  return {
    create: useMutation({
      mutationFn: (payload: WatchlistCreateInput) => watchlistApi.create(payload),
      onSuccess: invalidate,
    }),
    update: useMutation({
      mutationFn: ({
        itemId,
        payload,
      }: {
        itemId: string;
        payload: WatchlistUpdateInput;
      }) => watchlistApi.update(itemId, payload),
      onSuccess: invalidate,
    }),
    archive: useMutation({
      mutationFn: (itemId: string) => watchlistApi.archive(itemId),
      onSuccess: invalidate,
    }),
    restore: useMutation({
      mutationFn: (itemId: string) => watchlistApi.restore(itemId),
      onSuccess: invalidate,
    }),
    run: useMutation({
      mutationFn: (itemId: string) => watchlistApi.run(itemId),
      onSuccess: invalidate,
    }),
  };
}
