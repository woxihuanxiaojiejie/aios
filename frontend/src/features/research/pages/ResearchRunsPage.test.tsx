import { Refine } from "@refinedev/core";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { App as AntdApp } from "antd";
import { MemoryRouter, Route, Routes, useLocation, useParams } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { createAiosDataProvider } from "../../../infrastructure/refine/dataProvider";
import { ResearchRunsPage } from "./ResearchRunsPage";

const requests: string[] = [];
let mode: "items" | "empty" | "error" = "items";

describe("ResearchRunsPage", () => {
  beforeEach(() => {
    requests.length = 0;
    mode = "items";
    vi.stubGlobal("fetch", vi.fn(apiResponse));
  });

  it("loads research runs through Refine list data and opens detail", async () => {
    const user = userEvent.setup();
    renderPage();

    expect(await screen.findByText("run_1234567890")).toBeInTheDocument();
    expect(screen.getByText("600519")).toBeInTheDocument();
    expect(screen.getByText("buy")).toBeInTheDocument();

    const row = screen.getByText("run_1234567890").closest("tr");
    expect(row).not.toBeNull();
    await user.click(within(row as HTMLTableRowElement).getByRole("button", { name: "详情" }));

    await waitFor(() => expect(screen.getByTestId("detail-route")).toHaveTextContent("run_1234567890"));
  });

  it("shows empty state", async () => {
    mode = "empty";
    renderPage();

    expect(await screen.findByText("暂无 Research Run")).toBeInTheDocument();
  });

  it("shows API error state", async () => {
    mode = "error";
    renderPage("/research?symbol=ERR");

    expect(await screen.findByText(/Backend request failed/i)).toBeInTheDocument();
  });

  it("keeps filter and pagination state in the URL", async () => {
    const user = userEvent.setup();
    renderPage();

    await user.type(await screen.findByLabelText("股票代码"), "600519");
    await user.click(screen.getByRole("button", { name: "筛选" }));

    await waitFor(() => {
      expect(requests.some((url) => url.includes("symbol=600519"))).toBe(true);
      expect(screen.getByTestId("search-route")).toHaveTextContent("symbol=600519");
    });
  });
});

function renderPage(initialEntry = "/research") {
  return render(tree(initialEntry));
}

function tree(initialEntry: string) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return (
    <QueryClientProvider client={queryClient}>
      <AntdApp>
        <Refine
          dataProvider={createAiosDataProvider()}
          resources={[{ name: "research-runs", list: "/research" }]}
          options={{ syncWithLocation: false }}
        >
          <MemoryRouter initialEntries={[initialEntry]}>
            <Routes>
              <Route path="/research" element={<ResearchRunsPage />} />
              <Route path="/research/:runId" element={<DetailRoute />} />
            </Routes>
            <SearchRoute />
          </MemoryRouter>
        </Refine>
      </AntdApp>
    </QueryClientProvider>
  );
}

function DetailRoute() {
  const { runId } = useParams();
  return <span data-testid="detail-route">{runId}</span>;
}

function SearchRoute() {
  const location = useLocation();
  return <span data-testid="search-route" hidden>{location.search}</span>;
}

async function apiResponse(input: RequestInfo | URL) {
  const url = String(input);
  requests.push(url);
  if (mode === "error") {
    return jsonError(500, "request_failed", "Backend request failed");
  }
  if (mode === "empty") {
    return json({ items: [], total: 0, limit: 10, offset: 0, count: 0 });
  }
  return json({
    items: [
      {
        run_id: "run_1234567890",
        research_session_id: "rs_123",
        watchlist_item_id: "wl_123",
        symbol: "600519",
        market: "CN",
        trigger_method: "investment_committee",
        research_window_key: "600519:2026-07-28:3",
        current_stage: "completed",
        status: "completed",
        vibe_run_id: null,
        workflow: "investment_committee",
        input_params: { horizon_days: 3 },
        raw_output_reference: null,
        failed_stage: null,
        error_type: null,
        error: null,
        final_decision: "buy",
        confidence: 0.72,
        finished_at: "2026-07-28T08:05:00Z",
        created_at: "2026-07-28T08:00:00Z",
        updated_at: "2026-07-28T08:05:00Z",
      },
    ],
    total: 1,
    limit: 10,
    offset: 0,
    count: 1,
  });
}

function json(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "content-type": "application/json" },
  });
}

function jsonError(status: number, code: string, message: string) {
  return json({ error: { code, message, details: {} } }, status);
}
