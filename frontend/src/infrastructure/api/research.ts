export type ApiErrorBody = {
  error: {
    code: string;
    message: string;
    details: Record<string, unknown>;
  };
};

import { ApiError, apiClient } from "./client";

export { ApiError };

export type MarketBar = {
  symbol: string;
  market: string;
  trade_date: string;
  open: string;
  high: string;
  low: string;
  close: string;
  volume: string;
  amount: string | null;
  adjustment: string;
  source: string;
  fetched_at: string;
};

export type MarketResponse = {
  symbol: string;
  market: string;
  source: string;
  data_source: string;
  latest: MarketBar;
  bars: MarketBar[];
  change: string | null;
  change_percent: string | null;
  observed_at: string;
  available_at: string;
};

export type Evidence = {
  evidence_id: string;
  evidence_type: string;
  source: string;
  symbols: string[];
  published_at: string;
  available_at: string;
  summary: string;
  reliability: number;
  content_hash: string;
  metadata: Record<string, unknown>;
  created_at: string;
};

export type EvidenceImportResponse = {
  symbol: string;
  requested: number;
  created: number;
  existing: number;
  evidence_ids: string[];
  latest_evidence: Evidence | null;
};

export type ListResponse<T> = {
  items: T[];
  total: number;
  limit: number;
  offset: number;
};

