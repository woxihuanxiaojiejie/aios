import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ResearchWorkbench } from "./ResearchWorkbench";

vi.mock("lightweight-charts", () => ({
  createChart: () => ({
    addCandlestickSeries: () => ({ setData: vi.fn() }),
    addHistogramSeries: () => ({
      setData: vi.fn(),
      priceScale: () => ({ applyOptions: vi.fn() }),
    }),
    applyOptions: vi.fn(),
    remove: vi.fn(),
    removeSeries: vi.fn(),
    timeScale: () => ({ fitContent: vi.fn() }),
  }),
}));

describe("ResearchWorkbench", () => {
  beforeEach(() => {
    vi.stubGlobal(
      "ResizeObserver",
      class {
        observe() {}
        disconnect() {}
      },
    );
  });

  it("展示顶部中文搜索栏", async () => {
    renderWorkbench();

    const input = screen.getByLabelText("搜索股票");
    await userEvent.type(input, "平安银行");

    expect(input).toHaveValue("平安银行");
    expect(screen.getByPlaceholderText("搜索股票（名称/代码）")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "开始研究" })).toBeInTheDocument();
  });

  it("展示中间行情和放大的K线区域", () => {
    renderWorkbench();

    expect(screen.getByText("行情与K线")).toBeInTheDocument();
    expect(screen.getByText("平安银行 000001.SZ")).toBeInTheDocument();
    expect(screen.getByText("10.78")).toBeInTheDocument();
    expect(screen.getByLabelText("日K线图")).toBeInTheDocument();
  });

  it("展示中文AI研究报告", () => {
    renderWorkbench();

    expect(screen.getByText("AI研究报告")).toBeInTheDocument();
    expect(screen.getByText("建议")).toBeInTheDocument();
    expect(screen.getAllByText("观望").length).toBeGreaterThan(1);
    expect(screen.getByText("AI信心")).toBeInTheDocument();
    expect(screen.getByText("★★★★☆")).toBeInTheDocument();
    expect(screen.getByText("主要观点")).toBeInTheDocument();
    expect(screen.getByText("风险")).toBeInTheDocument();
    expect(screen.getByText("重点关注")).toBeInTheDocument();
  });

  it("展示底部新闻、公司信息、历史预测和AI复盘", () => {
    renderWorkbench();

    expect(screen.getByText("新闻")).toBeInTheDocument();
    expect(screen.getByText("今日新闻")).toBeInTheDocument();
    expect(screen.getByText("今天公告")).toBeInTheDocument();
    expect(screen.getAllByText("暂无数据")).toHaveLength(2);

    expect(screen.getByText("公司信息")).toBeInTheDocument();
    expect(screen.getByText("公司简介")).toBeInTheDocument();
    expect(screen.getByText("所属行业")).toBeInTheDocument();
    expect(screen.getByText("主营业务")).toBeInTheDocument();
    expect(screen.getByText("市值")).toBeInTheDocument();
    expect(screen.getByText("PE")).toBeInTheDocument();
    expect(screen.getByText("PB")).toBeInTheDocument();

    expect(screen.getByText("历史预测")).toBeInTheDocument();
    expect(screen.getByText("日期")).toBeInTheDocument();
    expect(screen.getAllByText("股票").length).toBeGreaterThan(1);
    expect(screen.getByText("AI建议")).toBeInTheDocument();
    expect(screen.getAllByText("收益").length).toBeGreaterThan(1);
    expect(screen.getByText("状态")).toBeInTheDocument();

    expect(screen.getByText("AI复盘")).toBeInTheDocument();
    expect(screen.getByText("评价")).toBeInTheDocument();
    expect(screen.getByText("原因")).toBeInTheDocument();
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
