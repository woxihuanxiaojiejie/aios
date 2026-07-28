import { Refine } from "@refinedev/core";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { App as AntdApp } from "antd";
import { MemoryRouter, Route, Routes, useLocation, useParams } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { createAiosDataProvider } from "../../../infrastructure/refine/dataProvider";
import { ExecutionDetailPage } from "./ExecutionDetailPage";
import { ExecutionsPage } from "./ExecutionsPage";
import { LearningProposalsPage } from "./LearningProposalsPage";
import { SettlementDetailPage } from "./SettlementDetailPage";
import { SettlementsPage } from "./SettlementsPage";

const requests: string[] = [];
let mode: "items" | "empty" | "error" | "partial" = "items";

describe("Execution and settlement explorer pages", () => {
  beforeEach(() => {
    requests.length = 0;
    mode = "items";
    vi.stubGlobal("fetch", vi.fn(apiResponse));
  });

  it("renders execution list, URL filters, pagination, and settlement link", async () => {
    const user = userEvent.setup();
    renderPage("/executions");

    expect(await screen.findByText("sx_123")).toBeInTheDocument();
    expect(screen.getByText("oc_123")).toBeInTheDocument();
    await user.type(screen.getByLabelText("Symbol"), "600519");
    await user.click(screen.getByRole("button", { name: "Filter" }));

    await waitFor(() => {
      expect(requests.some((url) => url.includes("symbol=600519"))).toBe(true);
      expect(screen.getByTestId("route-search")).toHaveTextContent("symbol=600519");
    });
  });

  it("renders settlement list and links back to execution", async () => {
    renderPage("/settlements");

    expect(await screen.findByText("oc_123")).toBeInTheDocument();
    expect(screen.getByText("sx_123")).toBeInTheDocument();
    expect(screen.getByText("0.01225")).toBeInTheDocument();
  });

  it("renders detail chains and explicit missing stages", async () => {
    mode = "partial";
    renderPage("/executions/sx_123");

    expect(await screen.findByText("Simulated Execution Detail")).toBeInTheDocument();
    expect(screen.getByText("等待结算")).toBeInTheDocument();
    expect(screen.getByText("尚未生成 Evaluation")).toBeInTheDocument();
    expect(screen.getByText("尚未生成 Review")).toBeInTheDocument();
    expect(screen.getByText("尚无 Learning Proposal")).toBeInTheDocument();
  });

  it("renders settlement detail with execution link", async () => {
    renderPage("/settlements/oc_123");

    expect(await screen.findByText("Settlement Detail")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Execution" })).toBeInTheDocument();
    expect(screen.getByText("lr_123")).toBeInTheDocument();
  });

  it("renders only pending learning proposals and no write actions", async () => {
    renderPage("/learning-proposals");

    expect(await screen.findByText("lr_123")).toBeInTheDocument();
    expect(screen.queryByText("lr_approved")).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /approve|reject|apply/i })).not.toBeInTheDocument();
  });

  it("renders empty and API error states", async () => {
    mode = "empty";
    const empty = renderPage("/executions");
    expect(await screen.findByText("暂无 Simulated Execution")).toBeInTheDocument();
    empty.unmount();

    mode = "error";
    renderPage("/settlements");
    expect(await screen.findByText("Backend request failed")).toBeInTheDocument();
  });
});

function renderPage(initialEntry: string) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <AntdApp>
        <Refine
          dataProvider={createAiosDataProvider()}
          resources={[
            { name: "simulated-executions", list: "/executions" },
            { name: "settlements", list: "/settlements" },
            { name: "learnings", list: "/learning-proposals" },
          ]}
        >
          <MemoryRouter initialEntries={[initialEntry]}>
            <Routes>
              <Route path="/executions" element={<ExecutionsPage />} />
              <Route path="/executions/:executionId" element={<ExecutionDetailPage />} />
              <Route path="/settlements" element={<SettlementsPage />} />
              <Route path="/settlements/:settlementId" element={<SettlementDetailPage />} />
              <Route path="/learning-proposals" element={<LearningProposalsPage />} />
              <Route path="/research/:runId" element={<RunRoute />} />
            </Routes>
            <SearchRoute />
          </MemoryRouter>
        </Refine>
      </AntdApp>
    </QueryClientProvider>,
  );
}

function RunRoute() {
  const { runId } = useParams();
  return <span data-testid="run-route">{runId}</span>;
}

