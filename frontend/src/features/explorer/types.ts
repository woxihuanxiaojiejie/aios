import type {
  Decision,
  Evaluation,
  Learning,
  Outcome,
  ResearchRun,
  ResearchSession,
  Review,
  SimulatedExecution,
  TradePlan,
} from "../../infrastructure/api/research";

export type ExplorerListResponse<T> = {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  count: number;
};

export type ExecutionListItem = {
  execution_id: string;
  symbol: string;
  market: string | null;
  side: string;
  action: string;
  quantity: string;
  simulated_price: string | null;
  status: string;
  created_at: string;
  research_run_id: string | null;
  research_session_id: string;
  decision_id: string;
  trade_plan_id: string;
  settlement_id: string | null;
};

export type SettlementListItem = {
  settlement_id: string;
  execution_id: string | null;
  trade_plan_id: string | null;
  decision_id: string;
  research_session_id: string | null;
  research_run_id: string | null;
  symbol: string;
  market: string | null;
  status: string;
  entry_price: string | null;
  exit_price: string | null;
  return_rate: string | null;
  pnl: string | null;
  settled_at: string;
  created_at: string;
};

export type ExplorerDetail = {
  research_run: ResearchRun | null;
  research_session: ResearchSession | null;
  decision: Decision | null;
  trade_plan: TradePlan | null;
  simulated_execution: SimulatedExecution | null;
  settlement: Outcome | null;
  evaluation: Evaluation | null;
  review: Review | null;
  learning_proposals: Learning[];
};

export type ExplorerFilters = {
  symbol?: string;
  market?: string;
  status?: string;
  created_from?: string;
  created_to?: string;
  sort?: string;
};
