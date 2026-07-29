import { useQuery } from "@tanstack/react-query";
import { Card, Form, Select, Space, Table, Typography } from "antd";
import type { ColumnsType, TablePaginationConfig } from "antd/es/table";
import { Link, useSearchParams } from "react-router-dom";

import {
  BusinessStatusTag,
  EmptyBusinessState,
  LongText,
  UserReadableError,
} from "../../../shared/businessComponents";
import { displayAction, displayStatus } from "../../../shared/displayMappings";
import { formatDateTime, formatPercent, formatValue } from "../../../shared/formatters";
import { reviewsApi } from "../api";
import type { ReviewSummary } from "../types";

const PAGE_SIZE = 10;

export function ReviewsPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const current = Number(searchParams.get("page") ?? "1");
  const includeTestData = searchParams.get("include_test_data") === "true";
  const reviews = useQuery({
    queryKey: ["reviews-summary", current, includeTestData],
    queryFn: () =>
      reviewsApi.summary({
        page: current,
        pageSize: PAGE_SIZE,
        includeTestData,
      }),
  });

  const columns: ColumnsType<ReviewSummary> = [
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
      title: "原始决策",
      dataIndex: "original_decision",
      width: 110,
      render: displayAction,
    },
    { title: "研究周期", dataIndex: "research_horizon", width: 110, render: formatValue },
    {
      title: "模拟执行时间",
      dataIndex: "execution_time",
      width: 170,
      render: formatDateTime,
    },
    { title: "入场价格", dataIndex: "entry_price", width: 110, render: formatValue },
    { title: "退出价格", dataIndex: "exit_price", width: 110, render: formatValue },
    {
      title: "实际收益率",
      dataIndex: "return_rate",
      width: 120,
      render: formatPercent,
    },
    {
      title: "判断是否正确",
      dataIndex: "directional_result",
      width: 130,
      render: displayStatus,
    },
    {
      title: "风控是否有效",
      dataIndex: "risk_result",
      width: 130,
      render: displayStatus,
    },
    {
      title: "主要错误",
      dataIndex: "main_error",
      width: 220,
      render: (value: string | null) => <LongText text={value} maxLength={64} />,
    },
    {
      title: "学习建议",
      dataIndex: "learning_proposal_status",
      width: 120,
      render: (value: string | null) => <BusinessStatusTag value={value} />,
    },
    {
      title: "查看详情",
      dataIndex: "settlement_id",
      fixed: "right",
      width: 120,
      render: (value: string) => (
        <Link to={`/reviews/${encodeURIComponent(value)}`}>查看复盘</Link>
      ),
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
    <section className="reviews-page">
      <div className="page-heading">
        <div>
          <Typography.Title level={2}>复盘</Typography.Title>
          <Typography.Text type="secondary">
            合并查看模拟执行、结果结算、评价、复盘和学习建议。
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

      {reviews.error ? <UserReadableError error={reviews.error} /> : null}

      <Table
        rowKey="settlement_id"
        columns={columns}
        dataSource={reviews.data?.items ?? []}
        loading={reviews.isLoading || reviews.isFetching}
        locale={{ emptyText: <EmptyBusinessState description="暂无复盘记录" /> }}
        pagination={{
          current,
          pageSize: PAGE_SIZE,
          total: reviews.data?.total ?? 0,
          showSizeChanger: false,
        }}
        scroll={{ x: 1500 }}
        onChange={changePage}
      />
    </section>
  );
}
