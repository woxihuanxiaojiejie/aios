import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi, beforeEach } from "vitest";

import { ResearchWorkbench } from "./ResearchWorkbench";

vi.mock("lightweight-charts", () => ({
  createChart: () => ({
    addCandlestickSeries: () => ({ setData: vi.fn() }),
    addHistogramSeries: () => ({
      setData: vi.fn(),
      priceScale: () => ({ applyOptions: vi.fn() }),
    }),
    applyOptions: vi.fn(),
    remove: vi.fn(),
    removeSeries: vi.fn(),
    timeScale: () => ({ fitContent: vi.fn() }),
  }),
}));

const marketResponse = {
  symbol: "000001.SZ",
  market: "CN_A",
  source: "deterministic-market",
  data_source: "REAL MARKET DATA",
  latest: bar("2026-07-19", "10.30"),
  bars: [bar("2026-07-18", "10.00"), bar("2026-07-19", "10.30")],
  change: "0.30",
  change_percent: "0.03",
  observed_at: "2026-07-19T00:00:00Z",
  available_at: "2026-07-20T08:00:00Z",
};

const evidenceResponse = {
  symbol: "000001.SZ",
  requested: 2,
  created: 2,
  existing: 0,
  evidence_ids: ["ev_1"],
  latest_evidence: {
    evidence_id: "ev_1",
    evidence_type: "market_daily_bar",
    source: "deterministic-market",
    symbols: ["000001.SZ"],
    published_at: "2026-07-19T07:00:00Z",
    available_at: "2026-07-20T08:00:00Z",
    summary: "CN_A 000001.SZ close 10.30",
    reliability: 0.95,
    content_hash: "hash",
    metadata: {},
    created_at: "2026-07-20T08:00:00Z",
  },
};

const experimentResponse = {
  experiment_id: "ex_1",
  name: "research-000001.SZ",
  model: "deepseek/deepseek-chat",
  prompt_version: "decision-v1",
  agent_config_version: "manual-research-ui",
  dataset_snapshot: "market-evidence:000001.SZ",
  evidence_ids: ["ev_1"],
  parameters: { temperature: 0 },
  status: "created",
  started_at: "2026-07-20T08:00:00Z",
  finished_at: null,
  created_at: "2026-07-20T08:00:00Z",
};

const decisionResponse = {
  decision: {
    decision_id: "dc_1",
    experiment_id: "ex_1",
    symbol: "000001.SZ",
    action: "buy",
    horizon: "1d",
    confidence: 0.7,
    expected_return: 0.02,
    max_expected_loss: 0.05,
    evidence_ids: ["ev_1"],
    reasoning_summary: "bounded long thesis",
    status: "proposed",
    created_at: "2026-07-20T08:00:00Z",
    valid_until: "2026-07-21T08:00:00Z",
  },
  generation: {
    provider: "deepseek",
    model: "deepseek/deepseek-chat",
    prompt_version: "decision-v1",
    request_id: "req_1",
    prompt_tokens: 10,
    completion_tokens: 5,
    total_tokens: 15,
    latency_ms: 1000,
    raw_finish_reason: "stop",
  },
};

const settlementResponse = {
  outcome: {
    outcome_id: "oc_1",
    decision_id: "dc_1",
    experiment_id: "ex_1",
    symbol: "000001.SZ",
    horizon: "1d",
    horizon_semantics: "natural_time",
    observation_started_at: "2026-07-20T08:00:00Z",
    observation_ended_at: "2026-07-21T08:00:00Z",
    entry_price: "10.30",
    exit_price: "10.60",
    realized_return: "0.029",
    maximum_adverse_excursion: "-0.01",
    maximum_favorable_excursion: "0.04",
    market_data_source: "deterministic-market",
    settled_at: "2026-07-22T08:00:00Z",
    status: "settled",
    created_at: "2026-07-22T08:00:00Z",
  },
  evaluation: {
    evaluation_id: "de_1",
    decision_id: "dc_1",
    outcome_id: "oc_1",
    experiment_id: "ex_1",
    directional_result: "correct",
    return_result: "met",
    risk_result: "within_limit",
    final_result: "pass",
    evaluation_rules_version: "decision-evaluation-v1",
    evaluated_at: "2026-07-22T08:00:00Z",
    explanation: "deterministic evaluation",
    created_at: "2026-07-22T08:00:00Z",
  },
  review: {
    review_id: "rv_1",
    decision_id: "dc_1",
    actual_return: "0.029",
    direction_correct: true,
    risk_limit_breached: false,
    outcome: "profit",
    cause_tags: ["direction_correct", "positive_return"],
    review_summary: "Decision settled with a positive realized return.",
    created_at: "2026-07-22T08:00:00Z",
  },
};

