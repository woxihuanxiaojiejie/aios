import { useDataProvider } from "@refinedev/core";
import { useQuery } from "@tanstack/react-query";
import { Button, Card, Form, Input, Select, Space, Table, Typography } from "antd";
import type { ColumnsType, TablePaginationConfig } from "antd/es/table";
import { useEffect, useMemo } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";

import { ApiError } from "../../../infrastructure/api/client";
import {
  EmptyState,
  ErrorState,
  StatusTag,
  formatDateTime,
} from "../../../shared/researchDisplay";
import type { ExplorerFilters, SettlementListItem } from "../types";
import { IdText } from "./common";

const PAGE_SIZE = 10;

export function SettlementsPage() {
  const navigate = useNavigate();
  const dataProvider = useDataProvider();
  const [form] = Form.useForm<ExplorerFilters>();
  const [searchParams, setSearchParams] = useSearchParams();
  const current = Number(searchParams.get("page") ?? "1");
  const filters = useMemo(
    () => ({
      symbol: searchParams.get("symbol") || undefined,
      market: searchParams.get("market") || undefined,
      status: searchParams.get("status") || undefined,
      created_from: searchParams.get("created_from") || undefined,
      created_to: searchParams.get("created_to") || undefined,
      sort: searchParams.get("sort") || undefined,
    }),
    [searchParams],
  );
  useEffect(() => form.setFieldsValue(filters), [filters, form]);

  const list = useQuery({
    queryKey: ["settlements", current, filters],
    queryFn: () =>
      dataProvider().getList<SettlementListItem>({
        resource: "settlements",
        pagination: { currentPage: current, pageSize: PAGE_SIZE },
        filters: Object.entries(filters)
          .filter(([, value]) => value)
          .map(([field, value]) => ({ field, operator: "eq", value })),
      }),
  });

  const columns: ColumnsType<SettlementListItem> = [
    {
      title: "Settlement ID",
      dataIndex: "settlement_id",
      width: 210,
      render: (value: string) => <IdText value={value} />,
    },
    { title: "Symbol", dataIndex: "symbol", width: 110 },
    { title: "Market", dataIndex: "market", width: 90 },
    {
      title: "Execution ID",
      dataIndex: "execution_id",
      width: 190,
      render: (value: string | null) =>
        value ? <Link to={`/executions/${encodeURIComponent(value)}`}>{value}</Link> : "-",
    },
    {
      title: "Status",
      dataIndex: "status",
      width: 120,
      render: (value: string) => <StatusTag value={value} />,
    },
    { title: "Entry", dataIndex: "entry_price", width: 110 },
    { title: "Exit", dataIndex: "exit_price", width: 110 },
    { title: "Return", dataIndex: "return_rate", width: 110 },
    { title: "PnL", dataIndex: "pnl", width: 110 },
    { title: "Settled Time", dataIndex: "settled_at", width: 180, render: formatDateTime },
    {
      title: "Research Run",
      dataIndex: "research_run_id",
      width: 180,
      render: (value: string | null) =>
        value ? <Link to={`/research/${encodeURIComponent(value)}`}>{value}</Link> : "-",
    },
    {
      title: "Action",
      key: "action",
      fixed: "right",
      width: 110,
      render: (_value, record) => (
        <Button
          type="link"
          onClick={(event) => {
            event.stopPropagation();
            navigate(`/settlements/${encodeURIComponent(record.settlement_id)}`);
          }}
        >
          Detail
        </Button>
      ),
    },
  ];

  function applyFilters(values: ExplorerFilters) {
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

  const error = list.error ?? list.failureReason;

  return (
    <section className="research-page">
      <div className="page-heading">
        <Typography.Title level={2}>Settlements</Typography.Title>
      </div>
      <Card className="tool-card" title="Filters">
        <Form form={form} layout="inline" onFinish={applyFilters}>
          <Form.Item name="symbol" label="Symbol"><Input allowClear /></Form.Item>
          <Form.Item name="market" label="Market"><Input allowClear /></Form.Item>
          <Form.Item name="status" label="Status"><Input allowClear /></Form.Item>
          <Form.Item name="created_from" label="Created From"><Input allowClear /></Form.Item>
          <Form.Item name="created_to" label="Created To"><Input allowClear /></Form.Item>
          <Form.Item name="sort" label="Sort">
            <Select
              allowClear
              className="filter-select"
              options={[
                { value: "-settled_at", label: "Settled desc" },
                { value: "settled_at", label: "Settled asc" },
                { value: "symbol", label: "Symbol asc" },
                { value: "status", label: "Status asc" },
              ]}
            />
          </Form.Item>
          <Space>
            <Button type="primary" htmlType="submit">Filter</Button>
            <Button onClick={() => applyFilters({})}>Reset</Button>
          </Space>
        </Form>
      </Card>
      {error ? <ErrorState message={errorMessage(error)} /> : null}
      <Table
        rowKey="settlement_id"
        columns={columns}
        dataSource={list.data?.data ?? []}
        loading={list.isLoading || list.isFetching}
        locale={{ emptyText: <EmptyState description="暂无 Settlement" /> }}
        pagination={{
          current,
          pageSize: PAGE_SIZE,
          total: list.data?.total ?? 0,
          showSizeChanger: false,
        }}
        scroll={{ x: 1700 }}
        onChange={changePage}
        onRow={(record) => ({
          onClick: () => navigate(`/settlements/${encodeURIComponent(record.settlement_id)}`),
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
