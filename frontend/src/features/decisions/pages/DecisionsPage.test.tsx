import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { App as AntdApp } from "antd";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { DecisionsPage } from "./DecisionsPage";

let mode: "items" | "empty" | "error" = "items";

describe("DecisionsPage", () => {
  beforeEach(() => {
    mode = "items";
    vi.stubGlobal("fetch", vi.fn(apiResponse));
  });

  it("renders Chinese decision summaries and real research links", async () => {
    renderPage();

    expect(await screen.findByRole("heading", { name: "决策" })).toBeInTheDocument();
    expect(await screen.findByText("600519")).toBeInTheDocument();
    expect(screen.getByText("买入")).toBeInTheDocument();
    expect(screen.getByText("72%")).toBeInTheDocument();
    expect(screen.getByText("guidance improved")).toBeInTheDocument();
    expect(screen.getByText("liquidity")).toBeInTheDocument();
    expect(screen.getByText("等待结算")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "查看研究" })).toHaveAttribute(
      "href",
      "/research/run_123",
    );
    expect(document.body.textContent).not.toContain("buy");
  });

  it("renders empty and error states", async () => {
    mode = "empty";
    const empty = renderPage();
    expect(await screen.findByText("暂无决策记录")).toBeInTheDocument();
    empty.unmount();

    mode = "error";
    renderPage();
    expect(
      await screen.findByText("请求失败，请稍后重试或检查系统状态。"),
    ).toBeInTheDocument();
  });
});

function renderPage() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <AntdApp>
        <MemoryRouter initialEntries={["/decisions"]}>
          <Routes>
            <Route path="/decisions" element={<DecisionsPage />} />
          </Routes>
        </MemoryRouter>
      </AntdApp>
    </QueryClientProvider>,
  );
}

async function apiResponse() {
  if (mode === "error") {
    return json({ error: { code: "request_failed", message: "failed" } }, 500);
  }
  if (mode === "empty") {
    return json({ items: [], total: 0, page: 1, page_size: 10, count: 0 });
  }
  return json({
    items: [
      {
        decision_id: "dc_123",
        research_run_id: "run_123",
        stock_name: null,
        symbol: "600519",
        market: "CN",
        decided_at: "2026-07-28T08:00:00Z",
        research_horizon: "3d",
        action: "buy",
        confidence: 0.72,
        decision_summary: "guidance improved",
        core_reason: "guidance improved",
        risks: ["liquidity"],
        invalidation_conditions: ["policy reversal"],
        trade_plan_status: "ready",
        simulated_execution_status: "waiting_settlement",
      },
    ],
    total: 1,
    page: 1,
    page_size: 10,
    count: 1,
  });
}

function json(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "content-type": "application/json" },
  });
}
