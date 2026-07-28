import { Refine } from "@refinedev/core";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { App as AntdApp, ConfigProvider } from "antd";
import type { ReactNode } from "react";

import { aiosDataProvider } from "../infrastructure/refine/dataProvider";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      staleTime: 30_000,
    },
    mutations: {
      retry: false,
    },
  },
});

export function AppProviders({ children }: { children: ReactNode }) {
  return (
    <ConfigProvider
      theme={{
        token: {
          borderRadius: 6,
          colorPrimary: "#1f6f8b",
          fontFamily:
            '"PingFang SC", "Microsoft YaHei", "Noto Sans CJK SC", system-ui, sans-serif',
        },
      }}
    >
      <AntdApp>
        <QueryClientProvider client={queryClient}>
          <Refine
            dataProvider={aiosDataProvider}
            resources={[
              {
                name: "watchlist",
                list: "/watchlist",
                create: "/watchlist",
                edit: "/watchlist",
              },
              {
                name: "research-runs",
                list: "/research",
                show: "/research/:runId",
                create: "/research/new",
              },
              {
                name: "simulated-executions",
                list: "/executions",
                show: "/executions/:executionId",
              },
              {
                name: "settlements",
                list: "/settlements",
                show: "/settlements/:settlementId",
              },
              {
                name: "learnings",
                list: "/learning-proposals",
              },
            ]}
            options={{ syncWithLocation: false }}
          >
            {children}
          </Refine>
        </QueryClientProvider>
      </AntdApp>
    </ConfigProvider>
  );
}