function SearchRoute() {
  const location = useLocation();
  return <span data-testid="route-search" hidden>{location.search}</span>;
}

async function apiResponse(input: RequestInfo | URL) {
  const url = String(input);
  requests.push(url);
  if (mode === "error") return jsonError(500, "Backend request failed");
  if (url.includes("/simulated-executions/sx_123")) {
    return json(mode === "partial" ? detailFixture({ settled: false }) : detailFixture());
  }
  if (url.includes("/settlements/oc_123")) return json(detailFixture());
  if (url.includes("/simulated-executions")) {
    return json(mode === "empty" ? emptyPage() : executionPage());
  }
  if (url.includes("/settlements")) {
    return json(mode === "empty" ? emptyPage() : settlementPage());
  }
  if (url.includes("/learnings")) {
    return json({
      items: [learning(), { ...learning(), learning_id: "lr_approved", approval_status: "approved" }],
      total: 2,
      limit: 50,
      offset: 0,
      count: 2,
    });
  }
  return json(emptyPage());
}

function emptyPage() {
  return { items: [], total: 0, page: 1, page_size: 10, count: 0 };
}

function executionPage() {
  return {
    items: [
      {
        execution_id: "sx_123",
        symbol: "600519",
        market: "CN",
        side: "bullish",
        action: "bullish",
        quantity: "0.25",
        simulated_price: "10.00",
        status: "waiting_settlement",
        created_at: "2026-07-28T08:00:00Z",
        research_run_id: "run_123",
        research_session_id: "rs_123",
        decision_id: "dc_123",
        trade_plan_id: "tp_123",
        settlement_id: "oc_123",
      },
    ],
    total: 1,
    page: 1,
    page_size: 10,
    count: 1,
  };
}

function settlementPage() {
  return {
    items: [
      {
        settlement_id: "oc_123",
        execution_id: "sx_123",
        trade_plan_id: "tp_123",
        decision_id: "dc_123",
        research_session_id: "rs_123",
        research_run_id: "run_123",
        symbol: "600519",
        market: "CN",
        status: "settled",
        entry_price: "10.00",
        exit_price: "10.50",
        return_rate: "0.049",
        pnl: "0.01225",
        settled_at: "2026-07-28T09:00:00Z",
        created_at: "2026-07-28T09:00:00Z",
      },
    ],
    total: 1,
    page: 1,
    page_size: 10,
    count: 1,
  };
}

