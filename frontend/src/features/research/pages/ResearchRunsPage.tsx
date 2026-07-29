import { useDataProvider } from "@refinedev/core";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Button, Card, Form, Input, Select, Space, Table, Typography, message } from "antd";
import type { ColumnsType, TablePaginationConfig } from "antd/es/table";
import { useEffect, useMemo } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";

import { apiClient } from "../../../infrastructure/api/client";
import {
  BusinessStatusTag,
  EmptyBusinessState,
  TechnicalDetails,
  UserReadableError,
} from "../../../shared/businessComponents";
import {
  displayAction,
  displayResearchStage,
  displayStatus,
  displayTriggerMethod,
} from "../../../shared/displayMappings";
import { formatDateTime, formatPercent, formatValue } from "../../../shared/formatters";
import type { ResearchRunFilters, ResearchRunListItem } from "../types";

const PAGE_SIZE = 10;

export function ResearchRunsPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [form] = Form.useForm<ResearchRunFilters>();
  const [searchParams, setSearchParams] = useSearchParams();
  const dataProvider = useDataProvider();
  const [messageApi, contextHolder] = message.useMessage();
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
      include_test_data: searchParams.get("include_test_data") || undefined,
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

  const resume = useMutation({
    mutationFn: (runId: string) =>
      apiClient.post(`/research/runs/${encodeURIComponent(runId)}/resume`, {}),
    onSuccess: async () => {
      messageApi.success("恢复研究请求已提交");
      await queryClient.invalidateQueries({ queryKey: ["research-runs"] });
    },
    onError: () => {
      messageApi.error("恢复研究失败，请检查系统状态后重试");
    },
  });

  const rows = list.data?.data ?? [];
  const total = list.data?.total ?? 0;
  const queryError = list.error ?? list.failureReason;

  const columns: ColumnsType<ResearchRunListItem> = [
    {
      title: "股票",
      dataIndex: "symbol",
      width: 130,
      render: (_value, record) => (
        <Space orientation="vertical" size={0}>
          <Typography.Text strong>{record.symbol ?? "未知股票"}</Typography.Text>
          <Typography.Text type="secondary">{record.market ?? "-"}</Typography.Text>
        </Space>
      ),
    },
    {
      title: "研究触发来源",
      dataIndex: "trigger_method",
      width: 150,
      render: (_value, record) => triggerText(record),
    },
    {
      title: "初始假设摘要",
      dataIndex: "input_params",
      width: 220,
      render: (_value, record) => initialHypothesis(record),
    },
    {
      title: "研究周期",
      dataIndex: "input_params",
      width: 110,
      render: (_value, record) => researchHorizon(record),
    },
    {
      title: "当前阶段",
      dataIndex: "current_stage",
      width: 140,
      render: displayResearchStage,
    },
    {
      title: "状态",
      dataIndex: "status",
      width: 110,
      render: (value: string) => <BusinessStatusTag value={value} />,
    },
    {
      title: "最终决策",
      dataIndex: "final_decision",
      width: 120,
      render: displayAction,
    },
    {
      title: "置信度",
      dataIndex: "confidence",
      width: 100,
      render: formatPercent,
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
    {
      title: "失败原因",
      dataIndex: "error_type",
      width: 170,
      render: (_value, record) =>
        record.error_type || record.error ? displayStatus(record.error_type) : "-",
    },
    {
      title: "操作",
      key: "actions",
      fixed: "right",
      width: 170,
      render: (_value, record) => (
        <Space>
          <Button
            type="link"
            onClick={(event) => {
              event.stopPropagation();
              navigate(`/research/${encodeURIComponent(record.run_id)}`);
            }}
          >
            查看详情
          </Button>
          {canResume(record) ? (
            <Button
              type="link"
              loading={resume.isPending}
              onClick={(event) => {
                event.stopPropagation();
                resume.mutate(record.run_id);
              }}
            >
              恢复研究
            </Button>
          ) : null}
        </Space>
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
      {contextHolder}
      <div className="page-heading">
        <div>
          <Typography.Title level={2}>研究</Typography.Title>
          <Typography.Text type="secondary">
            按股票查看 AIOS 研究闭环，不需要手工串联内部编号。
          </Typography.Text>
        </div>
        <Link to="/research/new">
          <Button type="primary">发起人工研究</Button>
        </Link>
      </div>

      <Card className="tool-card" title="筛选">
        <Form form={form} layout="inline" onFinish={applyFilters}>
          <Form.Item name="symbol" label="股票代码">
            <Input allowClear autoComplete="off" placeholder="例如 600519" />
          </Form.Item>
          <Form.Item name="market" label="市场">
            <Input allowClear autoComplete="off" placeholder="例如 CN" />
          </Form.Item>
          <Form.Item name="status" label="状态">
            <Select
              allowClear
              className="filter-select"
              options={[
                { value: "running", label: "运行中" },
                { value: "completed", label: "已完成" },
                { value: "failed", label: "失败" },
              ]}
            />
          </Form.Item>
          <Form.Item name="workflow" label="研究流程">
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
          <Form.Item name="include_test_data" label="测试数据">
            <Select
              allowClear
              className="filter-select"
              options={[{ value: "true", label: "显示测试数据" }]}
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

      {queryError ? <UserReadableError error={queryError} /> : null}

      <Table
        rowKey="run_id"
        columns={columns}
        dataSource={rows}
        loading={list.isLoading || list.isFetching}
        expandable={{
          expandedRowRender: (record) => (
            <TechnicalDetails
              data={{
                run_id: record.run_id,
                research_session_id: record.research_session_id,
                workflow: record.workflow,
                raw_status: record.status,
                error_type: record.error_type,
              }}
            />
          ),
        }}
        locale={{ emptyText: <EmptyBusinessState description="暂无研究记录" /> }}
        pagination={{ current, pageSize: PAGE_SIZE, total, showSizeChanger: false }}
        scroll={{ x: 1500 }}
        onChange={changePage}
        onRow={(record) => ({
          onClick: () => navigate(`/research/${encodeURIComponent(record.run_id)}`),
        })}
      />
    </section>
  );
}

function triggerText(record: ResearchRunListItem) {
  const trigger = record.trigger_method ?? stringParam(record, "trigger_method");
  return displayTriggerMethod(trigger ?? record.workflow);
}

function initialHypothesis(record: ResearchRunListItem) {
  return (
    stringParam(record, "initial_hypothesis") ??
    stringParam(record, "hypothesis") ??
    "未记录"
  );
}

function researchHorizon(record: ResearchRunListItem) {
  const days = record.input_params.horizon_days;
  if (typeof days === "number" || typeof days === "string") return `${days} 天`;
  return formatValue(record.research_window_key);
}

function stringParam(record: ResearchRunListItem, key: string) {
  const value = record.input_params[key];
  return typeof value === "string" && value ? value : null;
}

function canResume(record: ResearchRunListItem) {
  return record.status === "failed" || record.status === "running";
}
