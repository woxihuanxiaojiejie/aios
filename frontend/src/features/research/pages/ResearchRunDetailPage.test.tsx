import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { App as AntdApp } from "antd";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { ResearchRunDetail } from "../types";
import { ResearchRunDetailPage } from "./ResearchRunDetailPage";

let mode: "full" | "no-decision" | "not-found" = "full";

describe("ResearchRunDetailPage", () => {
  beforeEach(() => {
    mode = "full";
    vi.stubGlobal("fetch", vi.fn(apiResponse));
  });

  it("renders persisted research chain sections and local skill failure", async () => {
    renderPage();

    expect(await screen.findByRole("heading", { name: "研究详情" })).toBeInTheDocument();
    expect(screen.getByText("1. 研究概况")).toBeInTheDocument();
    expect(screen.getByText("2. 触发原因与初始假设")).toBeInTheDocument();
    expect(screen.getByText("3. 证据材料")).toBeInTheDocument();
    expect(screen.getByText("4. 五项独立分析")).toBeInTheDocument();
    expect(screen.getByText("5. 冲突识别")).toBeInTheDocument();
    expect(screen.getByText("6. 证据复核")).toBeInTheDocument();
    expect(screen.getByText("7. 反方审查")).toBeInTheDocument();
    expect(screen.getByText("8. 讨论修订")).toBeInTheDocument();
    expect(screen.getByText("9. 最终决策")).toBeInTheDocument();
    expect(screen.getByText("10. 交易计划")).toBeInTheDocument();
    expect(screen.getByText("11. 模拟执行")).toBeInTheDocument();
    expect(screen.getByText("12. 结果结算")).toBeInTheDocument();
    expect(screen.getByText("13. 评价与复盘")).toBeInTheDocument();
    expect(screen.getByText("14. 学习建议")).toBeInTheDocument();
    expect(screen.getByText("Quarterly update")).toBeInTheDocument();
    expect(screen.getByText("技术趋势分析")).toBeInTheDocument();
    expect(screen.getByText("市场情绪分析")).toBeInTheDocument();
    expect(screen.getAllByText(/validation_error/).length).toBeGreaterThan(0);
    expect(screen.getByText("Agent report cites evidence")).toBeInTheDocument();
    expect(screen.getByText("技能观点冲突")).toBeInTheDocument();
    expect(screen.getByText("证据已确认")).toBeInTheDocument();
    expect(screen.getByText("反方提示流动性风险")).toBeInTheDocument();
    expect(screen.getByText("watch pending confirmation")).toBeInTheDocument();
    expect(screen.getAllByText("买入").length).toBeGreaterThan(0);
    expect(screen.getByText("guidance improved")).toBeInTheDocument();
    expect(screen.getAllByText("liquidity").length).toBeGreaterThan(0);
    expect(screen.getByText("8.5")).toBeInTheDocument();
    expect(screen.getAllByText("20%").length).toBeGreaterThan(0);
  });

  it("shows an explicit empty decision state without defaulting to no_trade", async () => {
    mode = "no-decision";
    renderPage();

    expect(await screen.findByText("该次研究未产生最终决策的结构化记录。"))
      .toBeInTheDocument();
    expect(screen.queryByText("no_trade")).not.toBeInTheDocument();
  });

  it("renders Research Run 404 as an error state", async () => {
    mode = "not-found";
    renderPage();

    expect(await screen.findByText("没有找到对应记录，可能已被删除或当前环境数据不一致。"))
      .toBeInTheDocument();
  });
});

function renderPage() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  render(
    <QueryClientProvider client={queryClient}>
      <AntdApp>
        <MemoryRouter initialEntries={["/research/run_123"]}>
          <Routes>
            <Route path="/research/:runId" element={<ResearchRunDetailPage />} />
          </Routes>
        </MemoryRouter>
      </AntdApp>
    </QueryClientProvider>,
  );
}

async function apiResponse() {
  if (mode === "not-found") {
    return json(
      { error: { code: "entity_not_found", message: "missing", details: {} } },
      404,
    );
  }
  const detail = detailFixture();
  if (mode === "no-decision") {
    detail.decision = null;
    detail.trade_plan = null;
  }
  return json(detail);
}

