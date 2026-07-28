import { Alert, Empty, Skeleton, Tag } from "antd";

export function StatusTag({ value }: { value: string | null | undefined }) {
  const text = value || "-";
  const color =
    text === "completed" || text === "ready" || text === "active"
      ? "green"
      : text === "failed" || text === "invalid"
        ? "red"
        : text === "running"
          ? "blue"
          : text === "no_trade"
            ? "orange"
            : "default";
  return <Tag color={color}>{text}</Tag>;
}

export function LoadingState() {
  return <Skeleton active paragraph={{ rows: 8 }} />;
}

export function EmptyState({ description }: { description: string }) {
  return <Empty description={description} />;
}

export function ErrorState({ message }: { message: string }) {
  return <Alert type="error" showIcon title={message} />;
}

export function formatDateTime(value: string | null | undefined) {
  if (!value) return "-";
  return new Intl.DateTimeFormat("zh-CN", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false,
  }).format(new Date(value));
}

export function formatPercent(value: number | null | undefined) {
  if (value === null || value === undefined) return "-";
  return `${Math.round(value * 100)}%`;
}
