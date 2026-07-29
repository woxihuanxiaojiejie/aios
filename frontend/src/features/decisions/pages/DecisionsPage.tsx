import { useQuery } from "@tanstack/react-query";
import { Card, Form, Select, Space, Table, Typography } from "antd";
import type { ColumnsType, TablePaginationConfig } from "antd/es/table";
import { useMemo } from "react";
import { Link, useSearchParams } from "react-router-dom";

import {
  BusinessStatusTag,
  EmptyBusinessState,
  LongText,
  UserReadableError,
} from "../../../shared/businessComponents";
import { displayAction } from "../../../shared/displayMappings";
import { formatDateTime, formatPercent, formatValue } from "../../../shared/formatters";
import { decisionsApi } from "../api";
import type { DecisionSummary } from "../types";

const PAGE_SIZE = 10;

export function DecisionsPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const current = Number(searchParams.get("page") ?? "1");
  const includeTestData = searchParams.get("include_test_data") === "true";
  const queryKey = useMemo(
    () => ["decisions-summary", current, includeTestData],
    [current, includeTestData],
  );
  const decisions = useQuery({
    queryKey,
    queryFn: () =>
      decisionsApi.summary({
        page: current,
        pageSize: PAGE_SIZE,
        includeTestData,
      }),
  });

  const columns: ColumnsType<DecisionSummary> = [
    {
      title: "股票",
      dataIndex: "symbol",
      width: 140,
      render: (_value, record) => (
        <Space orientation="vertical" size={0}>
          <Typography.Text strong>{record.stock_name ?? record.symbol}</Typography.Text>
          <Typography.Text type="secondary">{record.market ?? "-"}</Typography.Text>
        </Space>
      ),
    },
    {
      title: "决策时间",
      dataIndex: "decided_at",
      width: 180,
      render: formatDateTime,
    },
    { title: "研究周期", dataIndex: "research_horizon", width: 110, render: formatValue },
    {
      title: "最终决策",
      dataIndex: "action",
      width: 110,
      render: displayAction,
    },
    {
      title: "置信度",
      dataIndex: "confidence",
      width: 100,
      render: formatPercent,
    },
    {
      title: "核心理由",
      dataIndex: "core_reason",
      width: 260,
      render: (value: string) => <LongText text={value} maxLength={72} />,
    },
    {
      title: "主要风险",
      dataIndex: "risks",
      width: 220,
      render: (value: string[]) => formatValue(value),
    },
    {
      title: "失效条件",
      dataIndex: "invalidation_conditions",
      width: 220,
      render: (value: string[]) => formatValue(value),
    },
    {
      title: "交易计划",
      dataIndex: "trade_plan_status",
      width: 120,
      render: (value: string | null) => <BusinessStatusTag value={value} />,
    },
    {
      title: "执行状态",
      dataIndex: "simulated_execution_status",
      width: 120,
      render: (value: string | null) => <BusinessStatusTag value={value} />,
    },
    {
      title: "查看完整研究",
      dataIndex: "research_run_id",
      fixed: "right",
      width: 140,
      render: (value: string | null) =>
        value ? <Link to={`/research/${encodeURIComponent(value)}`}>查看研究</Link> : "-",
    },
  ];

  function changePage(pagination: TablePaginationConfig) {
    const next = new URLSearchParams(searchParams);
    next.set("page", String(pagination.current ?? 1));
    setSearchParams(next);
  }

  function changeTestData(value: string | undefined) {
    const next = new URLSearchParams(searchParams);
    if (value === "true") next.set("include_test_data", "true");
    else next.delete("include_test_data");
    next.set("page", "1");
    setSearchParams(next);
  }

  return (
    <section className="decisions-page">
      <div className="page-heading">
        <div>
          <Typography.Title level={2}>决策</Typography.Title>
          <Typography.Text type="secondary">
            以 AIOS 最终决策为核心查看研究结论、风险和执行状态。
          </Typography.Text>
        </div>
      </div>

      <Card className="tool-card" title="筛选">
        <Form layout="inline">
          <Form.Item label="测试数据">
            <Select
              allowClear
              className="filter-select"
              value={includeTestData ? "true" : undefined}
              onChange={changeTestData}
              options={[{ value: "true", label: "显示测试数据" }]}
              placeholder="默认隐藏"
            />
          </Form.Item>
        </Form>
      </Card>

      {decisions.error ? <UserReadableError error={decisions.error} /> : null}

      <Table
        rowKey="decision_id"
        columns={columns}
        dataSource={decisions.data?.items ?? []}
        loading={decisions.isLoading || decisions.isFetching}
        locale={{ emptyText: <EmptyBusinessState description="暂无决策记录" /> }}
        pagination={{
          current,
          pageSize: PAGE_SIZE,
          total: decisions.data?.total ?? 0,
          showSizeChanger: false,
        }}
        scroll={{ x: 1600 }}
        onChange={changePage}
      />
    </section>
  );
}
