import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen } from "@testing-library/react";
import { App as AntdApp } from "antd";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { SystemStatusPage } from "./SystemStatusPage";

let mode: "healthy" | "error" | "loading" = "healthy";
let requests = 0;

describe("SystemStatusPage", () => {
  beforeEach(() => {
    mode = "healthy";
    requests = 0;
    vi.stubGlobal("fetch", vi.fn(apiResponse));
  });

  it("renders runtime status, pending work, providers, links, and no write controls", async () => {
    renderPage();

    expect(await screen.findByRole("heading", { name: "系统运行状态" })).toBeInTheDocument();
    expect(screen.getByText("系统总体状态")).toBeInTheDocument();
    expect(screen.getByText("核心组件")).toBeInTheDocument();
    expect(screen.getByText("调度任务")).toBeInTheDocument();
    expect(screen.getByText("待处理工作")).toBeInTheDocument();
    expect(screen.getByText("数据提供方与大模型提供方")).toBeInTheDocument();
    expect(screen.getByText("应用")).toBeInTheDocument();
    expect(screen.getByText("数据库")).toBeInTheDocument();
    expect(screen.getByText("调度器")).toBeInTheDocument();
    expect(screen.getByText("自动研究扫描")).toBeInTheDocument();
    expect(screen.getByText("自动结算扫描")).toBeInTheDocument();
    expect(screen.getByText("deepseek")).toBeInTheDocument();
    expect(screen.getAllByRole("link", { name: "进入研究" })[0]).toHaveAttribute("href", "/research");
    expect(screen.getByRole("link", { name: "进入复盘" })).toHaveAttribute("href", "/reviews");
    expect(screen.queryByRole("button", { name: /restart|start|stop|approve|reject|apply/i })).not.toBeInTheDocument();
    expect(document.body.textContent).not.toMatch(/api_key|secret|token|password|echarts|chart\.js|recharts/i);
  });

  it("refreshes by reloading the read-only status API", async () => {
    renderPage();

    expect(await screen.findByText("调度器心跳正常。")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /刷\s*新/ }));

    expect(await screen.findByText("调度器心跳正常。")).toBeInTheDocument();
    expect(requests).toBeGreaterThanOrEqual(2);
  });

  it("renders loading and API error states", async () => {
    mode = "loading";
    const loading = renderPage();
    expect(document.querySelector(".ant-skeleton")).toBeInTheDocument();
    loading.unmount();

    mode = "error";
    renderPage();
    expect(await screen.findByText("系统运行状态读取失败，请稍后重试。")).toBeInTheDocument();
  });
});

function renderPage() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <AntdApp>
        <MemoryRouter initialEntries={["/system"]}>
          <Routes>
            <Route path="/system" element={<SystemStatusPage />} />
          </Routes>
        </MemoryRouter>
      </AntdApp>
    </QueryClientProvider>,
  );
}

async function apiResponse(input: RequestInfo | URL) {
  const url = String(input);
  if (!url.endsWith("/system/status")) return json({});
  requests += 1;
  if (mode === "loading") return new Promise(() => undefined);
  if (mode === "error") {
    return json({ error: { code: "request_failed", message: "System status failed", details: {} } }, 500);
  }
  return json(systemStatus());
}

function systemStatus() {
  return {
    generated_at: "2026-07-28T08:00:00Z",
    overall_status: "healthy",
    application: {
      status: "healthy",
      name: "AIOS",
      version: "0.1.0",
      commit: "abc123",
      environment: "test",
      started_at: "2026-07-28T07:59:00Z",
      checked_at: "2026-07-28T08:00:00Z",
      message: null,
    },
    database: {
      status: "healthy",
      backend: "postgresql",
      checked_at: "2026-07-28T08:00:00Z",
      latency_ms: 3,
      message: "select 1 ok",
    },
    scheduler: {
      status: "healthy",
      running: true,
      last_heartbeat_at: "2026-07-28T07:59:30Z",
      heartbeat_age_seconds: 30,
      message: "scheduler heartbeat is current",
    },
    jobs: {
      research_due_scan: {
        status: "healthy",
        enabled: true,
        last_started_at: "2026-07-28T07:58:00Z",
        last_completed_at: "2026-07-28T07:58:05Z",
        last_result: "processed=2; succeeded=2; failed=0",
        last_error: null,
        processed_count: 2,
        success_count: 2,
        failure_count: 0,
      },
      settlement_due_scan: {
        status: "healthy",
        enabled: true,
        last_started_at: "2026-07-28T07:59:00Z",
        last_completed_at: "2026-07-28T07:59:02Z",
        last_result: "processed=1; succeeded=1; failed=0",
        last_error: null,
        processed_count: 1,
        success_count: 1,
        failure_count: 0,
      },
    },
    queues: {
      research_due: 4,
      settlement_due: 1,
      failed_research_runs: 0,
      resumable_research_runs: 0,
    },
    providers: [
      {
        provider: "deepseek",
        model: "deepseek/deepseek-chat",
        configured: true,
        status: "healthy",
        message: "local config valid",
      },
    ],
    issues: [],
  };
}

function json(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "content-type": "application/json" },
  });
}
