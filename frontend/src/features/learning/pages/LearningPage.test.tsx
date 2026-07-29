import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { App as AntdApp } from "antd";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { LearningPage } from "./LearningPage";

const requests: string[] = [];

describe("LearningPage", () => {
  beforeEach(() => {
    requests.length = 0;
    vi.stubGlobal("fetch", vi.fn(apiResponse));
  });

  it("renders readable learning proposals without JSON blobs", async () => {
    renderPage();

    expect(await screen.findByRole("heading", { name: "学习" })).toBeInTheDocument();
    expect(await screen.findByText("Skill 权重调整建议")).toBeInTheDocument();
    expect(screen.getByText("technical_trend")).toBeInTheDocument();
    expect(screen.getByText("weight：1")).toBeInTheDocument();
    expect(screen.getByText("1 → 1.1")).toBeInTheDocument();
    expect(screen.getByText("等待处理")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "查看详情" })).toHaveAttribute(
      "href",
      "/learning/lr_123",
    );
    expect(requests[0]).not.toContain("include_test_data=true");
    expect(document.body.textContent).not.toContain('{"weight"');
  });

  it("can include marked acceptance data on explicit request", async () => {
    renderPage();

    expect(await screen.findByText("Skill 权重调整建议")).toBeInTheDocument();
    fireEvent.mouseDown(screen.getByLabelText("测试数据"));
    fireEvent.click(await screen.findByText("显示测试数据"));

    await waitFor(() =>
      expect(requests.some((url) => url.includes("include_test_data=true"))).toBe(
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
        <MemoryRouter initialEntries={["/learning"]}>
          <Routes>
            <Route path="/learning" element={<LearningPage />} />
          </Routes>
        </MemoryRouter>
      </AntdApp>
    </QueryClientProvider>,
  );
}

async function apiResponse(input: RequestInfo | URL) {
  requests.push(String(input));
  return json({
    items: [
      {
        learning_id: "lr_123",
        review_id: "rv_123",
        learning_type: "skill_weight_update",
        target: "technical_trend",
        before: { weight: 1 },
        after: { weight: 1.1 },
        reason: "技术分析有效",
        approval_status: "pending",
        created_at: "2026-07-31T08:00:00Z",
      },
    ],
    total: 1,
    limit: 50,
    offset: 0,
  });
}

function json(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "content-type": "application/json" },
  });
}