export type WatchlistItem = {
  watchlist_item_id: string;
  symbol: string;
  market: string;
  note: string | null;
  status: string;
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

export type ResearchRun = {
  run_id: string;
  research_session_id: string | null;
  watchlist_item_id: string;
  symbol: string | null;
  research_window_key: string | null;
  current_stage: string;
  status: string;
  failed_stage: string | null;
  error_type: string | null;
  error: string | null;
  finished_at: string | null;
  created_at: string;
  updated_at: string;
};

export type ResearchSession = {
  research_session_id: string;
  scope: {
    watchlist_item_id: string;
    symbol: string;
    market: string;
    watchlist_note_snapshot: string | null;
    horizon_days: number;
    as_of: string;
    valid_until: string;
  };
  status: string;
  evidence_ids: string[];
  experiment_id: string | null;
  cancelled_at: string | null;
  created_at: string;
  updated_at: string;
};

export type AgentReport = {
  report_id: string;
  research_session_id: string;
  role: string;
  summary: string;
  stance: string;
  confidence: number;
  evidence_ids: string[];
  source: string;
  raw_reference: string | null;
  status: string;
  archived_at: string | null;
  created_at: string;
  updated_at: string;
};

export type Hypothesis = {
  hypothesis_id: string;
  research_session_id: string;
  statement: string;
  rationale: string;
  direction: string;
  horizon_days: number;
  confidence: number;
  supporting_report_ids: string[];
  supporting_evidence_ids: string[];
  status: string;
  created_at: string;
  updated_at: string;
};

export type Debate = {
  debate_id: string;
  research_session_id: string;
  report_ids: string[];
  hypothesis_ids: string[];
  status: string;
  final_decision_id: string | null;
  created_at: string;
  updated_at: string;
};

export type DebateStatement = {
  statement_id: string;
  debate_id: string;
  agent_report_id: string;
  hypothesis_id: string;
  stance: string;
  reasoning: string;
  evidence_ids: string[];
  confidence_before: number;
  confidence_after: number;
  created_at: string;
};

export type DecisionProposal = {
  proposal_id: string;
  debate_id: string;
  conclusion: string;
  confidence: number;
  thesis: string;
  supporting_hypothesis_ids: string[];
  rejected_hypothesis_ids: string[];
  evidence_ids: string[];
  risk_notes: string[];
  created_at: string;
};

export type RiskReview = {
  risk_review_id: string;
  proposal_id: string;
  verdict: string;
  final_conclusion: string;
  final_confidence: number;
  reasons: string[];
  created_at: string;
};

export type DecisionAssembly = {
  assembly_id: string;
  research_session_id: string;
  debate_id: string;
  proposal_id: string;
  risk_review_id: string;
  decision_id: string;
  conclusion: string;
  report_ids: string[];
  hypothesis_ids: string[];
  evidence_ids: string[];
  created_at: string;
};

export type Experiment = {
  experiment_id: string;
  name: string;
  model: string;
  prompt_version: string;
  agent_config_version: string;
  dataset_snapshot: string;
  evidence_ids: string[];
  parameters: Record<string, unknown>;
  status: string;
  started_at: string;
  finished_at: string | null;
  created_at: string;
};

export type Decision = {
  decision_id: string;
  experiment_id: string;
  symbol: string;
  action: string;
  horizon: string;
  confidence: number;
  expected_return: number;
  max_expected_loss: number;
  evidence_ids: string[];
  reasoning_summary: string;
  status: string;
  created_at: string;
  valid_until: string;
};

export type Generation = {
  provider: string;
  model: string;
  prompt_version: string;
  request_id: string | null;
  prompt_tokens: number | null;
  completion_tokens: number | null;
  total_tokens: number | null;
  latency_ms: number;
  raw_finish_reason: string | null;
};

export type DecisionRunResponse = {
  decision: Decision;
  generation: Generation;
};

export type TradePlan = {
  trade_plan_id: string;
  decision_id: string;
  research_session_id: string;
  symbol: string;
  direction: string;
  status: string;
  horizon: string;
  expiry: string;
  no_trade_reasons: string[];
  unavailable_fields: string[];
};

export type SimulatedExecution = {
  execution_id: string;
  trade_plan_id: string;
  decision_id: string;
  research_session_id: string;
  symbol: string;
  direction: string;
  execution_status: string;
  execution_date: string | null;
  exit_reason: string;
  created_at: string;
  updated_at: string;
};

export type RuntimeResearchResponse = {
  run: ResearchRun;
  trade_plan: TradePlan | null;
  simulated_execution: SimulatedExecution | null;
};

export type Outcome = {
  outcome_id: string;
  decision_id: string;
  experiment_id: string;
  symbol: string;
  horizon: string;
  horizon_semantics: string;
  observation_started_at: string;
  observation_ended_at: string;
  entry_price: string | null;
  exit_price: string | null;
  realized_return: string | null;
  maximum_adverse_excursion: string | null;
  maximum_favorable_excursion: string | null;
  market_data_source: string;
  settled_at: string;
  status: string;
  created_at: string;
};

export type Evaluation = {
  evaluation_id: string;
  decision_id: string;
  outcome_id: string;
  experiment_id: string;
  directional_result: string;
  return_result: string;
  risk_result: string;
  final_result: string;
  evaluation_rules_version: string;
  evaluated_at: string;
  explanation: string;
  created_at: string;
};

export type Review = {
  review_id: string;
  decision_id: string;
  actual_return: string | null;
  direction_correct: boolean | null;
  risk_limit_breached: boolean | null;
  outcome: string;
  cause_tags: string[];
  review_summary: string;
  created_at: string;
};

export type SettlementResponse = {
  outcome: Outcome;
  evaluation: Evaluation;
  review: Review;
};

export type Learning = {
  learning_id: string;
  review_id: string;
  learning_type: string;
  target: string;
  before: unknown;
  after: unknown;
  reason: string;
  approval_status: string;
  created_at: string;
};

export type ResearchSettlementRecord = {
  research_settlement_id: string;
  assembly_id: string;
  research_session_id: string;
  debate_id: string;
  proposal_id: string;
  risk_review_id: string;
  decision_id: string;
  outcome_id: string;
  evaluation_id: string;
  review_id: string;
  learning_ids: string[];
  evidence_ids: string[];
  report_ids: string[];
  hypothesis_ids: string[];
  settled_at: string;
  created_at: string;
};

export type AssemblySettlementResponse = SettlementResponse & {
  record: ResearchSettlementRecord;
  learnings: Learning[];
};

export type HistoryRow = {
  time: string;
  type: string;
  decision_id: string | null;
  direction: string | null;
  confidence: number | null;
  realized_return: string | null;
  review_outcome: string | null;
  status: string;
};

export type HistoryResponse = {
  symbol: string;
  latest_evidence: Evidence | null;
  latest_experiment: Experiment | null;
  latest_decision: Decision | null;
  latest_outcome: Outcome | null;
  latest_evaluation: Evaluation | null;
  latest_review: Review | null;
  rows: HistoryRow[];
};

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const body = init?.body ? JSON.parse(String(init.body)) : undefined;
  if (init?.method === "POST") return apiClient.post<T>(path, body);
  if (init?.method === "PATCH") return apiClient.patch<T>(path, body);
  if (init?.method === "DELETE") return apiClient.delete<T>(path);
  return apiClient.get<T>(path);
}

