import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ResearchWorkbench } from "./ResearchWorkbench";

let failWatchlist = false;
let failSettlementNotReady = false;
let initialData = false;
let sessionValidUntil = "2999-01-01T00:00:00Z";

describe("ResearchWorkbench", () => {
  beforeEach(() => {
    failWatchlist = false;
    failSettlementNotReady = false;
    initialData = false;
    sessionValidUntil = "2999-01-01T00:00:00Z";
    vi.stubGlobal("fetch", vi.fn(fetchResponse));
  });

  it("展示中文化的完整研究闭环验收区域", async () => {
    renderWorkbench();

    expect(screen.getByText("AIOS 人工验收工作台")).toBeInTheDocument();
    expect(screen.getByText("1 自选股票")).toBeInTheDocument();
    expect(screen.getByText("2 证据与研究")).toBeInTheDocument();
    expect(screen.getByText("3 Agent 汇报与假设")).toBeInTheDocument();
    expect(screen.getByText("4 辩论、建议与风险审核")).toBeInTheDocument();
    expect(screen.getByText("5 决策、结算与学习")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /生成最终决策/ })).toBeDisabled();
    expect(screen.getByText("请先创建决策建议。")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /执行结算/ })).toBeDisabled();
    expect(screen.getByText("请先生成最终决策。")).toBeInTheDocument();
    expect(screen.getByText("暂无学习记录")).toBeInTheDocument();
    await waitFor(() => expect(screen.getByText("等待操作")).toBeInTheDocument());
  });

  it("可以新增自选股票并显示已完成状态", async () => {
    const user = userEvent.setup();
    renderWorkbench();

    await user.clear(screen.getByDisplayValue("600519"));
    await user.type(screen.getByLabelText("股票"), "000001.SZ");
    await user.click(screen.getByRole("button", { name: /新增股票/ }));

    await waitFor(() =>
      expect(screen.getByText("新增自选股票完成")).toBeInTheDocument(),
    );
    expect(screen.getByText("已完成")).toBeInTheDocument();
    expect(screen.queryByText("wl_test")).not.toBeInTheDocument();
  });

  it("高级信息默认折叠，展开后才显示内部编号", async () => {
    const user = userEvent.setup();
    renderWorkbench();

    await user.click(screen.getByRole("button", { name: /新增股票/ }));
    await waitFor(() =>
      expect(screen.getByText("新增自选股票完成")).toBeInTheDocument(),
    );

    expect(screen.queryByText("wl_test")).not.toBeInTheDocument();
    await user.click(screen.getAllByText("高级信息")[0]);
    expect(screen.getByText("wl_test")).toBeInTheDocument();
  });

  it("后端错误映射为中文提示", async () => {
    failWatchlist = true;
    const user = userEvent.setup();
    renderWorkbench();

    await user.click(screen.getByRole("button", { name: /新增股票/ }));

    await waitFor(() =>
      expect(screen.getByText("当前记录已存在或操作发生冲突。")).toBeInTheDocument(),
    );
  });

  it("生成最终决策需要先完成风险审核", async () => {
    const user = userEvent.setup();
    renderWorkbench();

    await advanceToProposal(user);

    expect(screen.getByRole("button", { name: /生成最终决策/ })).toBeDisabled();
    expect(screen.getByText("请先完成风险审核。")).toBeInTheDocument();
  });

  it("刷新后根据最新研究会话和已加载记录恢复当前状态", async () => {
    initialData = true;
    renderWorkbench();

    await waitFor(() => expect(screen.getByText("当前状态：辩论中")).toBeInTheDocument());
    expect(screen.getByText("AIOS 初始记录 / CN")).toBeInTheDocument();
    expect(screen.getAllByText("当前选中").length).toBeGreaterThan(0);
  });

  it("不显示其他研究会话的学习记录", async () => {
    initialData = true;
    renderWorkbench();

    await waitFor(() => expect(screen.getByText("当前状态：辩论中")).toBeInTheDocument());

    expect(screen.getByText("暂无学习记录")).toBeInTheDocument();
    expect(screen.queryByText("lr_foreign")).not.toBeInTheDocument();
  });

  it("未到预测截止时间时显示尚未到期并禁用结算", async () => {
    const user = userEvent.setup();
    renderWorkbench();

    await advanceToAssembly(user);

    await waitFor(() => expect(screen.getByText("当前状态：等待结算")).toBeInTheDocument());
    expect(screen.getByText("当前结算状态")).toBeInTheDocument();
    expect(screen.getByText("尚未到期")).toBeInTheDocument();
    expect(screen.getByText(/预计可结算时间：/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /执行结算/ })).toBeDisabled();
    expect(screen.getByText("尚未到达预测截止时间")).toBeInTheDocument();
  });

  it("结算未到期错误映射为中文且不把阶段显示为失败", async () => {
    failSettlementNotReady = true;
    sessionValidUntil = "2000-01-01T00:00:00Z";
    const user = userEvent.setup();
    renderWorkbench();

    await advanceToAssembly(user);
    await user.clear(screen.getByLabelText("结算时间"));
    await user.type(screen.getByLabelText("结算时间"), futureIso(5));
    await user.click(screen.getByRole("button", { name: /执行结算/ }));

    await waitFor(() =>
      expect(
        screen.getByText("尚未到达预测截止时间，暂时不能结算。"),
      ).toBeInTheDocument(),
    );
    expect(screen.getByText("当前状态：等待结算")).toBeInTheDocument();
    expect(screen.queryByText("当前状态：失败")).not.toBeInTheDocument();
  });
});

