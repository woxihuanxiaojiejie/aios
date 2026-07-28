import { useDataProvider } from "@refinedev/core";
import { useQuery } from "@tanstack/react-query";
import { Button, Card, Form, Input, Select, Space, Table, Typography } from "antd";
import type { ColumnsType, TablePaginationConfig } from "antd/es/table";
import { useEffect, useMemo } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";

import {
  EmptyState,
  ErrorState,
  StatusTag,
  formatDateTime,
  formatPercent,
} from "../../../shared/researchDisplay";
import { ApiError } from "../../../infrastructure/api/client";
import type { ResearchRunFilters, ResearchRunListItem } from "../types";

const PAGE_SIZE = 10;

export function ResearchRunsPage() {
  const navigate = useNavigate();
  const [form] = Form.useForm<ResearchRunFilters>();
  const [searchParams, setSearchParams] = useSearchParams();
  const dataProvider = useDataProvider();
  const current = Number(searchParams.get("page") ?? "1");
  const filters = useMemo(
    () => ({
      symbol: searchParams.get("symbol") || undefined,
      market: searchParams.get("market") || undefined,
      status: searchParams.get("status") || undefined,
      workflow: searchParams.get("workflow") || undefined,
      created_from: searchParams.get("created_from") || undefined,
      created_to: searchParams.get("created_to") || undefined,
      sort: searchParams.get("sort") || undefined,
    }),
    [searchParams],
  );

  useEffect(() => {
    form.setFieldsValue(filters);
  }, [filters, form]);

  const list = useQuery({
    queryKey: ["research-runs", current, filters],
    queryFn: () =>
      dataProvider().getList<ResearchRunListItem>({
        resource: "research-runs",
        pagination: { currentPage: current, pageSize: PAGE_SIZE },
        filters: Object.entries(filters)
          .filter(([, value]) => value)
          .map(([field, value]) => ({ field, operator: "eq", value })),
      }),
  });

  const rows = list.data?.data ?? [];
  const total = list.data?.total ?? 0;
  const queryError = list.error ?? list.failureReason;

  const columns: ColumnsType<ResearchRunListItem> = [
    {
      title: "Run ID",
      dataIndex: "run_id",
      width: 190,
      render: (runId: string) => (
        <Typography.Text copyable={{ text: runId }} ellipsis>
          {runId}
        </Typography.Text>
      ),
    },
    { title: "股票代码", dataIndex: "symbol", width: 110 },
    { title: "市场", dataIndex: "market", width: 90 },
    { title: "触发方式", dataIndex: "trigger_method", width: 150 },
    { title: "Workflow", dataIndex: "workflow", width: 170 },
    {
      title: "状态",
      dataIndex: "status",
      width: 110,
      render: (value: string) => <StatusTag value={value} />,
    },
    {
      title: "开始时间",
      dataIndex: "created_at",
      width: 180,
      render: formatDateTime,
    },
    {
      title: "完成时间",
      dataIndex: "finished_at",
      width: 180,
      render: formatDateTime,
    },
    { title: "最终 Decision", dataIndex: "final_decision", width: 130 },
    {
      title: "置信度",
      dataIndex: "confidence",
      width: 100,
      render: formatPercent,
    },
    {
      title: "错误状态",
      dataIndex: "error_type",
      width: 150,
      render: (value: string | null) => value || "-",
    },
    {
      title: "操作",
      key: "actions",
      fixed: "right",
      width: 130,
      render: (_value, record) => (
        <Button
          type="link"
          onClick={(event) => {
            event.stopPropagation();
            navigate(`/research/${encodeURIComponent(record.run_id)}`);
          }}
        >
          详情
        </Button>
      ),
    },
  ];

  function applyFilters(values: ResearchRunFilters) {
    const next = new URLSearchParams();
    for (const [key, value] of Object.entries(values)) {
      if (value) next.set(key, value);
    }
    next.set("page", "1");
    setSearchParams(next);
  }

  function changePage(pagination: TablePaginationConfig) {
    const next = new URLSearchParams(searchParams);
    next.set("page", String(pagination.current ?? 1));
    setSearchParams(next);
  }

  return (
    <section className="research-page">
      <div className="page-heading">
        <div>
          <Typography.Title level={2}>Research Runs</Typography.Title>
          <Typography.Text type="secondary">
            来自当前 AIOS 后端持久化 Research Run。
          </Typography.Text>
        </div>
        <Link to="/research/new">
          <Button type="primary">发起研究</Button>
        </Link>
      </div>

      <Card className="tool-card" title="筛选">
        <Form form={form} layout="inline" onFinish={applyFilters}>
          <Form.Item name="symbol" label="股票代码">
            <Input allowClear autoComplete="off" />
          </Form.Item>
          <Form.Item name="market" label="市场">
            <Input allowClear autoComplete="off" />
          </Form.Item>
          <Form.Item name="status" label="状态">
            <Select
              allowClear
              className="filter-select"
              options={[
                { value: "running", label: "running" },
                { value: "completed", label: "completed" },
                { value: "failed", label: "failed" },
              ]}
            />
          </Form.Item>
          <Form.Item name="workflow" label="Workflow">
            <Input allowClear autoComplete="off" />
          </Form.Item>
          <Form.Item name="created_from" label="开始日期">
            <Input allowClear autoComplete="off" placeholder="2026-07-28T00:00:00Z" />
          </Form.Item>
          <Form.Item name="created_to" label="结束日期">
            <Input allowClear autoComplete="off" placeholder="2026-07-29T00:00:00Z" />
          </Form.Item>
          <Form.Item name="sort" label="排序">
            <Select
              allowClear
              className="filter-select"
              options={[
                { value: "-created_at", label: "创建时间倒序" },
                { value: "created_at", label: "创建时间正序" },
                { value: "-finished_at", label: "完成时间倒序" },
                { value: "symbol", label: "股票代码正序" },
                { value: "status", label: "状态正序" },
              ]}
            />
          </Form.Item>
          <Space>
            <Button type="primary" htmlType="submit" aria-label="筛选">
              筛选
            </Button>
            <Button onClick={() => applyFilters({})}>重置</Button>
          </Space>
        </Form>
      </Card>

      {queryError ? <ErrorState message={errorMessage(queryError)} /> : null}

      <Table
        rowKey="run_id"
        columns={columns}
        dataSource={rows}
        loading={list.isLoading || list.isFetching}
        locale={{ emptyText: <EmptyState description="暂无 Research Run" /> }}
        pagination={{ current, pageSize: PAGE_SIZE, total, showSizeChanger: false }}
        scroll={{ x: 1600 }}
        onChange={changePage}
        onRow={(record) => ({
          onClick: () => navigate(`/research/${encodeURIComponent(record.run_id)}`),
        })}
      />
    </section>
  );
}

function errorMessage(error: unknown) {
  if (error instanceof ApiError) return error.readableMessage;
  if (error instanceof Error) return error.message;
  return "Backend request failed";
}
