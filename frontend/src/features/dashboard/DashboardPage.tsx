import { useQuery } from "@tanstack/react-query";
import { Alert, Card, Col, Row, Space, Statistic, Table, Typography } from "antd";
import type { ColumnsType } from "antd/es/table";
import { Link } from "react-router-dom";

import {
  BusinessStatusTag,
  EmptyBusinessState,
  LoadingState,
  LongText,
  UserReadableError,
} from "../../shared/businessComponents";
import {
  displayAction,
  displayAttentionType,
  displayResearchStage,
} from "../../shared/displayMappings";
import { formatDateTime, formatPercent, formatValue } from "../../shared/formatters";
import { systemApi } from "../system/api";
import type { SystemStatusSummary } from "../system/types";
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
  const system = useQuery({
    queryKey: ["system-status", "dashboard-entry"],
    queryFn: () => systemApi.status(),
    retry: false,
  });

  if (summary.isLoading) return <LoadingState />;
  if (summary.error) return <UserReadableError error={summary.error} />;
  if (!summary.data) return <EmptyBusinessState description="暂无首页数据" />;

  return (
    <section className="dashboard-page">
      <div className="page-heading">
        <div>
          <Typography.Title level={2}>AIOS 工作台首页</Typography.Title>
          <Typography.Text type="secondary">
            今天需要处理的闭环事项，以及 AIOS 最近形成的研究、复盘和学习结果。
          </Typography.Text>
        </div>
        <Typography.Text type="secondary">
          最近检查：{formatDateTime(summary.data.generated_at)}
        </Typography.Text>
      </div>

      <Space orientation="vertical" className="full-width" size="middle">
        <TodayTodo summary={summary.data} system={system.data} />
        <RecentResearchTable rows={summary.data.recent_research} />
        <AttentionTable rows={summary.data.attention_required} system={system.data} />
        <RecentReviewTable rows={summary.data.recent_settlements} />
        <SecondaryStats summary={summary.data} />
        <SystemEntry system={system.data} error={system.error} />
      </Space>
    </section>
  );
}

function TodayTodo({
  summary,
  system,
}: {
  summary: DashboardSummary;
  system: SystemStatusSummary | undefined;
}) {
  const queues = system?.queues;
  const stats = [
    ["等待研究", queues?.research_due ?? null],
    ["研究中", summary.counts.failed_or_resumable_research_runs],
    ["等待模拟执行", countAttention(summary, "missing_simulated_execution")],
    ["等待结算", queues?.settlement_due ?? countAttention(summary, "missing_settlement")],
    ["失败但可恢复", queues ? queues.failed_research_runs + queues.resumable_research_runs : null],
    ["等待人工审核的学习建议", summary.counts.pending_learning_proposals],
  ] as const;

  return (
    <Card className="tool-card" title="今日待办">
      <Row gutter={[12, 12]}>
        {stats.map(([title, value]) => (
          <Col xs={24} sm={12} lg={8} xl={4} key={title}>
            <Statistic
              title={title}
              value={value === null ? "暂无足够数据" : value}
            />
          </Col>
        ))}
      </Row>
    </Card>
  );
}

function RecentResearchTable({ rows }: { rows: RecentResearchItem[] }) {
  const columns: ColumnsType<RecentResearchItem> = [
    { title: "时间", dataIndex: "created_at", width: 180, render: formatDateTime },
    { title: "股票代码", dataIndex: "symbol", width: 120, render: formatValue },
    { title: "市场", dataIndex: "market", width: 90, render: formatValue },
    {
      title: "最终决策",
      dataIndex: "decision_action",
      width: 120,
      render: displayAction,
    },
    {
      title: "置信度",
      dataIndex: "confidence",
      width: 110,
      render: formatPercent,
    },
    {
      title: "当前阶段",
      dataIndex: "current_loop_stage",
      width: 150,
      render: displayResearchStage,
    },
    {
      title: "查看详情",
      dataIndex: "run_id",
      width: 120,
      render: (value: string) => (
        <Link to={`/research/${encodeURIComponent(value)}`}>查看研究</Link>
      ),
    },
  ];
  return (
    <Card className="tool-card" title="最新研究结果">
      <Table
        rowKey="run_id"
        columns={columns}
        dataSource={rows}
        pagination={false}
        locale={{ emptyText: <EmptyBusinessState description="暂无最近研究结果" /> }}
        scroll={{ x: 900 }}
      />
    </Card>
  );
}