function renderWorkbench() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  render(
    <QueryClientProvider client={queryClient}>
      <ResearchWorkbench />
    </QueryClientProvider>,
  );
}

async function fetchResponse(input: RequestInfo | URL, init?: RequestInit) {
  const url = String(input);
  const method = init?.method ?? "GET";
  if (method === "POST" && url.endsWith("/research/watchlist")) {
    if (failWatchlist) {
      return jsonError(409, "conflict", "duplicate watchlist item");
    }
    const body = JSON.parse(String(init?.body)) as { symbol: string; market: string };
    return json(watchlistFixture({
      watchlist_item_id: "wl_test",
      symbol: body.symbol,
      market: body.market,
      note: null,
    }));
  }
  if (method === "PATCH" && url.includes("/research/watchlist/")) {
    const body = JSON.parse(String(init?.body)) as Record<string, unknown>;
    return json(
      watchlistFixture({
        watchlist_item_id: "wl_test",
        symbol: "600519",
        market: "CN",
        note: null,
        ...body,
      }),
    );
  }
  if (method === "POST" && url.endsWith("/run")) {
    return json({
      run: {
        run_id: "rr_test",
        research_session_id: "rs_test",
        watchlist_item_id: "wl_test",
        symbol: "600519",
        research_window_key: "CN:600519:3:2026-07-22T00:00:00Z",
        current_stage: "completed",
        status: "completed",
        failed_stage: null,
        error_type: null,
        error: null,
        finished_at: "2026-07-22T00:00:00Z",
        created_at: "2026-07-22T00:00:00Z",
        updated_at: "2026-07-22T00:00:00Z",
      },
      trade_plan: null,
      simulated_execution: null,
    });
  }
  if (method === "POST" && url.endsWith("/evidence")) {
    return json({
      evidence_id: "ev_test",
      evidence_type: "manual_acceptance",
      source: "manual",
      symbols: ["000001.SZ"],
      published_at: "2026-07-22T00:00:00Z",
      available_at: "2026-07-22T00:00:00Z",
      summary: "人工验收证据",
      reliability: 0.8,
      content_hash: "hash_test",
      metadata: {},
      created_at: "2026-07-22T00:00:00Z",
    });
  }
  if (method === "POST" && url.endsWith("/research/sessions")) {
    return json({
      research_session_id: "rs_test",
      scope: {
        watchlist_item_id: "wl_test",
        symbol: "000001.SZ",
        market: "CN",
        watchlist_note_snapshot: null,
        horizon_days: 3,
        as_of: "2026-07-22T00:00:00Z",
        valid_until: sessionValidUntil,
      },
      status: "active",
      evidence_ids: ["ev_test"],
      experiment_id: null,
      cancelled_at: null,
      created_at: "2026-07-22T00:00:00Z",
      updated_at: "2026-07-22T00:00:00Z",
    });
  }
  if (method === "POST" && url.endsWith("/agent-reports")) {
    return json({
      report_id: "ar_test",
      research_session_id: "rs_test",
      role: "technical",
      summary: "技术报告支持假设",
      stance: "buy",
      confidence: 0.7,
      evidence_ids: ["ev_test"],
      source: "manual",
      raw_reference: null,
      status: "active",
      archived_at: null,
      created_at: "2026-07-22T00:00:00Z",
      updated_at: "2026-07-22T00:00:00Z",
    });
  }
  if (method === "POST" && url.endsWith("/hypotheses")) {
    return json({
      hypothesis_id: "hp_test",
      research_session_id: "rs_test",
      statement: "价格趋势支持上行",
      rationale: "人工验收报告支持该假设",
      direction: "bullish",
      horizon_days: 3,
      confidence: 0.7,
      supporting_report_ids: ["ar_test"],
      supporting_evidence_ids: ["ev_test"],
      status: "active",
      created_at: "2026-07-22T00:00:00Z",
      updated_at: "2026-07-22T00:00:00Z",
    });
  }
  if (method === "POST" && url.endsWith("/debates")) {
    return json({
      debate_id: "db_test",
      research_session_id: "rs_test",
      report_ids: ["ar_test"],
      hypothesis_ids: ["hp_test"],
      status: "open",
      final_decision_id: null,
      created_at: "2026-07-22T00:00:00Z",
      updated_at: "2026-07-22T00:00:00Z",
    });
  }
  if (method === "POST" && url.endsWith("/statements")) {
    return json({
      statement_id: "ds_test",
      debate_id: "db_test",
      agent_report_id: "ar_test",
      hypothesis_id: "hp_test",
      stance: "support",
      reasoning: "人工验收：报告支持假设",
      evidence_ids: ["ev_test"],
      confidence_before: 0.5,
      confidence_after: 0.7,
      created_at: "2026-07-22T00:00:00Z",
    });
  }
  if (method === "POST" && url.endsWith("/proposal")) {
    return json({
      proposal_id: "dp_test",
      debate_id: "db_test",
      conclusion: "buy",
      confidence: 0.7,
      thesis: "基于证据和辩论形成买入提案",
      supporting_hypothesis_ids: ["hp_test"],
      rejected_hypothesis_ids: [],
      evidence_ids: ["ev_test"],
      risk_notes: ["人工验收风险记录"],
      created_at: "2026-07-22T00:00:00Z",
    });
  }
  if (method === "POST" && url.endsWith("/risk-review")) {
    return json({
      risk_review_id: "rr_test",
      proposal_id: "dp_test",
      verdict: "approve",
      final_conclusion: "buy",
      final_confidence: 0.7,
      reasons: ["人工验收通过风险复核"],
      created_at: "2026-07-22T00:00:00Z",
    });
  }
  if (method === "POST" && url.endsWith("/finalize")) {
    return json({
      assembly_id: "da_test",
      research_session_id: "rs_test",
      debate_id: "db_test",
      proposal_id: "dp_test",
      risk_review_id: "rr_test",
      decision_id: "dc_test",
      conclusion: "buy",
      report_ids: ["ar_test"],
      hypothesis_ids: ["hp_test"],
      evidence_ids: ["ev_test"],
      created_at: "2026-07-22T00:00:00Z",
    });
  }
  if (method === "POST" && url.endsWith("/settlement")) {
    if (failSettlementNotReady) {
      return jsonError(409, "invalid_state_transition", "session not ready");
    }
    return json({ items: [], total: 0, limit: 50, offset: 0 });
  }
  if (url.endsWith("/research/watchlist")) {
    return json({
      items: initialData
        ? [
            watchlistFixture({
              watchlist_item_id: "wl_initial",
              symbol: "AIOS 初始记录",
              market: "CN",
              note: null,
            }),
          ]
        : [],
      total: initialData ? 1 : 0,
      limit: 50,
      offset: 0,
    });
  }
  if (url.endsWith("/evidence")) {
    return json({
      items: initialData
        ? [
            {
              evidence_id: "ev_initial",
              evidence_type: "manual_acceptance",
              source: "manual",
              symbols: ["AIOS 初始记录"],
              published_at: "2026-07-22T00:00:00Z",
              available_at: "2026-07-22T00:00:00Z",
              summary: "初始证据",
              reliability: 0.8,
              content_hash: "hash_initial",
              metadata: {},
              created_at: "2026-07-22T00:00:00Z",
            },
          ]
        : [],
      total: initialData ? 1 : 0,
      limit: 50,
      offset: 0,
    });
  }
  if (url.endsWith("/research/sessions")) {
    return json({
      items: initialData
        ? [
            {
              research_session_id: "rs_initial",
              scope: {
                watchlist_item_id: "wl_initial",
                symbol: "AIOS 初始记录",
                market: "CN",
                watchlist_note_snapshot: null,
                horizon_days: 3,
                as_of: "2026-07-22T00:00:00Z",
                valid_until: "2026-07-25T00:00:00Z",
              },
              status: "active",
              evidence_ids: ["ev_initial"],
              experiment_id: null,
              cancelled_at: null,
              created_at: "2026-07-22T00:00:00Z",
              updated_at: "2026-07-22T00:00:00Z",
            },
          ]
        : [],
      total: initialData ? 1 : 0,
      limit: 50,
      offset: 0,
    });
  }
  if (url.endsWith("/learnings")) {
    return json({
      items: initialData
        ? [
            {
              learning_id: "lr_foreign",
              review_id: "rv_foreign",
              learning_type: "adjustment",
              target: "foreign",
              before: null,
              after: null,
              reason: "其他研究会话的学习记录",
              approval_status: "pending",
              created_at: "2026-07-22T00:00:00Z",
            },
          ]
        : [],
      total: initialData ? 1 : 0,
      limit: 50,
      offset: 0,
    });
  }
  if (url.endsWith("/agent-reports")) {
    return json({
      items: initialData
        ? [
            {
              report_id: "ar_initial",
              research_session_id: "rs_initial",
              role: "technical",
              summary: "初始 Agent 汇报",
              stance: "buy",
              confidence: 0.7,
              evidence_ids: ["ev_initial"],
              source: "manual",
              raw_reference: null,
              status: "active",
              archived_at: null,
              created_at: "2026-07-22T00:00:00Z",
              updated_at: "2026-07-22T00:00:00Z",
            },
          ]
        : [],
      total: initialData ? 1 : 0,
      limit: 50,
      offset: 0,
    });
  }
  if (url.endsWith("/hypotheses")) {
    return json({
      items: initialData
        ? [
            {
              hypothesis_id: "hp_initial",
              research_session_id: "rs_initial",
              statement: "初始策略假设",
              rationale: "初始证据支持",
              direction: "bullish",
              horizon_days: 3,
              confidence: 0.7,
              supporting_report_ids: ["ar_initial"],
              supporting_evidence_ids: ["ev_initial"],
              status: "active",
              created_at: "2026-07-22T00:00:00Z",
              updated_at: "2026-07-22T00:00:00Z",
            },
          ]
        : [],
      total: initialData ? 1 : 0,
      limit: 50,
      offset: 0,
    });
  }
  if (url.endsWith("/debates")) {
    return json({
      items: initialData
        ? [
            {
              debate_id: "db_initial",
              research_session_id: "rs_initial",
              report_ids: ["ar_initial"],
              hypothesis_ids: ["hp_initial"],
              status: "open",
              final_decision_id: null,
              created_at: "2026-07-22T00:00:00Z",
              updated_at: "2026-07-22T00:00:00Z",
            },
          ]
        : [],
      total: initialData ? 1 : 0,
      limit: 50,
      offset: 0,
    });
  }
  return json({ items: [], total: 0, limit: 50, offset: 0 });
}

