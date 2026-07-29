import { Alert, Empty, Skeleton } from "antd";

import { BusinessStatusTag } from "./businessComponents";
import { formatDateTime, formatPercent } from "./formatters";

export function StatusTag({ value }: { value: string | null | undefined }) {
  return <BusinessStatusTag value={value} />;
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

export { formatDateTime, formatPercent };
