import { useQuery } from "@tanstack/react-query";
import { Card, Col, Row, Space, Statistic, Table, Typography } from "antd";
import type { ColumnsType } from "antd/es/table";
import { Link } from "react-router-dom";

import { ApiError } from "../../infrastructure/api/client";
import {
  EmptyState,
  ErrorState,
  LoadingState,
  formatDateTime,
  formatPercent,
} from "../../shared/researchDisplay";
import { dashboardApi } from "./api";
import type {
  AttentionRequiredItem,
  DashboardSummary,
  RecentResearchItem,
  RecentSettlementItem,
} from "./types";

export function DashboardPage() {
  const summary = useQuery({
    queryKey: ["dashboard-summary"],
    queryFn: () => dashboardApi.summary(),
  });

  if (summary.isLoading) return <LoadingState />;
  if (summary.error) return <ErrorState message={errorMessage(summary.error)} />;
  if (!summary.data) return <EmptyState description="暂无 Dashboard 数据" />;

  return (
    <section className="dashboard-page">
      <div className="page-heading">
        <div>
          <Typography.Title level={2}>AIOS Results Summary</Typography.Title>
          <Typography.Text type="secondary">
            研究、决策、模拟执行、结算和学习结果总览
          </Typography.Text>
        </div>
        <Typography.Text type="secondary">
          Generated {formatDateTime(summary.data.generated_at)}
        </Typography.Text>
      </div>
      <Space orientation="vertical" className="full-width" size="middle">
        <SummaryCards summary={summary.data} />
        <AttentionTable rows={summary.data.attention_required} />
        <RecentResearchTable rows={summary.data.recent_research} />
        <RecentSettlementTable rows={summary.data.recent_settlements} />
        <SystemEntry />
      </Space>
    </section>
  );
}

function SummaryCards({ summary }: { summary: DashboardSummary }) {
  const counts = summary.counts;
  const stats = [
    ["Research Runs", counts.research_runs],
    ["Completed Research", counts.completed_research_runs],
    ["Simulated Executions", counts.simulated_executions],
    ["Settlements", counts.settlements],
    ["Pending Learning Proposals", counts.pending_learning_proposals],
    ["Failed / Resumable Research", counts.failed_or_resumable_research_runs],
  ] as const;
  return (
    <Card className="tool-card" title="Summary">
      <Row gutter={[12, 12]}>
        {stats.map(([title, value]) => (
          <Col xs={24} sm={12} lg={6} key={title}>
            <Statistic title={title} value={value} />
          </Col>
        ))}
      </Row>
    </Card>
  );
}

function AttentionTable({ rows }: { rows: AttentionRequiredItem[] }) {
  const columns: ColumnsType<AttentionRequiredItem> = [
    { title: "类型", dataIndex: "type", width: 220 },
    { title: "Symbol", dataIndex: "symbol", width: 120, render: text },
    { title: "当前阶段", dataIndex: "current_stage", width: 180 },
    { title: "缺失阶段", dataIndex: "missing_stage", width: 180 },
    { title: "时间", dataIndex: "created_at", width: 190, render: formatDateTime },
    {
      title: "详情",
      dataIndex: "detail_id",
      width: 220,
      render: (value: string, record) => <Link to={record.detail_path}>{value}</Link>,
    },
  ];
  return (
    <Card className="tool-card" title="待处理事项">
      <Table
        rowKey={(row) => `${row.type}:${row.detail_id}`}
        columns={columns}
        dataSource={rows}
        pagination={false}
        locale={{ emptyText: <EmptyState description="暂无需要处理的事项" /> }}
        scroll={{ x: 980 }}
      />
    </Card>
  );
}

function RecentResearchTable({ rows }: { rows: RecentResearchItem[] }) {
  const columns: ColumnsType<RecentResearchItem> = [
    { title: "时间", dataIndex: "created_at", width: 190, render: formatDateTime },
    { title: "Symbol", dataIndex: "symbol", width: 120, render: text },
    { title: "Market", dataIndex: "market", width: 100, render: text },
    { title: "Decision", dataIndex: "decision_action", width: 150, render: text },
    { title: "Confidence", dataIndex: "confidence", width: 120, render: formatPercent },
    { title: "当前阶段", dataIndex: "current_loop_stage", width: 180 },
    {
      title: "详情",
      dataIndex: "run_id",
      width: 220,
      render: (value: string) => <Link to={`/research/${encodeURIComponent(value)}`}>{value}</Link>,
    },
  ];
  return (
    <Card className="tool-card" title="最近研究结果">
      <Table
        rowKey="run_id"
        columns={columns}
        dataSource={rows}
        pagination={false}
        locale={{ emptyText: <EmptyState description="暂无最近研究结果" /> }}
        scroll={{ x: 980 }}
      />
    </Card>
  );
}

function RecentSettlementTable({ rows }: { rows: RecentSettlementItem[] }) {
  const columns: ColumnsType<RecentSettlementItem> = [
    { title: "时间", dataIndex: "settled_at", width: 190, render: formatDateTime },
    { title: "Symbol", dataIndex: "symbol", width: 120 },
    { title: "Decision", dataIndex: "decision_action", width: 150, render: text },
    { title: "Entry", dataIndex: "entry_price", width: 120, render: text },
    { title: "Exit", dataIndex: "exit_price", width: 120, render: text },
    {
      title: "Return",
      width: 140,
      render: (_value, record) => record.return_rate ?? record.pnl ?? "-",
    },
    {
      title: "Evaluation",
      dataIndex: "evaluation_summary",
      width: 260,
      render: text,
    },
    {
      title: "详情",
      dataIndex: "settlement_id",
      width: 220,
      render: (value: string) => (
        <Link to={`/settlements/${encodeURIComponent(value)}`}>{value}</Link>
      ),
    },
  ];
  return (
    <Card className="tool-card" title="最近结算结果">
      <Table
        rowKey="settlement_id"
        columns={columns}
        dataSource={rows}
        pagination={false}
        locale={{ emptyText: <EmptyState description="暂无最近结算结果" /> }}
        scroll={{ x: 1180 }}
      />
    </Card>
  );
}

function SystemEntry() {
  return (
    <Card className="tool-card" title="System 状态入口">
      <Space orientation="vertical" size={4}>
        <Typography.Text>后端、数据库、Scheduler 和 Provider 配置状态在 System 页面查看。</Typography.Text>
        <Link to="/system">Open System Status</Link>
      </Space>
    </Card>
  );
}

function text(value: string | null | undefined) {
  return value || "-";
}

function errorMessage(error: unknown) {
  if (error instanceof ApiError) return error.readableMessage;
  if (error instanceof Error) return error.message;
  return "Backend request failed";
}