function AttentionTable({
  rows,
  system,
}: {
  rows: AttentionRequiredItem[];
  system: SystemStatusSummary | undefined;
}) {
  const systemIssues = system?.issues ?? [];
  const columns: ColumnsType<AttentionRequiredItem> = [
    {
      title: "类型",
      dataIndex: "type",
      width: 160,
      render: displayAttentionType,
    },
    { title: "股票代码", dataIndex: "symbol", width: 120, render: formatValue },
    {
      title: "当前阶段",
      dataIndex: "current_stage",
      width: 180,
      render: displayResearchStage,
    },
    {
      title: "缺失阶段",
      dataIndex: "missing_stage",
      width: 160,
      render: displayResearchStage,
    },
    { title: "时间", dataIndex: "created_at", width: 180, render: formatDateTime },
    {
      title: "详情",
      dataIndex: "detail_id",
      width: 120,
      render: (_value: string, record) => <Link to={record.detail_path}>查看处理</Link>,
    },
  ];
  return (
    <Card className="tool-card" title="待处理异常">
      <Space orientation="vertical" className="full-width" size="middle">
        {systemIssues.length > 0 ? (
          <Alert
            type="warning"
            showIcon
            message="系统存在需要处理的问题"
            description={systemIssues.join("；")}
          />
        ) : null}
        <Table
          rowKey={(row) => `${row.type}:${row.detail_id}`}
          columns={columns}
          dataSource={rows}
          pagination={false}
          locale={{ emptyText: <EmptyBusinessState description="暂无待处理异常" /> }}
          scroll={{ x: 900 }}
        />
      </Space>
    </Card>
  );
}

function RecentReviewTable({ rows }: { rows: RecentSettlementItem[] }) {
  const columns: ColumnsType<RecentSettlementItem> = [
    { title: "时间", dataIndex: "settled_at", width: 180, render: formatDateTime },
    { title: "股票代码", dataIndex: "symbol", width: 120, render: formatValue },
    {
      title: "原始决策",
      dataIndex: "decision_action",
      width: 120,
      render: displayAction,
    },
    { title: "入场价", dataIndex: "entry_price", width: 110, render: formatValue },
    { title: "退出价", dataIndex: "exit_price", width: 110, render: formatValue },
    {
      title: "实际收益",
      width: 130,
      render: (_value, record) =>
        record.return_rate ? formatPercent(record.return_rate) : formatValue(record.pnl),
    },
    {
      title: "评价摘要",
      dataIndex: "evaluation_summary",
      width: 260,
      render: (value: string | null) => <LongText text={value} maxLength={64} />,
    },
    {
      title: "查看详情",
      dataIndex: "settlement_id",
      width: 120,
      render: (value: string) => (
        <Link to={`/reviews/${encodeURIComponent(value)}`}>查看复盘</Link>
      ),
    },
  ];
  return (
    <Card className="tool-card" title="最近复盘结果">
      <Table
        rowKey="settlement_id"
        columns={columns}
        dataSource={rows}
        pagination={false}
        locale={{ emptyText: <EmptyBusinessState description="暂无最近复盘结果" /> }}
        scroll={{ x: 1100 }}
      />
    </Card>
  );
}

function SecondaryStats({ summary }: { summary: DashboardSummary }) {
  const counts = summary.counts;
  const stats = [
    ["研究总数", counts.research_runs],
    ["已完成研究", counts.completed_research_runs],
    ["决策数量", counts.decisions],
    ["交易计划数量", counts.trade_plans],
    ["模拟执行数量", counts.simulated_executions],
    ["结果结算数量", counts.settlements],
  ] as const;
  return (
    <Card className="tool-card" title="辅助统计">
      <Row gutter={[12, 12]}>
        {stats.map(([title, value]) => (
          <Col xs={24} sm={12} lg={8} xl={4} key={title}>
            <Statistic title={title} value={value} />
          </Col>
        ))}
      </Row>
    </Card>
  );
}

function SystemEntry({
  system,
  error,
}: {
  system: SystemStatusSummary | undefined;
  error: unknown;
}) {
  return (
    <Card className="tool-card" title="系统状态入口">
      <Space orientation="vertical" size={6}>
        {system ? (
          <Space>
            <Typography.Text>系统总体状态</Typography.Text>
            <BusinessStatusTag value={system.overall_status} />
            <Typography.Text type="secondary">
              最近检查：{formatDateTime(system.generated_at)}
            </Typography.Text>
          </Space>
        ) : error ? (
          <Typography.Text type="warning">
            暂时无法读取系统状态，请进入系统页面查看详情。
          </Typography.Text>
        ) : (
          <Typography.Text type="secondary">正在读取系统状态...</Typography.Text>
        )}
        <Link to="/system">进入系统运行状态</Link>
      </Space>
    </Card>
  );
}

function countAttention(summary: DashboardSummary, type: string) {
  return summary.attention_required.filter((item) => item.type === type).length;
}
