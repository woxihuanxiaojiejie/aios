export type WatchlistStatus = "active" | "archived";

export type WatchlistItem = {
  watchlist_item_id: string;
  symbol: string;
  market: string;
  note: string | null;
  status: WatchlistStatus;
  auto_research_enabled: boolean;
  research_horizon_days: number;
  schedule_time: string;
  schedule_timezone: string;
  next_run_at: string | null;
  last_run_at: string | null;
  created_at: string;
  updated_at: string;
  archived_at: string | null;
};

export type WatchlistCreateInput = {
  symbol: string;
  market: string;
  note?: string | null;
  auto_research_enabled?: boolean;
  research_horizon_days?: number;
  schedule_time?: string;
  schedule_timezone?: string;
  next_run_at?: string | null;
};

export type WatchlistUpdateInput = {
  note?: string | null;
  auto_research_enabled?: boolean;
  research_horizon_days?: number;
  schedule_time?: string;
  schedule_timezone?: string;
  next_run_at?: string | null;
};
