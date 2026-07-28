export type DashboardSummary = {
  generated_at: string;
  counts: {
    research_runs: number;
    completed_research_runs: number;
    failed_or_resumable_research_runs: number;
    decisions: number;
    trade_plans: number;
    simulated_executions: number;
    settlements: number;
    pending_learning_proposals: number;
    positive_settlements: number;
    negative_settlements: number;
  };
  performance: {
    average_return: string | null;
  };
  attention_required: AttentionRequiredItem[];
  recent_research: RecentResearchItem[];
  recent_settlements: RecentSettlementItem[];
};

export type AttentionRequiredItem = {
  type: string;
  symbol: string | null;
  market: string | null;
  current_stage: string;
  missing_stage: string;
  created_at: string;
  detail_path: string;
  detail_id: string;
};

export type RecentResearchItem = {
  run_id: string;
  created_at: string;
  symbol: string | null;
  market: string | null;
  research_status: string;
  decision_action: string | null;
  confidence: number | null;
  trade_plan_status: string | null;
  current_loop_stage: string;
};

export type RecentSettlementItem = {
  settlement_id: string;
  settled_at: string;
  symbol: string;
  market: string | null;
  decision_action: string | null;
  entry_price: string | null;
  exit_price: string | null;
  return_rate: string | null;
  pnl: string | null;
  evaluation_summary: string | null;
  review_status: string | null;
};
