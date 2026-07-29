export type DecisionSummaryResponse = {
  items: DecisionSummary[];
  total: number;
  page: number;
  page_size: number;
  count: number;
};

export type DecisionSummary = {
  decision_id: string;
  research_run_id: string | null;
  stock_name: string | null;
  symbol: string;
  market: string | null;
  decided_at: string;
  research_horizon: string | null;
  action: string;
  confidence: number;
  decision_summary: string;
  core_reason: string;
  risks: string[];
  invalidation_conditions: string[];
  trade_plan_status: string | null;
  simulated_execution_status: string | null;
};
