import type {
  AgentReport,
  Debate,
  DebateStatement,
  Decision,
  DecisionAssembly,
  DecisionProposal,
  Evidence,
  Hypothesis,
  ResearchRun,
  ResearchSession,
  RiskReview,
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