const emptyHistory = {
  symbol: "000001.SZ",
  latest_evidence: null,
  latest_experiment: null,
  latest_decision: null,
  latest_outcome: null,
  latest_evaluation: null,
  latest_review: null,
  rows: [],
};

describe("ResearchWorkbench", () => {
  beforeEach(() => {
    vi.stubGlobal("ResizeObserver", class {
      observe() {}
      disconnect() {}
    });
  });

  it("loads market data for a typed stock symbol", async () => {
    mockFetch();
    renderWorkbench();

    await screen.findByLabelText("Daily candlestick chart");
    await userEvent.clear(screen.getByLabelText("Stock Symbol"));
    await userEvent.type(screen.getByLabelText("Stock Symbol"), "000001.SZ");
    await userEvent.click(screen.getByRole("button", { name: /load/i }));

    expect(await screen.findByText("REAL MARKET DATA")).toBeInTheDocument();
    expect(screen.getByText("CN_A")).toBeInTheDocument();
  });

  it("shows market loading failure", async () => {
    mockFetch({ marketError: true });
    renderWorkbench();

    expect(
      await screen.findByText(/market_data_unsupported_symbol/i),
    ).toBeInTheDocument();
  });

  it("creates Evidence and displays Evidence details", async () => {
    mockFetch();
    renderWorkbench();

    await userEvent.click(await screen.findByRole("button", { name: /create evidence/i }));

    expect(await screen.findByText("ev_1")).toBeInTheDocument();
    expect(screen.getByText(/CN_A 000001.SZ close/)).toBeInTheDocument();
  });

  it("shows AI loading state and renders Decision metadata", async () => {
    mockFetch({ slowDecision: true });
    renderWorkbench();

    await userEvent.click(await screen.findByRole("button", { name: /create evidence/i }));
    await userEvent.click(screen.getByRole("button", { name: /run ai analysis/i }));

    expect(screen.getByText("Loading...")).toBeInTheDocument();
    expect(await screen.findByText("deepseek")).toBeInTheDocument();
    expect(screen.getByText("req_1")).toBeInTheDocument();
  });

  it("displays no trade decisions", async () => {
    mockFetch({ action: "no_trade" });
    renderWorkbench();

    await userEvent.click(await screen.findByRole("button", { name: /create evidence/i }));
    await userEvent.click(screen.getByRole("button", { name: /run ai analysis/i }));

    expect(await screen.findByText("no_trade")).toBeInTheDocument();
    expect(screen.getByText("Yes")).toBeInTheDocument();
  });

  it("shows DeepSeek authentication errors", async () => {
    mockFetch({ decisionError: true });
    renderWorkbench();

    await userEvent.click(await screen.findByRole("button", { name: /create evidence/i }));
    await userEvent.click(screen.getByRole("button", { name: /run ai analysis/i }));

    expect(await screen.findByText(/llm_unavailable/i)).toBeInTheDocument();
  });

  it("shows settlement not-ready errors", async () => {
    mockFetch({ settlementError: true });
    renderWorkbench();

    await createDecision();
    await userEvent.click(screen.getByRole("button", { name: /settle decision/i }));

    expect(
      await screen.findByText(/invalid_state_transition/i),
    ).toBeInTheDocument();
  });

  it("renders Review after settlement", async () => {
    mockFetch();
    renderWorkbench();

    await createDecision();
    await userEvent.click(screen.getByRole("button", { name: /settle decision/i }));

    expect(await screen.findByText("profit")).toBeInTheDocument();
    expect(screen.getByText(/positive realized return/i)).toBeInTheDocument();
  });

  it("shows empty history state", async () => {
    mockFetch();
    renderWorkbench();

    expect(
      await screen.findByText("No saved records for this symbol."),
    ).toBeInTheDocument();
  });

  it("shows initial empty workflow states", async () => {
    mockFetch();
    renderWorkbench();

    expect(
      await screen.findByText("No Evidence has been created yet."),
    ).toBeInTheDocument();
    expect(
      screen.getByText("Run AI analysis to create a Decision."),
    ).toBeInTheDocument();
    expect(screen.getByText("No Settlement or Review yet.")).toBeInTheDocument();
  });

  it("renders history rows from the backend", async () => {
    mockFetch({ historyRows: true });
    renderWorkbench();

    expect(await screen.findByText("buy")).toBeInTheDocument();
    expect(screen.getAllByText("profit")).toHaveLength(2);
  });

  it("shows backend connection failures", async () => {
    mockFetch({ backendDown: true });
    renderWorkbench();

    expect(await screen.findAllByText("Backend unavailable")).toHaveLength(2);
  });
});

