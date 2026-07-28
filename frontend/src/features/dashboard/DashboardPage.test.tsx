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

  it("renders summary counts, attention rows, recent results, and real detail links", async () => {
    renderPage();

    expect(await screen.findByRole("heading", { name: "AIOS Results Home" })).toBeInTheDocument();
    expect(screen.getByText("Research Runs 总数")).toBeInTheDocument();
    expect(screen.getByText("12")).toBeInTheDocument();
    expect(screen.getByText("暂无足够数据")).toBeInTheDocument();
    expect(screen.getByText("missing_trade_plan")).toBeInTheDocument();
    expect(screen.getByText("Decision 已生成")).toBeInTheDocument();
    expect(screen.getByText("Trade Plan")).toBeInTheDocument();
    expect(screen.getAllByText("buy").length).toBeGreaterThan(0);
    expect(screen.getByText("ready")).toBeInTheDocument();
    expect(screen.getByText("fixed deterministic execution evaluation")).toBeInTheDocument();
    expect(screen.getAllByRole("link", { name: "run_123" })[0]).toHaveAttribute(
      "href",
      "/research/run_123",
    );
    expect(screen.getByRole("link", { name: "oc_123" })).toHaveAttribute(
      "href",
      "/settlements/oc_123",
    );
    expect(document.body.textContent).not.toMatch(/echarts|lightweight-charts/i);
  });

  it("renders empty and error states without manufacturing zeros for null performance", async () => {
    mode = "empty";
    const empty = renderPage();
    expect(await screen.findAllByText("暂无需要处理的事项")).toHaveLength(1);
    expect(screen.getByText("暂无最近研究结果")).toBeInTheDocument();
    expect(screen.getByText("暂无最近结算结果")).toBeInTheDocument();
    expect(screen.getByText("暂无足够数据")).toBeInTheDocument();
    empty.unmount();

    mode = "error";
    renderPage();
    expect(await screen.findByText("Dashboard failed")).toBeInTheDocument();
  });

  it("renders a loading state while the summary is pending", () => {
    mode = "loading";
    renderPage();

    expect(document.querySelector(".ant-skeleton")).toBeInTheDocument();
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
  if (!url.endsWith("/dashboard/summary")) return json({});
  if (mode === "loading") return new Promise(() => undefined);
  if (mode === "error") {
    return json({ error: { code: "request_failed", message: "Dashboard failed", details: {} } }, 500);
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
        current_stage: "Decision 已生成",
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
        evaluation_summary: "fixed deterministic execution evaluation",
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

function json(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "content-type": "application/json" },
  });
}