export const researchApi = {
  listWatchlist() {
    return request<ListResponse<WatchlistItem>>("/research/watchlist");
  },
  addWatchlist(symbol: string, market: string, note?: string) {
    return request<WatchlistItem>("/research/watchlist", {
      method: "POST",
      body: JSON.stringify({ symbol, market, note: note || null }),
    });
  },
  updateWatchlist(
    itemId: string,
    payload: Partial<
      Pick<
        WatchlistItem,
        | "auto_research_enabled"
        | "research_horizon_days"
        | "schedule_time"
        | "schedule_timezone"
        | "next_run_at"
      >
    >,
  ) {
    return request<WatchlistItem>(`/research/watchlist/${itemId}`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    });
  },
  runWatchlist(itemId: string) {
    return request<RuntimeResearchResponse>(`/research/watchlist/${itemId}/run`, {
      method: "POST",
      body: JSON.stringify({}),
    });
  },
  runSchedulerOnce() {
    return request<{ runs: ResearchRun[]; errors: unknown[] }>(
      "/research/scheduler/run-once",
      {
        method: "POST",
        body: JSON.stringify({}),
      },
    );
  },
  runSettlementOnce() {
    return request<{ settled: SettlementResponse[]; errors: unknown[] }>(
      "/research/settlement/run-once",
      {
        method: "POST",
        body: JSON.stringify({}),
      },
    );
  },
  listEvidence() {
    return request<ListResponse<Evidence>>("/evidence");
  },
  createManualEvidence(payload: {
    evidence_type: string;
    source: string;
    symbols: string[];
    published_at: string;
    available_at: string;
    summary: string;
    reliability: number;
    content_hash: string;
    metadata: Record<string, unknown>;
  }) {
    return request<Evidence>("/evidence", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },
  listSessions() {
    return request<ListResponse<ResearchSession>>("/research/sessions");
  },
  createSession(payload: {
    watchlist_item_id: string;
    horizon_days: number;
    as_of: string;
    evidence_ids: string[];
  }) {
    return request<ResearchSession>("/research/sessions", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },
  listAgentReports(sessionId: string) {
    return request<ListResponse<AgentReport>>(
      `/research/sessions/${sessionId}/agent-reports`,
    );
  },
  createAgentReport(sessionId: string, payload: Record<string, unknown>) {
    return request<AgentReport>(
      `/research/sessions/${sessionId}/agent-reports`,
      {
        method: "POST",
        body: JSON.stringify(payload),
      },
    );
  },
  listHypotheses(sessionId: string) {
    return request<ListResponse<Hypothesis>>(
      `/research/sessions/${sessionId}/hypotheses`,
    );
  },
  createHypothesis(sessionId: string, payload: Record<string, unknown>) {
    return request<Hypothesis>(`/research/sessions/${sessionId}/hypotheses`, {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },
  createDebate(sessionId: string) {
    return request<Debate>(`/research/sessions/${sessionId}/debates`, {
      method: "POST",
      body: JSON.stringify({}),
    });
  },
  listDebates(sessionId: string) {
    return request<ListResponse<Debate>>(
      `/research/sessions/${sessionId}/debates`,
    );
  },
  addDebateStatement(debateId: string, payload: Record<string, unknown>) {
    return request<DebateStatement>(`/research/debates/${debateId}/statements`, {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },
  createProposal(debateId: string, payload: Record<string, unknown>) {
    return request<DecisionProposal>(`/research/debates/${debateId}/proposal`, {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },
  createRiskReview(proposalId: string, payload: Record<string, unknown>) {
    return request<RiskReview>(`/research/proposals/${proposalId}/risk-review`, {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },
  finalizeProposal(proposalId: string) {
    return request<DecisionAssembly>(`/research/proposals/${proposalId}/finalize`, {
      method: "POST",
      body: JSON.stringify({}),
    });
  },
  settleAssembly(assemblyId: string, asOf?: string) {
    return request<AssemblySettlementResponse>(
      `/research/assemblies/${assemblyId}/settlement`,
      {
        method: "POST",
        body: JSON.stringify({ as_of: asOf || null }),
      },
    );
  },
  listLearnings() {
    return request<ListResponse<Learning>>("/learnings");
  },
  market(symbol: string) {
    return request<MarketResponse>(
      `/research/market?symbol=${encodeURIComponent(symbol)}`,
    );
  },
  createEvidence(symbol: string) {
    return request<EvidenceImportResponse>("/research/evidence", {
      method: "POST",
      body: JSON.stringify({ symbol }),
    });
  },
  createExperiment(symbol: string, evidenceIds: string[], model?: string) {
    return request<Experiment>("/research/experiments", {
      method: "POST",
      body: JSON.stringify({ symbol, evidence_ids: evidenceIds, model }),
    });
  },
  runDecision(experimentId: string, symbol: string, horizon: string) {
    return request<DecisionRunResponse>("/research/decisions", {
      method: "POST",
      body: JSON.stringify({ experiment_id: experimentId, symbol, horizon }),
    });
  },
  settleDecision(decisionId: string) {
    return request<SettlementResponse>(`/research/settlements/${decisionId}`, {
      method: "POST",
      body: JSON.stringify({}),
    });
  },
  history(symbol: string) {
    return request<HistoryResponse>(
      `/research/history?symbol=${encodeURIComponent(symbol)}`,
    );
  },
};