function watchlistFixture(
  overrides: Partial<Record<string, unknown>> & {
    watchlist_item_id: string;
    symbol: string;
    market: string;
  },
) {
  return {
    note: null,
    status: "active",
    auto_research_enabled: false,
    research_horizon_days: 3,
    schedule_time: "15:00:00",
    schedule_timezone: "Asia/Shanghai",
    next_run_at: null,
    last_run_at: null,
    created_at: "2026-07-22T00:00:00Z",
    updated_at: "2026-07-22T00:00:00Z",
    archived_at: null,
    ...overrides,
  };
}

function json(payload: unknown) {
  return Promise.resolve(
    new Response(JSON.stringify(payload), {
      status: 200,
      headers: { "content-type": "application/json" },
    }),
  );
}

function jsonError(status: number, code: string, message: string) {
  return Promise.resolve(
    new Response(
      JSON.stringify({
        error: { code, message, details: {} },
      }),
      {
        status,
        headers: { "content-type": "application/json" },
      },
    ),
  );
}

async function advanceToProposal(user: ReturnType<typeof userEvent.setup>) {
  await user.click(screen.getByRole("button", { name: /新增股票/ }));
  await waitFor(() =>
    expect(screen.getByText("新增自选股票完成")).toBeInTheDocument(),
  );
  await user.click(screen.getByRole("button", { name: /创建证据/ }));
  await waitFor(() => expect(screen.getByText("创建证据完成")).toBeInTheDocument());
  await user.click(screen.getByRole("button", { name: /创建研究会话/ }));
  await waitFor(() =>
    expect(screen.getByText("创建研究会话完成")).toBeInTheDocument(),
  );
  await user.click(screen.getByRole("button", { name: /提交 Agent 汇报/ }));
  await waitFor(() =>
    expect(screen.getByText("提交 Agent 汇报完成")).toBeInTheDocument(),
  );
  await user.click(screen.getByRole("button", { name: /提交策略假设/ }));
  await waitFor(() =>
    expect(screen.getByText("提交策略假设完成")).toBeInTheDocument(),
  );
  await user.click(screen.getByRole("button", { name: /创建辩论/ }));
  await waitFor(() => expect(screen.getByText("创建辩论完成")).toBeInTheDocument());
  await user.click(screen.getByRole("button", { name: /提交辩论意见/ }));
  await waitFor(() =>
    expect(screen.getByText("提交辩论意见完成")).toBeInTheDocument(),
  );
  await user.click(screen.getByRole("button", { name: /创建决策建议/ }));
  await waitFor(() =>
    expect(screen.getByText("创建决策建议完成")).toBeInTheDocument(),
  );
}

async function advanceToAssembly(user: ReturnType<typeof userEvent.setup>) {
  await advanceToProposal(user);
  await user.click(screen.getByRole("button", { name: /提交风险审核/ }));
  await waitFor(() =>
    expect(screen.getByText("提交风险审核完成")).toBeInTheDocument(),
  );
  await user.click(screen.getByRole("button", { name: /生成最终决策/ }));
  await waitFor(() =>
    expect(screen.getByText("生成最终决策完成")).toBeInTheDocument(),
  );
}

function futureIso(days: number) {
  const date = new Date();
  date.setUTCDate(date.getUTCDate() + days);
  return date.toISOString();
}
