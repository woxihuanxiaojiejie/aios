import type { ExplorerDetail } from "../explorer/types";

export type ReviewSummaryResponse = {
  items: ReviewSummary[];
  total: number;
  page: number;
  page_size: number;
  count: number;
};

export type ReviewSummary = {
  settlement_id: string;
  research_run_id: string | null;
  stock_name: string | null;
  symbol: string;
  market: string | null;
  original_decision: string | null;
  research_horizon: string | null;
  execution_time: string | null;
  entry_price: string | null;
  exit_price: string | null;
  return_rate: string | null;
  pnl: string | null;
  directional_result: string | null;
  return_result: string | null;
  risk_result: string | null;
  main_error: string | null;
  learning_proposal_status: string | null;
};

export type ReviewDetail = ExplorerDetail;
