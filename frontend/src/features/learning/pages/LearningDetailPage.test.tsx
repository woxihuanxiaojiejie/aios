import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { App as AntdApp } from "antd";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { LearningDetailPage } from "./LearningDetailPage";

const requests: string[] = [];

describe("LearningDetailPage", () => {
  beforeEach(() => {
    requests.length = 0;
    vi.stubGlobal("fetch", vi.fn(apiResponse));
  });

  it("renders readable detail and defers proposal with confirmation", async () => {
    const user = userEvent.setup();
    renderPage();

    expect(await screen.findByRole("heading", { name: "学习建议详情" }))
      .toBeInTheDocument();
    expect(screen.getByText("Skill 权重调整建议")).toBeInTheDocument();
    expect(screen.getByText("权重 1")).toBeInTheDocument();
    expect(screen.getByText("权重 1.1")).toBeInTheDocument();
    expect(screen.getByText("1 -> 1.1")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "查看研究" })).toHaveAttribute(
      "href",
      "/research/run_123",
    );
    expect(screen.getByRole("button", { name: /批\s*准/ })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /拒\s*绝/ })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /暂\s*缓/ })).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /暂\s*缓/ }));
    const confirmButtons = await screen.findAllByRole("button", {
      name: /暂\s*缓/,
    });
    const confirmButton = confirmButtons[confirmButtons.length - 1];
    expect(confirmButton).toBeDefined();
    await user.click(confirmButton);

    await waitFor(() =>
      expect(requests.some((url) => url.endsWith("/learnings/lr_123/defer"))).toBe(
        true,
      ),
    );
  });
});

function renderPage() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  render(
    <QueryClientProvider client={queryClient}>
      <AntdApp>
        <MemoryRouter initialEntries={["/learning/lr_123"]}>
          <Routes>
            <Route path="/learning/:learningId" element={<LearningDetailPage />} />
          </Routes>
        </MemoryRouter>
      </AntdApp>
    </QueryClientProvider>,
  );
}

async function apiResponse(input: RequestInfo | URL) {
  const url = String(input);
  requests.push(url);
  if (url.endsWith("/defer")) return json({ ...learning(), approval_status: "deferred" });
  if (url.endsWith("/approve") || url.endsWith("/reject")) return json(learning());
  return json({
    learning: learning(),
    review: {
      review_id: "rv_123",
      decision_id: "dc_123",
      actual_return: "0.05",
      direction_correct: true,
      risk_limit_breached: false,
      outcome: "profit",
      cause_tags: ["evidence"],
      review_summary: "固定复盘摘要",
      success_reasons: ["趋势判断正确"],
      failure_reasons: [],
      effective_evidence_ids: ["ev_123"],
      effective_skill_ids: ["technical_trend"],
      mistaken_judgement_ids: [],
      reference_ids: {},
      created_at: "2026-07-31T08:00:00Z",
    },
    evaluation: {
      evaluation_id: "evl_123",
      decision_id: "dc_123",
      outcome_id: "oc_123",
      experiment_id: "ex_123",
      directional_result: "correct",
      return_result: "met",
      risk_result: "within_limit",
      final_result: "pass",
      evaluation_rules_version: "v1",
      evaluated_at: "2026-07-31T08:00:00Z",
      explanation: "方向和收益均符合预期",
      prediction_accuracy: null,
      timing_accuracy: null,
      risk_control: null,
      execution_quality: null,
      created_at: "2026-07-31T08:00:00Z",
    },
    settlement: {
      outcome_id: "oc_123",
      decision_id: "dc_123",
      experiment_id: "ex_123",
      symbol: "600519",
      horizon: "3d",
      horizon_semantics: "calendar",
      observation_started_at: "2026-07-28T08:00:00Z",
      observation_ended_at: "2026-07-31T08:00:00Z",
      entry_price: "10",
      exit_price: "10.5",
      realized_return: "0.05",
      maximum_adverse_excursion: "0.01",
      maximum_favorable_excursion: "0.08",
      market_data_source: "fixture",
      settled_at: "2026-07-31T08:00:00Z",
      status: "settled",
      execution_id: "sx_123",
      trade_plan_id: "tp_123",
      research_session_id: "rs_123",
      pnl: "0.1",
      return_rate: "0.05",
      holding_days: 3,
      exit_reason: "target",
      max_drawdown: "0.01",
      max_favorable_excursion: "0.08",
      created_at: "2026-07-31T08:00:00Z",
    },
    simulated_execution: null,
    decision: {
      decision_id: "dc_123",
      experiment_id: "ex_123",
      symbol: "600519",
      action: "buy",
      horizon: "3d",
      confidence: 0.72,
      expected_return: 0.04,
      max_expected_loss: 0.02,
      evidence_ids: [],
      reasoning_summary: "guidance improved",
      entry_conditions: [],
      invalidation_conditions: [],
      risk_factors: [],
      status: "proposed",
      created_at: "2026-07-28T08:04:00Z",
      valid_until: "2026-07-31T08:04:00Z",
      research_session_id: "rs_123",
      decision_result_id: null,
      risk_review_id: null,
      direction: "bullish",
      original_direction: null,
      target_range: [10, 12],
      stop_loss: 8.5,
      position_suggestion: 0.2,
      supporting_skill_ids: [],
      dissenting_opinions: [],
      market_regime: null,
      generated_at: null,
      planned_settlement_at: null,
      unavailable_fields: [],
      downgrade_reasons: [],
    },
    research_run: {
      run_id: "run_123",
      research_session_id: "rs_123",
      watchlist_item_id: "wl_123",
      symbol: "600519",
      research_window_key: null,
      current_stage: "reviewed",
      status: "completed",
      vibe_run_id: null,
      workflow: "investment_committee",
      input_params: {},
      raw_output_reference: null,
      failed_stage: null,
      error_type: null,
      error: null,
      finished_at: "2026-07-28T08:05:00Z",
      created_at: "2026-07-28T08:00:00Z",
      updated_at: "2026-07-28T08:05:00Z",
    },
    research_session: null,
    current_value_summary: "权重 1",
    proposed_value_summary: "权重 1.1",
    change_summary: "1 -> 1.1",
    technical_details: {
      before: { weight: 1 },
      after: { weight: 1.1 },
      expected_effect: "提升有效技能权重",
      risks: "样本量有限",
      sample_size: 1,
    },
  });
}

function learning() {
  return {
    learning_id: "lr_123",
    review_id: "rv_123",
    learning_type: "skill_weight_update",
    target: "technical_trend",
    before: { weight: 1 },
    after: { weight: 1.1 },
    reason: "技术分析有效",
    approval_status: "pending",
    created_at: "2026-07-31T08:00:00Z",
  };
}

function json(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "content-type": "application/json" },
  });
}
