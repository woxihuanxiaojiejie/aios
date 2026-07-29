import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { App as AntdApp } from "antd";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ReviewsPage } from "./ReviewsPage";

let mode: "items" | "empty" | "error" = "items";

describe("ReviewsPage", () => {
  beforeEach(() => {
    mode = "items";
    vi.stubGlobal("fetch", vi.fn(apiResponse));
  });

  it("renders review summaries in Chinese", async () => {
    renderPage();

    expect(await screen.findByRole("heading", { name: "复盘" })).toBeInTheDocument();
    expect(await screen.findByText("600519")).toBeInTheDocument();
    expect(screen.getByText("买入")).toBeInTheDocument();
    expect(screen.getByText("5%")).toBeInTheDocument();
    expect(screen.getByText("正确")).toBeInTheDocument();
    expect(screen.getByText("风控有效")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "查看复盘" })).toHaveAttribute(
      "href",
      "/reviews/oc_123",
    );
  });

  it("renders empty and error states", async () => {
    mode = "empty";
    const empty = renderPage();
    expect(await screen.findByText("暂无复盘记录")).toBeInTheDocument();
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
        <MemoryRouter initialEntries={["/reviews"]}>
          <Routes>
            <Route path="/reviews" element={<ReviewsPage />} />
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
        settlement_id: "oc_123",
        research_run_id: "run_123",
        stock_name: null,
        symbol: "600519",
        market: "CN",
        original_decision: "buy",
        research_horizon: "3d",
        execution_time: "2026-07-28T08:00:00Z",
        entry_price: "10",
        exit_price: "10.5",
        return_rate: "0.05",
        pnl: "0.1",
        directional_result: "correct",
        return_result: "met",
        risk_result: "within_limit",
        main_error: null,
        learning_proposal_status: "pending",
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
