import { useQuery } from "@tanstack/react-query";
import { Alert, Button, Card, Col, Descriptions, Empty, Row, Space, Statistic, Table, Tag, Typography } from "antd";
import type { ColumnsType } from "antd/es/table";
import { Link } from "react-router-dom";

import { ApiError } from "../../../infrastructure/api/client";
import { TechnicalDetails } from "../../../shared/businessComponents";
import { displayProviderStatus, displayRuntimeStatus } from "../../../shared/displayMappings";
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
  if (!status.data) return <EmptyState description="暂无系统运行状态数据" />;

  return (
    <section className="system-status-page">
      <div className="page-heading">
        <div>
          <Typography.Title level={2}>系统运行状态</Typography.Title>
          <Typography.Text type="secondary">
            最近检查时间：{formatDateTime(status.data.generated_at)}
          </Typography.Text>
        </div>
        <Button onClick={() => void status.refetch()}>刷新</Button>
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
    <Card className="tool-card" title="系统总体状态">
      <Space orientation="vertical" className="full-width" size="middle">
        {summary.issues.length > 0 ? (
          <Alert
            type={summary.overall_status === "unavailable" ? "error" : "warning"}
            showIcon
            message="当前存在需要处理的问题"
            description={
              <Space orientation="vertical" className="full-width">
                {summary.issues.map((issue, index) => (
                  <Typography.Text key={`${issue}-${index}`}>{systemMessage(issue)}</Typography.Text>
                ))}
                <TechnicalDetails data={sanitizeTechnical(summary.issues)} />
              </Space>
            }
          />
        ) : null}
        <Descriptions bordered column={{ xs: 1, md: 2 }}>
          <Descriptions.Item label="总体状态">
            <RuntimeStatusTag status={summary.overall_status} />
          </Descriptions.Item>
          <Descriptions.Item label="最近检查时间">
            {formatDateTime(summary.generated_at)}
          </Descriptions.Item>
          <Descriptions.Item label="应用版本">
            {value(summary.application.version)}
          </Descriptions.Item>
          <Descriptions.Item label="代码提交">
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
      component: "应用",
      status: summary.application.status,
      last_check: summary.application.checked_at,
      message: summary.application.message,
      technical: summary.application.message,
    },
    {
      component: "数据库",
      status: summary.database.status,
      last_check: summary.database.checked_at,
      message: databaseMessage(summary.database),
      technical: summary.database.message,
    },
    {
      component: "调度器",
      status: summary.scheduler.status,
      last_check: summary.scheduler.last_heartbeat_at,
      message: summary.scheduler.message,
      technical: summary.scheduler.message,
    },
  ];
  const columns: ColumnsType<(typeof rows)[number]> = [
    { title: "组件", dataIndex: "component", width: 180 },
    {
      title: "状态",
      dataIndex: "status",
      width: 140,
      render: (status: SystemStatus) => <RuntimeStatusTag status={status} />,
    },
    { title: "最近检查", dataIndex: "last_check", width: 220, render: formatDateTime },
    {
      title: "问题原因",
      dataIndex: "message",
      render: (message: string | null | undefined, row) => (
        <Space orientation="vertical" size={4}>
          <Typography.Text>{systemMessage(message)}</Typography.Text>
          {row.technical ? <TechnicalDetails data={sanitizeTechnical(row.technical)} /> : null}
        </Space>
      ),
    },
  ];
  return (
    <Card className="tool-card" title="核心组件">
      <Table rowKey="component" columns={columns} dataSource={rows} pagination={false} />
    </Card>
  );
}

function SchedulerJobs({ jobs }: { jobs: Record<string, SchedulerJobStatus> }) {
  const rows = Object.entries(jobs).map(([job, detail]) => ({
    job,
    job_name: displayJobName(job),
    ...detail,
  }));
  const columns: ColumnsType<(typeof rows)[number]> = [
    { title: "任务", dataIndex: "job_name", width: 220 },
    { title: "是否启用", dataIndex: "enabled", width: 120, render: booleanText },
    {
      title: "状态",
      dataIndex: "status",
      width: 140,
      render: (status: SystemStatus) => <RuntimeStatusTag status={status} />,
    },
    { title: "最近运行", dataIndex: "last_completed_at", width: 220, render: formatDateTime },
    { title: "最近结果", dataIndex: "last_result", render: value },
    {
      title: "错误原因",
      dataIndex: "last_error",
      render: (error: string | null | undefined) =>
        error ? (
          <Space orientation="vertical" size={4}>
            <Typography.Text>{systemMessage(error)}</Typography.Text>
            <TechnicalDetails data={sanitizeTechnical(error)} />
          </Space>
        ) : (
          "-"
        ),
    },
  ];
  return (
    <Card className="tool-card" title="调度任务">
      <Table
        rowKey="job"
        columns={columns}
        dataSource={rows}
        pagination={false}
        locale={{ emptyText: <Empty description="暂无调度任务状态" /> }}
        scroll={{ x: 1100 }}
      />
    </Card>
  );
}

