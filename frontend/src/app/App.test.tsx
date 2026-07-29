import { render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { App } from "./App";

describe("App routing", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", vi.fn(apiResponse));
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    window.history.replaceState({}, "", "/");
  });

  it("redirects / to the dashboard page", async () => {
    window.history.pushState({}, "", "/");

    render(<App />);

    await waitFor(() => expect(window.location.pathname).toBe("/dashboard"));
    expect(
      await screen.findByRole("heading", { name: "AIOS Results Summary" }),
    ).toBeInTheDocument();
    expect(screen.queryByText("AIOS 人工验收工作台")).not.toBeInTheDocument();
  });

  it("serves /dashboard and keeps dashboard first in navigation", async () => {
    window.history.pushState({}, "", "/dashboard");

    render(<App />);

    expect(await screen.findByRole("heading", { name: "AIOS Results Summary" })).toBeInTheDocument();
    expect(screen.queryByText("新增股票")).not.toBeInTheDocument();
    expect(screen.queryByText("创建证据")).not.toBeInTheDocument();
    const navItems = screen.getAllByRole("menuitem").map((item) => item.textContent);
    expect(navItems).toEqual([
      "Dashboard",
      "Research",
      "Executions",
      "Settlements",
      "Learning Proposals",
      "System",
    ]);
  });

  it("serves the Research Runs list at /research", async () => {
    window.history.pushState({}, "", "/research");

    render(<App />);

    expect(await screen.findByText("Research Runs")).toBeInTheDocument();
  });

  it("keeps the existing ResearchWorkbench available at /research/new", async () => {
    window.history.pushState({}, "", "/research/new");

    render(<App />);

    expect(
      await screen.findByText("AIOS 人工验收工作台"),
    ).toBeInTheDocument();
    expect(screen.getByText("新增股票")).toBeInTheDocument();
    expect(screen.getByText("创建证据")).toBeInTheDocument();
  });

  it("serves the execution and settlement explorer routes", async () => {
    window.history.pushState({}, "", "/executions");
    const { unmount } = render(<App />);

    expect(await screen.findByText("Simulated Executions")).toBeInTheDocument();
    unmount();

    window.history.pushState({}, "", "/settlements");
    const settlements = render(<App />);

    expect(await screen.findByText("Settlements")).toBeInTheDocument();
    settlements.unmount();

    window.history.pushState({}, "", "/learning-proposals");
    render(<App />);

    expect(await screen.findByText("Learning Proposals")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /approve|reject|apply/i })).not.toBeInTheDocument();
  });

  it("serves /system and keeps System last in navigation", async () => {
    window.history.pushState({}, "", "/system");

    render(<App />);

    expect(await screen.findByRole("heading", { name: "System Runtime Status" })).toBeInTheDocument();
    const navItems = screen.getAllByRole("menuitem").map((item) => item.textContent);
    expect(navItems.at(-1)).toBe("System");
  });
});

async function apiResponse(input: RequestInfo | URL) {
  const url = String(input);
  if (url.endsWith("/research/watchlist")) {
    return json({ items: [], total: 0, limit: 50, offset: 0 });
  }
  if (url.endsWith("/dashboard/summary")) {
    return json({
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
    });
  }
  if (url.endsWith("/system/status")) {
    return json({
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
        message: "git commit was not injected",
      },
      database: {
        status: "healthy",
        backend: "in_memory",
        checked_at: "2026-07-28T08:00:00Z",
        latency_ms: 0,
        message: null,
      },
      scheduler: {
        status: "unknown",
        running: false,
        last_heartbeat_at: null,
        heartbeat_age_seconds: null,
        message: "scheduler heartbeat has not been recorded",
      },
      jobs: {
        research_due_scan: {
          status: "unknown",
          enabled: true,
          last_started_at: null,
          last_completed_at: null,
          last_result: null,
          last_error: null,
          processed_count: null,
          success_count: null,
          failure_count: null,
        },
        settlement_due_scan: {
          status: "unknown",
          enabled: true,
          last_started_at: null,
          last_completed_at: null,
          last_result: null,
          last_error: null,
          processed_count: null,
          success_count: null,
          failure_count: null,
        },
      },
      queues: {
        research_due: 0,
        settlement_due: 0,
        failed_research_runs: 0,
        resumable_research_runs: 0,
      },
      providers: [],
      issues: [],
    });
  }
  if (url.includes("/research/runs")) {
    return json({ items: [], total: 0, limit: 10, offset: 0, count: 0 });
  }
  if (url.includes("/simulated-executions")) {
    return json({ items: [], total: 0, page: 1, page_size: 10, count: 0 });
  }
  if (url.includes("/settlements")) {
    return json({ items: [], total: 0, page: 1, page_size: 10, count: 0 });
  }
  if (url.includes("/learnings")) {
    return json({ items: [], total: 0, limit: 50, offset: 0, count: 0 });
  }
  if (url.endsWith("/evidence") || url.endsWith("/research/sessions")) {
    return json({ items: [], total: 0, limit: 50, offset: 0 });
  }
  return json({ items: [], total: 0, limit: 50, offset: 0 });
}

function json(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "content-type": "application/json" },
  });
}
