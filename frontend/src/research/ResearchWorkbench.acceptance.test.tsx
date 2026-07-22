import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import { ResearchWorkbench } from "./ResearchWorkbench";

const acceptanceIt =
  import.meta.env.VITE_AIOS_RUN_FRONTEND_ACCEPTANCE === "1" ? it : it.skip;

describe("ResearchWorkbench acceptance", () => {
  acceptanceIt(
    "通过真实 API 从自选股票推进到学习记录",
    async () => {
      const user = userEvent.setup();
      renderWorkbench();

      const suffix = Date.now().toString();
      await user.clear(screen.getByLabelText("股票"));
      await user.type(screen.getByLabelText("股票"), `AIOS${suffix.slice(-8)}`);
      await user.click(screen.getByRole("button", { name: /新增股票/ }));
      await waitForStatus("新增自选股票完成");

      await user.click(screen.getByRole("button", { name: /创建证据/ }));
      await waitForStatus("创建证据完成");

      await user.click(screen.getByRole("button", { name: /创建研究会话/ }));
      await waitForStatus("创建研究会话完成");

      await user.click(screen.getByRole("button", { name: /提交 Agent 汇报/ }));
      await waitForStatus("提交 Agent 汇报完成");

      await user.click(screen.getByRole("button", { name: /提交策略假设/ }));
      await waitForStatus("提交策略假设完成");

      await user.click(screen.getByRole("button", { name: /创建辩论/ }));
      await waitForStatus("创建辩论完成");

      await user.click(screen.getByRole("button", { name: /提交辩论意见/ }));
      await waitForStatus("提交辩论意见完成");

      await user.click(screen.getByRole("button", { name: /创建决策建议/ }));
      await waitForStatus("创建决策建议完成");

      await user.click(screen.getByRole("button", { name: /提交风险审核/ }));
      await waitForStatus("提交风险审核完成");

      await user.click(screen.getByRole("button", { name: /生成最终决策/ }));
      await waitForStatus("生成最终决策完成");

      await user.type(
        screen.getByPlaceholderText("留空使用后端当前时间"),
        futureIso(5),
      );
      await user.click(screen.getByRole("button", { name: /执行结算/ }));
      await waitForStatus("执行结算完成");

      expect(screen.getByText("自选股票")).toBeInTheDocument();
      expect(screen.getByText("研究会话")).toBeInTheDocument();
      expect(screen.getByText("最终决策")).toBeInTheDocument();
      expect(screen.getByText("学习记录")).toBeInTheDocument();
      expect(screen.getByText("已结算")).toBeInTheDocument();
    },
    60000,
  );
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

async function waitForStatus(status: string) {
  await waitFor(() => expect(screen.getByText(status)).toBeInTheDocument(), {
    timeout: 10000,
  });
}

function futureIso(days: number) {
  const date = new Date();
  date.setUTCDate(date.getUTCDate() + days);
  return date.toISOString();
}