function detailFixture({ settled = true } = {}) {
  return {
    research_run: {
      run_id: "run_123",
      research_session_id: "rs_123",
      watchlist_item_id: "wl_123",
      symbol: "600519",
      research_window_key: null,
      current_stage: "completed",
      status: "completed",
      vibe_run_id: null,
      workflow: "investment_committee",
      input_params: {},
      raw_output_reference: null,
      failed_stage: null,
      error_type: null,
      error: null,
      finished_at: "2026-07-28T09:00:00Z",
      created_at: "2026-07-28T08:00:00Z",
      updated_at: "2026-07-28T09:00:00Z",
    },
    research_session: {
      research_session_id: "rs_123",
      scope: {
        watchlist_item_id: "wl_123",
        symbol: "600519",
        market: "CN",
        watchlist_note_snapshot: null,
        horizon_days: 3,
        as_of: "2026-07-28T08:00:00Z",
        valid_until: "2026-07-31T08:00:00Z",
      },
      status: "completed",
      evidence_ids: [],
      experiment_id: "ex_123",
      cancelled_at: null,
      created_at: "2026-07-28T08:00:00Z",
      updated_at: "2026-07-28T09:00:00Z",
    },
    decision: {
      decision_id: "dc_123",
      experiment_id: "ex_123",
      symbol: "600519",
      action: "buy",
      horizon: "3d",
      confidence: 0.7,
      expected_return: 0.04,
      max_expected_loss: 0.02,
      evidence_ids: [],
      reasoning_summary: "real persisted decision",
      status: "proposed",
      created_at: "2026-07-28T08:10:00Z",
      valid_until: "2026-07-31T08:10:00Z",
      research_session_id: "rs_123",
      decision_result_id: null,
      risk_review_id: null,
      direction: "bullish",
      original_direction: null,
      target_range: [10, 12],
      entry_conditions: ["10.00"],
      invalidation_conditions: ["close below 9.50"],
      stop_loss: 9.5,
      position_suggestion: 0.25,
      risk_factors: [],
      supporting_skill_ids: [],
      dissenting_opinions: [],
      market_regime: null,
      generated_at: null,
      planned_settlement_at: null,
      unavailable_fields: [],
      downgrade_reasons: [],
    },
    trade_plan: {
      trade_plan_id: "tp_123",
      decision_id: "dc_123",
      research_session_id: "rs_123",
      symbol: "600519",
      direction: "bullish",
      status: "ready",
      planned_entry: ["10.00"],
      entry_conditions: ["10.00"],
      target: [10, 12],
      stop_loss: 9.5,
      invalidation_conditions: ["close below 9.50"],
      planned_position: 0.25,
      horizon: "3d",
      expiry: "2026-07-31T08:10:00Z",
      fee_model: {},
      slippage_model: {},
      no_trade_reasons: [],
      unavailable_fields: [],
      created_at: "2026-07-28T08:11:00Z",
      updated_at: "2026-07-28T08:11:00Z",
    },
    simulated_execution: {
      execution_id: "sx_123",
      trade_plan_id: "tp_123",
      decision_id: "dc_123",
      research_session_id: "rs_123",
      symbol: "600519",
      direction: "bullish",
      execution_status: "waiting_settlement",
      execution_date: "2026-07-28T00:00:00Z",
      market_bar_id: "bar",
      market_data_source: "fixture",
      planned_entry: "10.00",
      executed_entry: "10.00",
      executed_exit: "10.50",
      position_size: "0.25",
      fee: "0.001",
      slippage: "0",
      realized_return: "0.049",
      exit_reason: "target",
      created_at: "2026-07-28T08:12:00Z",
      updated_at: "2026-07-28T08:12:00Z",
    },
    settlement: settled ? {
      outcome_id: "oc_123",
      decision_id: "dc_123",
      experiment_id: "ex_123",
      symbol: "600519",
      horizon: "3d",
      horizon_semantics: "trade_plan_expiry",
      observation_started_at: "2026-07-28T08:11:00Z",
      observation_ended_at: "2026-07-31T08:11:00Z",
      entry_price: "10.00",
      exit_price: "10.50",
      realized_return: "0.049",
      maximum_adverse_excursion: "-0.01",
      maximum_favorable_excursion: "0.05",
      market_data_source: "fixture",
      settled_at: "2026-07-28T09:00:00Z",
      status: "settled",
      execution_id: "sx_123",
      trade_plan_id: "tp_123",
      research_session_id: "rs_123",
      pnl: "0.01225",
      return_rate: "0.049",
      holding_days: 0,
      exit_reason: "target",
      max_drawdown: "-0.01",
      max_favorable_excursion: "0.05",
      created_at: "2026-07-28T09:00:00Z",
    } : null,
    evaluation: settled ? {
      evaluation_id: "de_123",
      decision_id: "dc_123",
      outcome_id: "oc_123",
      experiment_id: "ex_123",
      directional_result: "correct",
      return_result: "met",
      risk_result: "within_limit",
      final_result: "pass",
      evaluation_rules_version: "simulated-execution-evaluation-v1",
      evaluated_at: "2026-07-28T09:00:00Z",
      explanation: "fixed deterministic execution evaluation",
      prediction_accuracy: "good",
      timing_accuracy: "good",
      risk_control: "good",
      execution_quality: "good",
      created_at: "2026-07-28T09:00:00Z",
    } : null,
    review: settled ? {
      review_id: "rv_123",
      decision_id: "dc_123",
      actual_return: "0.049",
      direction_correct: true,
      risk_limit_breached: false,
      outcome: "profit",
      cause_tags: ["simulated_execution"],
      review_summary: "deterministic review",
      success_reasons: [],
      failure_reasons: [],
      effective_evidence_ids: [],
      effective_skill_ids: [],
      mistaken_judgement_ids: [],
      reference_ids: {},
      created_at: "2026-07-28T09:00:00Z",
    } : null,
    learning_proposals: settled ? [learning()] : [],
  };
}

function learning() {
  return {
    learning_id: "lr_123",
    review_id: "rv_123",
    learning_type: "skill_weight_update",
    target: "simulated_execution_review",
    before: { status: "current" },
    after: { status: "proposal_only" },
    reason: "proposal only",
    approval_status: "pending",
    created_at: "2026-07-28T09:00:00Z",
  };
}

function json(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "content-type": "application/json" },
  });
}

function jsonError(status: number, message: string) {
  return json({ error: { code: "request_failed", message, details: {} } }, status);
}