function detailFixture(): ResearchRunDetail {
  return {
    run: {
      run_id: "run_123",
      research_session_id: "rs_123",
      watchlist_item_id: "wl_123",
      symbol: "600519",
      research_window_key: "600519:2026-07-28:3",
      current_stage: "completed",
      status: "completed",
      vibe_run_id: null,
      workflow: "investment_committee",
      input_params: { provider: "deepseek" },
      raw_output_reference: null,
      failed_stage: null,
      error_type: null,
      error: null,
      finished_at: "2026-07-28T08:05:00Z",
      created_at: "2026-07-28T08:00:00Z",
      updated_at: "2026-07-28T08:05:00Z",
    },
    watchlist_item: {
      watchlist_item_id: "wl_123",
      symbol: "600519",
      market: "CN",
      note: null,
      status: "active",
      auto_research_enabled: false,
      research_horizon_days: 3,
      schedule_time: "15:00:00",
      schedule_timezone: "Asia/Shanghai",
      next_run_at: null,
      last_run_at: null,
      archived_at: null,
      created_at: "2026-07-28T08:00:00Z",
      updated_at: "2026-07-28T08:00:00Z",
    },
    session: {
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
      status: "trade_plan_ready",
      evidence_ids: ["ev_123"],
      experiment_id: null,
      cancelled_at: null,
      created_at: "2026-07-28T08:00:00Z",
      updated_at: "2026-07-28T08:05:00Z",
    },
    evidence: [
      {
        evidence_id: "ev_123",
        evidence_type: "filing",
        source: "company-report",
        symbols: ["600519"],
        published_at: "2026-07-28T08:00:00Z",
        available_at: "2026-07-28T08:00:00Z",
        summary: "updated guidance",
        reliability: 0.85,
        content_hash: "hash",
        metadata: {},
        title: "Quarterly update",
        raw_content: null,
        raw_response: null,
        source_type: null,
        source_identifier: null,
        source_url: "https://example.test/filing",
        collected_at: null,
        entities: {},
        fingerprint: null,
        credibility: null,
        freshness: null,
        processing_status: "parsed",
        parse_error: null,
        legacy_brain_evidence_id: null,
        created_at: "2026-07-28T08:00:00Z",
      },
    ],
    skill_reports: [
      report("ar_technical", "technical", "trend remains constructive", null),
      report("ar_sentiment", "sentiment", "parser failed", "validation_error"),
    ],
    hypotheses: [
      {
        hypothesis_id: "hp_123",
        research_session_id: "rs_123",
        statement: "Demand recovery supports upside",
        rationale: "Agent report cites evidence",
        direction: "bullish",
        horizon_days: 3,
        confidence: 0.65,
        supporting_report_ids: ["ar_technical"],
        supporting_evidence_ids: ["ev_123"],
        status: "proposed",
        created_at: "2026-07-28T08:01:00Z",
        updated_at: "2026-07-28T08:01:00Z",
      },
    ],
    analysis_task: {
      task_id: "at_123",
      symbol: "600519",
      market: "CN",
      asset_type: "stock",
      horizon: "3d",
      as_of: "2026-07-28T08:00:00Z",
      evidence_ids: ["ev_123"],
      user_constraints: {},
      requested_skill_ids: [
        "technical_trend",
        "sector_strength",
        "policy_impact",
        "announcement_risk",
        "market_sentiment",
      ],
      created_at: "2026-07-28T08:00:00Z",
    },
    skill_executions: [
      {
        execution_id: "se_technical",
        task_id: "at_123",
        skill_id: "technical_trend",
        skill_version: "1",
        started_at: "2026-07-28T08:01:00Z",
        finished_at: "2026-07-28T08:01:10Z",
        status: "succeeded",
        provider: "test",
        model: "deterministic",
        prompt_version: null,
        latency_ms: 10,
        retry_count: 0,
        error: null,
      },
      {
        execution_id: "se_sentiment",
        task_id: "at_123",
        skill_id: "market_sentiment",
        skill_version: "1",
        started_at: "2026-07-28T08:01:00Z",
        finished_at: "2026-07-28T08:01:10Z",
        status: "failed",
        provider: "test",
        model: "deterministic",
        prompt_version: null,
        latency_ms: 10,
        retry_count: 0,
        error: "validation_error",
      },
    ],
    skill_results: [
      {
        result_id: "sr_technical",
        execution_id: "se_technical",
        skill_id: "technical_trend",
        skill_version: "1",
        conclusion: "趋势仍然支持上涨",
        direction: "bullish",
        confidence: 0.7,
        supporting_evidence_ids: ["ev_123"],
        contradicting_evidence_ids: [],
        assumptions: ["成交维持"],
        risk_factors: ["liquidity"],
        invalid_conditions: ["跌破止损"],
        missing_information: ["行业确认"],
        reasoning_summary: "技术结构改善",
        raw_output: { source: "deterministic" },
        created_at: "2026-07-28T08:01:20Z",
      },
    ],
    discussion_result: {
      discussion_result_id: "dr_123",
      discussion_execution_id: "de_123",
      task_id: "at_123",
      skill_result_ids: ["sr_technical"],
      conflicts: [{ summary: "技能观点冲突" }],
      evidence_reviews: [{ summary: "证据已确认" }],
      counter_arguments: [{ summary: "反方提示流动性风险" }],
      revision_suggestions: [{ summary: "提高止损纪律" }],
      discussion_summary: "watch pending confirmation",
      discussion_confidence: 0.66,
      created_at: "2026-07-28T08:03:00Z",
    },
    decision_result: {
      decision_result_id: "dcr_123",
      decision_execution_id: "dce_123",
      discussion_result_id: "dr_123",
      action: "buy",
      direction: "bullish",
      confidence: 0.72,
      rationale: "guidance improved",
      supporting_reasons: [{ summary: "证据和趋势同时支持" }],
      risk_factors: [{ summary: "liquidity" }],
      rejected_directions: [],
      invalidation_conditions: ["policy reversal"],
      created_at: "2026-07-28T08:04:00Z",
    },
    discussion: {
      debates: [
        {
          debate_id: "db_123",
          research_session_id: "rs_123",
          report_ids: ["ar_technical", "ar_sentiment"],
          hypothesis_ids: ["hp_123"],
          status: "assembled",
          final_decision_id: "dc_123",
          created_at: "2026-07-28T08:02:00Z",
          updated_at: "2026-07-28T08:03:00Z",
        },
      ],
      statements: [
        {
          statement_id: "ds_123",
          debate_id: "db_123",
          agent_report_id: "ar_technical",
          hypothesis_id: "hp_123",
          stance: "support",
          reasoning: "evidence supports the hypothesis",
          evidence_ids: ["ev_123"],
          confidence_before: 0.5,
          confidence_after: 0.6,
          created_at: "2026-07-28T08:02:00Z",
        },
      ],
      proposal: {
        proposal_id: "dp_123",
        debate_id: "db_123",
        conclusion: "buy",
        confidence: 0.7,
        thesis: "watch pending confirmation",
        supporting_hypothesis_ids: ["hp_123"],
        rejected_hypothesis_ids: [],
        evidence_ids: ["ev_123"],
        risk_notes: ["position size pending"],
        created_at: "2026-07-28T08:03:00Z",
      },
      risk_review: {
        risk_review_id: "rr_123",
        proposal_id: "dp_123",
        verdict: "approve",
        final_conclusion: "buy",
        final_confidence: 0.65,
        reasons: ["risk is bounded"],
        confidence_delta: null,
        adjusted_position: null,
        condition_changes: [],
        converted_to_no_trade: false,
        research_session_id: null,
        decision_result_id: null,
        discussion_result_id: null,
        skill_result_ids: [],
        evidence_ids: [],
        supporting_arguments: [],
        opposing_arguments: [],
        created_at: "2026-07-28T08:03:00Z",
      },
      assembly: {
        assembly_id: "da_123",
        research_session_id: "rs_123",
        debate_id: "db_123",
        proposal_id: "dp_123",
        risk_review_id: "rr_123",
        decision_id: "dc_123",
        conclusion: "buy",
        report_ids: ["ar_technical", "ar_sentiment"],
        hypothesis_ids: ["hp_123"],
        evidence_ids: ["ev_123"],
        created_at: "2026-07-28T08:04:00Z",
      },
    },
    decision: {
      decision_id: "dc_123",
      experiment_id: "ex_123",
      symbol: "600519",
      action: "buy",
      horizon: "3d",
      confidence: 0.72,
      expected_return: 0.04,
      max_expected_loss: 0.02,
      evidence_ids: ["ev_123"],
      reasoning_summary: "guidance improved",
      status: "proposed",
      created_at: "2026-07-28T08:04:00Z",
      valid_until: "2026-07-31T08:04:00Z",
      research_session_id: "rs_123",
      decision_result_id: null,
      risk_review_id: null,
      direction: "bullish",
      original_direction: null,
      target_range: [10, 12],
      entry_conditions: ["breakout confirmation"],
      invalidation_conditions: ["policy reversal"],
      stop_loss: 8.5,
      position_suggestion: 0.2,
      risk_factors: ["liquidity"],
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
      planned_entry: ["breakout confirmation"],
      entry_conditions: ["breakout confirmation"],
      target: [10, 12],
      stop_loss: 8.5,
      invalidation_conditions: ["policy reversal"],
      planned_position: 0.2,
      horizon: "3d",
      expiry: "2026-07-31T08:04:00Z",
      fee_model: {},
      slippage_model: {},
      unavailable_fields: [],
      no_trade_reasons: [],
      created_at: "2026-07-28T08:04:00Z",
      updated_at: "2026-07-28T08:04:00Z",
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
      market_bar_id: "fixture:600519",
      market_data_source: "fixture",
      planned_entry: "10.00",
      executed_entry: "10.00",
      executed_exit: "10.50",
      position_size: "0.2",
      fee: "0.001",
      slippage: "0",
      realized_return: "0.05",
      exit_reason: "target",
      created_at: "2026-07-28T08:05:00Z",
      updated_at: "2026-07-28T08:05:00Z",
    },
    settlement: null,
    evaluation: null,
    review: null,
    learning_proposals: [],
  };
}

function report(
  report_id: string,
  role: string,
  summary: string,
  raw_reference: string | null,
) {
  return {
    report_id,
    research_session_id: "rs_123",
    role,
    summary,
    stance: raw_reference ? "failed" : "buy",
    confidence: raw_reference ? 0 : 0.7,
    evidence_ids: raw_reference ? [] : ["ev_123"],
    source: "brain002",
    raw_reference,
    status: "active",
    archived_at: null,
    created_at: "2026-07-28T08:01:00Z",
    updated_at: "2026-07-28T08:01:00Z",
  };
}

function json(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "content-type": "application/json" },
  });
}
