import { Alert, Button, Collapse, Empty, Space, Tag, Typography } from "antd";
import { useMemo, useState } from "react";

import { displayStatus } from "./displayMappings";
import { userReadableError } from "./errorMessages";

type StatusTone = "success" | "warning" | "error" | "processing" | "default";

export function BusinessStatusTag({ value }: { value: string | null | undefined }) {
  return <Tag color={statusColor(value)}>{displayStatus(value)}</Tag>;
}

export function TechnicalDetails({
  data,
  title = "技术详情",
}: {
  data: unknown;
  title?: string;
}) {
  const content = useMemo(() => safeSerialize(data), [data]);
  return (
    <Collapse
      ghost
      items={[
        {
          key: "technical",
          label: title,
          children: <pre className="json-block">{content}</pre>,
        },
      ]}
    />
  );
}

export function CopyableId({
  value,
  label = "内部编号",
}: {
  value: string | null | undefined;
  label?: string;
}) {
  if (!value) return <>-</>;
  return (
    <Space size={6} className="technical-id">
      <Typography.Text type="secondary">{label}</Typography.Text>
      <Typography.Text copyable={{ text: value }} type="secondary" ellipsis>
        {value}
      </Typography.Text>
    </Space>
  );
}

export function LongText({
  text,
  maxLength = 120,
}: {
  text: string | null | undefined;
  maxLength?: number;
}) {
  const [expanded, setExpanded] = useState(false);
  if (!text) return <>-</>;
  if (text.length <= maxLength) return <Typography.Text>{text}</Typography.Text>;
  const visible = expanded ? text : `${text.slice(0, maxLength)}...`;
  return (
    <Space orientation="vertical" size={4}>
      <Typography.Paragraph className="long-text">{visible}</Typography.Paragraph>
      <Button type="link" size="small" onClick={() => setExpanded(!expanded)}>
        {expanded ? "收起全文" : "展开全文"}
      </Button>
    </Space>
  );
}

export function EmptyBusinessState({ description }: { description: string }) {
  return <Empty description={description} />;
}

export function UserReadableError({ error }: { error: unknown }) {
  const info = userReadableError(error);
  return (
    <Alert
      type="error"
      showIcon
      title={info.message}
      description={<TechnicalDetails data={info.technical} />}
    />
  );
}

export function LoadingState() {
  return <Typography.Text type="secondary">正在加载...</Typography.Text>;
}

function statusColor(value: string | null | undefined): StatusTone {
  if (!value) return "default";
  if (
    [
      "completed",
      "ready",
      "active",
      "approved",
      "healthy",
      "settled",
      "succeeded",
      "pass",
      "profit",
      "correct",
      "met",
      "within_limit",
    ].includes(value)
  ) {
    return "success";
  }
  if (
    [
      "failed",
      "invalid",
      "unavailable",
      "rejected",
      "fail",
      "loss",
      "incorrect",
      "missed",
      "breached",
    ].includes(value)
  ) {
    return "error";
  }
  if (
    [
      "running",
      "pending",
      "waiting_settlement",
      "degraded",
      "not_configured",
      "deferred",
      "unknown",
    ].includes(value)
  ) {
    return "warning";
  }
  return "default";
}

function safeSerialize(data: unknown) {
  try {
    return JSON.stringify(data, null, 2);
  } catch {
    return String(data);
  }
}