function PendingWork({ summary }: { summary: SystemStatusSummary }) {
  const queues = summary.queues;
  return (
    <Card className="tool-card" title="待处理工作">
      <Row gutter={[12, 12]}>
        <Col xs={24} sm={12} lg={6}>
          <Statistic title="等待研究" value={queues.research_due} />
          <Link to="/research">进入研究</Link>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Statistic title="等待结算" value={queues.settlement_due} />
          <Link to="/reviews">进入复盘</Link>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Statistic title="失败研究" value={queues.failed_research_runs} />
          <Link to="/research">进入研究</Link>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Statistic title="可恢复研究" value={queues.resumable_research_runs} />
          <Link to="/research">进入研究</Link>
        </Col>
      </Row>
    </Card>
  );
}

function Providers({ providers }: { providers: ProviderStatus[] }) {
  const columns: ColumnsType<ProviderStatus> = [
    { title: "提供方", dataIndex: "provider", width: 160 },
    { title: "模型", dataIndex: "model", width: 260, render: value },
    { title: "是否配置", dataIndex: "configured", width: 140, render: booleanText },
    {
      title: "状态",
      dataIndex: "status",
      width: 160,
      render: (status: SystemStatus) => <ProviderStatusTag status={status} />,
    },
    {
      title: "问题原因",
      dataIndex: "message",
      render: (message: string | null | undefined) =>
        message ? (
          <Space orientation="vertical" size={4}>
            <Typography.Text>{systemMessage(message)}</Typography.Text>
            <TechnicalDetails data={sanitizeTechnical(message)} />
          </Space>
        ) : (
          "-"
        ),
    },
  ];
  return (
    <Card className="tool-card" title="数据提供方与大模型提供方">
      <Table
        rowKey={(row) => `${row.provider}:${row.model ?? "none"}`}
        columns={columns}
        dataSource={providers}
        pagination={false}
        locale={{ emptyText: <Empty description="暂无提供方状态" /> }}
        scroll={{ x: 1000 }}
      />
    </Card>
  );
}

function RuntimeStatusTag({ status }: { status: SystemStatus }) {
  return <Tag color={statusColor(status)}>{displayRuntimeStatus(status)}</Tag>;
}

function ProviderStatusTag({ status }: { status: SystemStatus }) {
  return <Tag color={statusColor(status)}>{displayProviderStatus(status)}</Tag>;
}

function databaseMessage(database: DatabaseStatus) {
  const latency = database.latency_ms === null ? null : `${database.latency_ms}ms`;
  const backend = database.backend === "postgresql" ? "PostgreSQL" : value(database.backend);
  return [backend, latency, database.message ? systemMessage(database.message) : null]
    .filter(Boolean)
    .join(" · ");
}

function value(input: string | number | null | undefined) {
  return input === null || input === undefined || input === "" ? "-" : String(input);
}

function booleanText(input: boolean) {
  return input ? "是" : "否";
}

function errorMessage(error: unknown) {
  if (error instanceof ApiError) return systemMessage(error.readableMessage);
  return "系统运行状态读取失败，请稍后重试。";
}

function displayJobName(job: string) {
  if (job === "research_due_scan") return "自动研究扫描";
  if (job === "settlement_due_scan") return "自动结算扫描";
  return "未知调度任务";
}

function systemMessage(message: string | null | undefined) {
  if (!message) return "-";
  const normalized = message.toLowerCase();
  if (normalized.includes("heartbeat") && normalized.includes("expired")) {
    return "调度器心跳已过期或不可用，请检查调度器进程是否正在运行。";
  }
  if (normalized.includes("heartbeat") && normalized.includes("not been recorded")) {
    return "尚未记录调度器心跳，请确认调度器进程是否已经启动。";
  }
  if (normalized.includes("heartbeat") && normalized.includes("current")) {
    return "调度器心跳正常。";
  }
  if (normalized.includes("system status failed")) {
    return "系统运行状态读取失败，请稍后重试。";
  }
  if (normalized.includes("local config valid")) {
    return "本地配置检查通过。";
  }
  if (normalized.includes("not configured")) {
    return "尚未配置。";
  }
  if (normalized.includes("invalid")) {
    return "配置无效，请检查系统配置。";
  }
  if (normalized.includes("select 1 ok")) {
    return "数据库轻量查询成功。";
  }
  return message;
}

function statusColor(status: SystemStatus) {
  return status === "healthy"
    ? "green"
    : status === "degraded"
      ? "orange"
      : status === "unavailable"
        ? "red"
        : status === "not_configured"
          ? "default"
          : "blue";
}

type TechnicalValue =
  | string
  | number
  | boolean
  | null
  | undefined
  | TechnicalValue[]
  | { [key: string]: TechnicalValue };

function sanitizeTechnical(data: unknown): TechnicalValue {
  if (Array.isArray(data)) return data.map(sanitizeTechnical);
  if (data && typeof data === "object") {
    return Object.fromEntries(
      Object.entries(data).map(([key, value]) => [
        sensitiveKey(key) ? "已隐藏敏感字段" : key,
        sensitiveKey(key) ? "[已隐藏]" : sanitizeTechnical(value),
      ]),
    );
  }
  if (data === null || data === undefined) return data;
  if (typeof data === "number" || typeof data === "boolean") return data;
  if (typeof data !== "string") return String(data);
  return data
    .replace(/(api[_-]?key|secret|token|password|authorization|database[_-]?url)\s*[:=]\s*[^;\s]+/gi, "$1=[已隐藏]")
    .replace(/Bearer\s+[A-Za-z0-9._~+/=-]+/gi, "Bearer [已隐藏]");
}

function sensitiveKey(key: string) {
  return /api[_-]?key|secret|token|password|authorization|database[_-]?url/i.test(key);
}
