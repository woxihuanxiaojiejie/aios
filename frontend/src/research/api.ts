export type ApiErrorBody = {
  error: {
    code: string;
    message: string;
    details: Record<string, unknown>;
  };
};

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

export class ApiError extends Error {
  code: string;
  status: number;

  constructor(status: number, code: string, message: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
  }
}

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000/api/v1";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers: {
      "content-type": "application/json",
      ...init?.headers,
    },
  });
  const body = (await response.json().catch(() => null)) as unknown;
  if (!response.ok) {
    const error = body as ApiErrorBody | null;
    throw new ApiError(
      response.status,
      error?.error?.code ?? "request_failed",
      error?.error?.message ?? "Backend request failed",
    );
  }
  return body as T;
}

export const researchApi = {
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
