import type {
  AgentReport,
  Debate,
  DebateStatement,
  Decision,
  DecisionAssembly,
  DecisionProposal,
  Evaluation,
  Evidence,
  Hypothesis,
  Learning,
  Outcome,
  ResearchRun,
  ResearchSession,
  Review,
  RiskReview,
  SimulatedExecution,
  TradePlan,
  WatchlistItem,
} from "../../../infrastructure/api/research";

export type ResearchRunListItem = ResearchRun & {
  market: string | null;
  trigger_method: string | null;
  final_decision: string | null;
  confidence: number | null;
};

export type ResearchRunDiscussion = {
  debates: Debate[];
  statements: DebateStatement[];
  proposal: DecisionProposal | null;
  risk_review: RiskReview | null;
  assembly: DecisionAssembly | null;
};

export type ResearchRunDetail = {
  run: ResearchRun;
  watchlist_item: WatchlistItem | null;
  session: ResearchSession | null;
  evidence: Evidence[];
  skill_reports: AgentReport[];
  hypotheses: Hypothesis[];
  discussion: ResearchRunDiscussion;
  decision: Decision | null;
  trade_plan: TradePlan | null;
  simulated_execution: SimulatedExecution | null;
  settlement: Outcome | null;
  evaluation: Evaluation | null;
  review: Review | null;
  learning_proposals: Learning[];
};

export type ResearchRunFilters = {
  symbol?: string;
  market?: string;
  status?: string;
  workflow?: string;
  created_from?: string;
  created_to?: string;
  sort?: string;
};
