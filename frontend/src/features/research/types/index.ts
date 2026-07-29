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

export type AnalysisTask = {
  task_id: string;
  symbol: string;
  market: string;
  asset_type: string;
  horizon: string;
  as_of: string;
  evidence_ids: string[];
  user_constraints: Record<string, unknown>;
  requested_skill_ids: string[];
  created_at: string;
};

export type SkillExecution = {
  execution_id: string;
  task_id: string;
  skill_id: string;
  skill_version: string;
  started_at: string;
  finished_at: string | null;
  status: string;
  provider: string | null;
  model: string | null;
  prompt_version: string | null;
  latency_ms: number | null;
  retry_count: number;
  error: string | null;
};

export type SkillResult = {
  result_id: string;
  execution_id: string;
  skill_id: string;
  skill_version: string;
  conclusion: string;
  direction: string;
  confidence: number;
  supporting_evidence_ids: string[];
  contradicting_evidence_ids: string[];
  assumptions: string[];
  risk_factors: string[];
  invalid_conditions: string[];
  missing_information: string[];
  reasoning_summary: string;
  raw_output: Record<string, unknown>;
  created_at: string;
};

export type DiscussionResult = {
  discussion_result_id: string;
  discussion_execution_id: string;
  task_id: string;
  skill_result_ids: string[];
  conflicts: Record<string, unknown>[];
  evidence_reviews: Record<string, unknown>[];
  counter_arguments: Record<string, unknown>[];
  revision_suggestions: Record<string, unknown>[];
  discussion_summary: string;
  discussion_confidence: number;
  created_at: string;
};

export type DecisionResult = {
  decision_result_id: string;
  decision_execution_id: string;
  discussion_result_id: string;
  action: string;
  direction: string;
  confidence: number;
  rationale: string;
  supporting_reasons: Record<string, unknown>[];
  risk_factors: Record<string, unknown>[];
  rejected_directions: Record<string, unknown>[];
  invalidation_conditions: string[];
  created_at: string;
};

export type ResearchRunDetail = {
  run: ResearchRun;
  watchlist_item: WatchlistItem | null;
  session: ResearchSession | null;
  evidence: Evidence[];
  skill_reports: AgentReport[];
  hypotheses: Hypothesis[];
  analysis_task: AnalysisTask | null;
  skill_executions: SkillExecution[];
  skill_results: SkillResult[];
  discussion_result: DiscussionResult | null;
  decision_result: DecisionResult | null;
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