async function createDecision() {
  await userEvent.click(await screen.findByRole("button", { name: /create evidence/i }));
  await userEvent.click(screen.getByRole("button", { name: /run ai analysis/i }));
  await screen.findByText("req_1");
}

function renderWorkbench() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  render(
    <QueryClientProvider client={queryClient}>
      <ResearchWorkbench />
    </QueryClientProvider>,
  );
}

function mockFetch(options: {
  action?: string;
  backendDown?: boolean;
  decisionError?: boolean;
  historyRows?: boolean;
  marketError?: boolean;
  settlementError?: boolean;
  slowDecision?: boolean;
} = {}) {
  const responseFor = async (url: string) => {
    if (options.backendDown) {
      throw new Error("Backend unavailable");
    }
    if (url.includes("/research/market")) {
      if (options.marketError) {
        return jsonError(400, "market_data_unsupported_symbol", "unsupported");
      }
      return jsonOk(marketResponse);
    }
    if (url.includes("/research/history")) {
      if (options.historyRows) {
        return jsonOk({
          ...emptyHistory,
          rows: [
            {
              time: "2026-07-22T08:00:00Z",
              type: "decision",
              decision_id: "dc_1",
              direction: "buy",
              confidence: 0.7,
              realized_return: "0.029",
              review_outcome: "profit",
              status: "profit",
            },
          ],
        });
      }
      return jsonOk(emptyHistory);
    }
    if (url.includes("/research/evidence")) {
      return jsonOk(evidenceResponse, 201);
    }
    if (url.includes("/research/experiments")) {
      return jsonOk(experimentResponse, 201);
    }
    if (url.includes("/research/decisions")) {
      if (options.decisionError) {
        return jsonError(503, "llm_unavailable", "LLM provider is unavailable");
      }
      const payload = {
        ...decisionResponse,
        decision: { ...decisionResponse.decision, action: options.action ?? "buy" },
      };
      if (options.slowDecision) {
        await new Promise((resolve) => window.setTimeout(resolve, 10));
      }
      return jsonOk(payload, 201);
    }
    if (url.includes("/research/settlements")) {
      if (options.settlementError) {
        return jsonError(409, "invalid_state_transition", "not ready");
      }
      return jsonOk(settlementResponse, 201);
    }
    return jsonError(404, "not_found", "not found");
  };
  vi.stubGlobal("fetch", vi.fn(responseFor));
}

function jsonOk(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), { status });
}

function jsonError(status: number, code: string, message: string) {
  return new Response(
    JSON.stringify({ error: { code, message, details: {} } }),
    { status },
  );
}

function bar(tradeDate: string, close: string) {
  return {
    symbol: "000001.SZ",
    market: "CN_A",
    trade_date: tradeDate,
    open: close,
    high: close,
    low: close,
    close,
    volume: "1000",
    amount: "10000",
    adjustment: "none",
    source: "deterministic-market",
    fetched_at: "2026-07-20T08:00:00Z",
  };
}
