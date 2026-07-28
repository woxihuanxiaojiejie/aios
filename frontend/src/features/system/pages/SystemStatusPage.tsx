import { useQuery } from "@tanstack/react-query";
import { Alert, Button, Card, Col, Descriptions, Empty, Row, Space, Statistic, Table, Tag, Typography } from "antd";
import type { ColumnsType } from "antd/es/table";
import { Link } from "react-router-dom";

import { ApiError } from "../../../infrastructure/api/client";
import { EmptyState, ErrorState, LoadingState, formatDateTime } from "../../../shared/researchDisplay";
import { systemApi } from "../api";
import type {
  DatabaseStatus,
  ProviderStatus,
  SchedulerJobStatus,
  SystemStatus,
  SystemStatusSummary,
} from "../types";

export function SystemStatusPage() {
  const status = useQuery({
    queryKey: ["system-status"],
    queryFn: () => systemApi.status(),
  });

  if (status.isLoading) return <LoadingState />;
  if (status.error) return <ErrorState message={errorMessage(status.error)} />;
  if (!status.data) return <EmptyState description="暂无 System 状态数据" />;

  return (
    <section className="system-status-page">
      <div className="page-heading">
        <div>
          <Typography.Title level={2}>System Runtime Status</Typography.Title>
          <Typography.Text type="secondary">
            Checked {formatDateTime(status.data.generated_at)}
          </Typography.Text>
        </div>
        <Button onClick={() => void status.refetch()}>Refresh</Button>
      </div>
      <Space orientation="vertical" className="full-width" size="middle">
        <OverallStatus summary={status.data} />
        <CoreComponents summary={status.data} />
        <SchedulerJobs jobs={status.data.jobs} />
        <PendingWork summary={status.data} />
        <Providers providers={status.data.providers} />
      </Space>
    </section>
  );
}

function OverallStatus({ summary }: { summary: SystemStatusSummary }) {
  return (
    <Card className="tool-card" title="Overall Status">
      <Space orientation="vertical" className="full-width" size="middle">
        {summary.issues.length > 0 ? (
          <Alert
            type={summary.overall_status === "unavailable" ? "error" : "warning"}
            showIcon
            message="Issues"
            description={summary.issues.join("; ")}
          />
        ) : null}
        <Descriptions bordered column={{ xs: 1, md: 2 }}>
          <Descriptions.Item label="Overall">
            <RuntimeStatusTag status={summary.overall_status} />
          </Descriptions.Item>
          <Descriptions.Item label="Generated At">
            {formatDateTime(summary.generated_at)}
          </Descriptions.Item>
          <Descriptions.Item label="Application Version">
            {value(summary.application.version)}
          </Descriptions.Item>
          <Descriptions.Item label="Git Commit">
            {value(summary.application.commit)}
          </Descriptions.Item>
        </Descriptions>
      </Space>
    </Card>
  );
}

function CoreComponents({ summary }: { summary: SystemStatusSummary }) {
  const rows = [
    {
      component: "Application",
      status: summary.application.status,
      last_check: summary.application.checked_at,
      message: summary.application.message,
    },
    {
      component: "Database",
      status: summary.database.status,
      last_check: summary.database.checked_at,
      message: databaseMessage(summary.database),
    },
    {
      component: "Scheduler",
      status: summary.scheduler.status,
      last_check: summary.scheduler.last_heartbeat_at,
      message: summary.scheduler.message,
    },
  ];
  const columns: ColumnsType<(typeof rows)[number]> = [
    { title: "Component", dataIndex: "component", width: 180 },
    {
      title: "Status",
      dataIndex: "status",
      width: 140,
      render: (status: SystemStatus) => <RuntimeStatusTag status={status} />,
    },
    { title: "Last Check", dataIndex: "last_check", width: 220, render: formatDateTime },
    { title: "Message", dataIndex: "message", render: value },
  ];
  return (
    <Card className="tool-card" title="Core Components">
      <Table rowKey="component" columns={columns} dataSource={rows} pagination={false} />
    </Card>
  );
}

function SchedulerJobs({ jobs }: { jobs: Record<string, SchedulerJobStatus> }) {
  const rows = Object.entries(jobs).map(([job, detail]) => ({ job, ...detail }));
  const columns: ColumnsType<(typeof rows)[number]> = [
    { title: "Job", dataIndex: "job", width: 220 },
    { title: "Enabled", dataIndex: "enabled", width: 120, render: booleanText },
    {
      title: "Status",
      dataIndex: "status",
      width: 140,
      render: (status: SystemStatus) => <RuntimeStatusTag status={status} />,
    },
    { title: "Last Run", dataIndex: "last_completed_at", width: 220, render: formatDateTime },
    { title: "Result", dataIndex: "last_result", render: value },
    { title: "Error", dataIndex: "last_error", render: value },
  ];
  return (
    <Card className="tool-card" title="Scheduler Jobs">
      <Table
        rowKey="job"
        columns={columns}
        dataSource={rows}
        pagination={false}
        locale={{ emptyText: <Empty description="暂无 Scheduler job 状态" /> }}
        scroll={{ x: 1100 }}
      />
    </Card>
  );
}

function PendingWork({ summary }: { summary: SystemStatusSummary }) {
  const queues = summary.queues;
  return (
    <Card className="tool-card" title="Pending Work">
      <Row gutter={[12, 12]}>
        <Col xs={24} sm={12} lg={6}>
          <Statistic title="Due Research" value={queues.research_due} />
          <Link to="/research">Research</Link>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Statistic title="Due Settlement" value={queues.settlement_due} />
          <Link to="/settlements">Settlements</Link>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Statistic title="Failed Research" value={queues.failed_research_runs} />
          <Link to="/research">Research</Link>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Statistic title="Resumable Research" value={queues.resumable_research_runs} />
          <Link to="/executions">Executions</Link>
        </Col>
      </Row>
    </Card>
  );
}

function Providers({ providers }: { providers: ProviderStatus[] }) {
  const columns: ColumnsType<ProviderStatus> = [
    { title: "Provider", dataIndex: "provider", width: 160 },
    { title: "Model", dataIndex: "model", width: 260, render: value },
    { title: "Configured", dataIndex: "configured", width: 140, render: booleanText },
    {
      title: "Status",
      dataIndex: "status",
      width: 160,
      render: (status: SystemStatus) => <RuntimeStatusTag status={status} />,
    },
    { title: "Message", dataIndex: "message", render: value },
  ];
  return (
    <Card className="tool-card" title="Providers">
      <Table
        rowKey={(row) => `${row.provider}:${row.model ?? "none"}`}
        columns={columns}
        dataSource={providers}
        pagination={false}
        locale={{ emptyText: <Empty description="暂无 Provider 状态" /> }}
        scroll={{ x: 1000 }}
      />
    </Card>
  );
}

function RuntimeStatusTag({ status }: { status: SystemStatus }) {
  const color =
    status === "healthy"
      ? "green"
      : status === "degraded"
        ? "orange"
        : status === "unavailable"
          ? "red"
          : status === "not_configured"
            ? "default"
            : "blue";
  return <Tag color={color}>{status}</Tag>;
}

function databaseMessage(database: DatabaseStatus) {
  const latency = database.latency_ms === null ? null : `${database.latency_ms}ms`;
  return [database.backend, latency, database.message].filter(Boolean).join(" · ");
}

function value(input: string | number | null | undefined) {
  return input === null || input === undefined || input === "" ? "-" : String(input);
}

function booleanText(input: boolean) {
  return input ? "Yes" : "No";
}

function errorMessage(error: unknown) {
  return error instanceof ApiError ? error.readableMessage : "System status failed";
}
