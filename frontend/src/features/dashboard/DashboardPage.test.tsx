import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { App as AntdApp } from "antd";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { DashboardPage } from "./DashboardPage";

let mode: "items" | "empty" | "error" | "loading" = "items";

describe("DashboardPage", () => {
  beforeEach(() => {
    mode = "items";
    vi.stubGlobal("fetch", vi.fn(apiResponse));
  });

  it("renders the Chinese business home instead of the manual workbench", async () => {
    renderPage();

    expect(
      await screen.findByRole("heading", { name: "AIOS 工作台首页" }),
    ).toBeInTheDocument();
    expect(screen.getByText("今日待办")).toBeInTheDocument();
    expect(screen.getByText("最新研究结果")).toBeInTheDocument();
    expect(screen.getByText("待处理异常")).toBeInTheDocument();
    expect(screen.getByText("最近复盘结果")).toBeInTheDocument();
    expect(screen.queryByText("AIOS 人工验收工作台")).not.toBeInTheDocument();
    expect(screen.queryByText("新增股票")).not.toBeInTheDocument();
    expect(screen.queryByText("创建证据")).not.toBeInTheDocument();
    expect(screen.queryByText("Research Runs")).not.toBeInTheDocument();
    expect(screen.getByText("等待交易计划")).toBeInTheDocument();
    expect(screen.getAllByText("买入").length).toBeGreaterThan(0);
    expect(screen.getAllByText("结果结算")[0]).toBeInTheDocument();
    expect(screen.getByText("固定验收复盘摘要")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "进入系统运行状态" })).toHaveAttribute(
      "href",
      "/system",
    );
    expect(screen.getByRole("link", { name: "查看研究" })).toHaveAttribute(
      "href",
      "/research/run_123",
    );
    expect(screen.getByRole("link", { name: "查看复盘" })).toHaveAttribute(
      "href",
      "/reviews/oc_123",
    );
    expect(document.body.textContent).not.toMatch(/echarts|lightweight-charts/i);
  });

  it("renders empty and error states in Chinese", async () => {
    mode = "empty";
    const empty = renderPage();
    expect(await screen.findByText("暂无待处理异常")).toBeInTheDocument();
    expect(screen.getByText("暂无最近研究结果")).toBeInTheDocument();
    expect(screen.getByText("暂无最近复盘结果")).toBeInTheDocument();
    empty.unmount();

    mode = "error";
    renderPage();
    expect(
      await screen.findByText("请求失败，请稍后重试或检查系统状态。"),
    ).toBeInTheDocument();
  });

  it("renders a loading state while the summary is pending", () => {
    mode = "loading";
    renderPage();

    expect(screen.getByText("正在加载...")).toBeInTheDocument();
  });
});

function renderPage() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <AntdApp>
        <MemoryRouter initialEntries={["/dashboard"]}>
          <Routes>
            <Route path="/dashboard" element={<DashboardPage />} />
          </Routes>
        </MemoryRouter>
      </AntdApp>
    </QueryClientProvider>,
  );
}

async function apiResponse(input: RequestInfo | URL) {
  const url = String(input);
  if (url.endsWith("/system/status")) return json(systemStatus());
  if (!url.endsWith("/dashboard/summary")) return json({});
  if (mode === "loading") return new Promise(() => undefined);
  if (mode === "error") {
    return json(
      {
        error: {
          code: "request_failed",
          message: "Dashboard failed",
          details: {},
        },
      },
      500,
    );
  }
  if (mode === "empty") return json(emptySummary());
  return json({
    generated_at: "2026-07-28T08:00:00Z",
    counts: {
      research_runs: 12,
      completed_research_runs: 8,
      failed_or_resumable_research_runs: 2,
      decisions: 7,
      trade_plans: 4,
      simulated_executions: 3,
      settlements: 2,
      pending_learning_proposals: 1,
      positive_settlements: 1,
      negative_settlements: 1,
    },
    performance: { average_return: null },
    attention_required: [
      {
        type: "missing_trade_plan",
        symbol: "600519",
        market: "CN",
        current_stage: "Decision",
        missing_stage: "Trade Plan",
        created_at: "2026-07-28T08:00:00Z",
        detail_path: "/research/run_123",
        detail_id: "run_123",
      },
    ],
    recent_research: [
      {
        run_id: "run_123",
        created_at: "2026-07-28T08:00:00Z",
        symbol: "600519",
        market: "CN",
        research_status: "completed",
        decision_action: "buy",
        confidence: 0.72,
        trade_plan_status: "ready",
        current_loop_stage: "Settlement",
      },
    ],
    recent_settlements: [
      {
        settlement_id: "oc_123",
        settled_at: "2026-07-28T09:00:00Z",
        symbol: "600519",
        market: "CN",
        decision_action: "buy",
        entry_price: "10.00",
        exit_price: "10.50",
        return_rate: "0.049",
        pnl: "0.01225",
        evaluation_summary: "固定验收复盘摘要",
        review_status: "profit",
      },
    ],
  });
}

function emptySummary() {
  return {
    generated_at: "2026-07-28T08:00:00Z",
    counts: {
      research_runs: 0,
      completed_research_runs: 0,
      failed_or_resumable_research_runs: 0,
      decisions: 0,
      trade_plans: 0,
      simulated_executions: 0,
      settlements: 0,
      pending_learning_proposals: 0,
      positive_settlements: 0,
      negative_settlements: 0,
    },
    performance: { average_return: null },
    attention_required: [],
    recent_research: [],
    recent_settlements: [],
  };
}

function systemStatus() {
  return {
    generated_at: "2026-07-28T08:00:00Z",
    overall_status: "healthy",
    application: {
      status: "healthy",
      name: "AIOS",
      version: "0.1.0",
      commit: null,
      environment: null,
      started_at: null,
      checked_at: "2026-07-28T08:00:00Z",
      message: null,
    },
    database: {
      status: "healthy",
      backend: "in_memory",
      checked_at: "2026-07-28T08:00:00Z",
      latency_ms: 0,
      message: null,
    },
    scheduler: {
      status: "healthy",
      running: true,
      last_heartbeat_at: "2026-07-28T08:00:00Z",
      heartbeat_age_seconds: 1,
      message: null,
    },
    jobs: {},
    queues: {
      research_due: 1,
      settlement_due: 2,
      failed_research_runs: 1,
      resumable_research_runs: 1,
    },
    providers: [],
    issues: [],
  };
}

function json(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "content-type": "application/json" },
  });
}
