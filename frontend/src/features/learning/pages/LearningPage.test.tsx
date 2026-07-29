import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { App as AntdApp } from "antd";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { LearningPage } from "./LearningPage";

describe("LearningPage", () => {
  beforeEach(() => {
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
    expect(document.body.textContent).not.toContain('{"weight"');
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

async function apiResponse() {
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
