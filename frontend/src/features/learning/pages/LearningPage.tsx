import { useQuery } from "@tanstack/react-query";
import { Card, Select, Table, Typography } from "antd";
import type { ColumnsType } from "antd/es/table";
import { Link, useSearchParams } from "react-router-dom";

import type { Learning } from "../../../infrastructure/api/research";
import {
  BusinessStatusTag,
  EmptyBusinessState,
  LongText,
  UserReadableError,
} from "../../../shared/businessComponents";
import { displayLearningType } from "../../../shared/displayMappings";
import { formatDateTime } from "../../../shared/formatters";
import { learningApi } from "../api";

export function LearningPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const includeTestData = searchParams.get("include_test_data") === "true";
  const learnings = useQuery({
    queryKey: ["learning-proposals", includeTestData],
    queryFn: () => learningApi.list({ includeTestData }),
  });

  const columns: ColumnsType<Learning> = [
    {
      title: "建议类型",
      dataIndex: "learning_type",
      width: 170,
      render: displayLearningType,
    },
    { title: "调整对象", dataIndex: "target", width: 180 },
    {
      title: "当前值",
      dataIndex: "before",
      width: 180,
      render: summarizeValue,
    },
    {
      title: "建议值",
      dataIndex: "after",
      width: 180,
      render: summarizeValue,
    },
    {
      title: "调整幅度",
      width: 150,
      render: (_value, record) => changeSummary(record.before, record.after),
    },
    {
      title: "建议原因",
      dataIndex: "reason",
      width: 260,
      render: (value: string) => <LongText text={value} maxLength={72} />,
    },
    { title: "样本数量", width: 100, render: () => "未记录" },
    { title: "主要风险", width: 180, render: () => "需人工审核" },
    {
      title: "当前状态",
      dataIndex: "approval_status",
      width: 120,
      render: (value: string) => <BusinessStatusTag value={value} />,
    },
    {
      title: "创建时间",
      dataIndex: "created_at",
      width: 180,
      render: formatDateTime,
    },
    {
      title: "查看详情",
      dataIndex: "learning_id",
      fixed: "right",
      width: 120,
      render: (value: string) => (
        <Link to={`/learning/${encodeURIComponent(value)}`}>查看详情</Link>
      ),
    },
  ];

  return (
    <section className="learning-page">
      <div className="page-heading">
        <div>
          <Typography.Title level={2}>学习</Typography.Title>
          <Typography.Text type="secondary">
            AIOS 只提出学习建议，批准、拒绝或暂缓均需要人工审核。
          </Typography.Text>
        </div>
      </div>

      {learnings.error ? <UserReadableError error={learnings.error} /> : null}

      <Card
        className="tool-card"
        title="学习建议"
        extra={
          <Select
            aria-label="测试数据"
            placeholder="测试数据"
            allowClear
            value={includeTestData ? "true" : undefined}
            style={{ width: 160 }}
            options={[{ value: "true", label: "显示测试数据" }]}
            onChange={(value) => {
              const next = new URLSearchParams(searchParams);
              if (value === "true") next.set("include_test_data", "true");
              else next.delete("include_test_data");
              setSearchParams(next);
            }}
          />
        }
      >
        <Table
          rowKey="learning_id"
          columns={columns}
          dataSource={learnings.data?.items ?? []}
          loading={learnings.isLoading || learnings.isFetching}
          locale={{ emptyText: <EmptyBusinessState description="暂无学习建议" /> }}
          pagination={{ pageSize: 10, showSizeChanger: false }}
          scroll={{ x: 1700 }}
        />
      </Card>
    </section>
  );
}

export function summarizeValue(value: unknown) {
  if (value && typeof value === "object" && !Array.isArray(value)) {
    return Object.entries(value)
      .slice(0, 3)
      .map(([key, current]) => `${key}：${String(current)}`)
      .join("；");
  }
  if (Array.isArray(value)) return value.length ? `${value.length} 项` : "-";
  return value === null || value === undefined || value === "" ? "-" : String(value);
}

function changeSummary(before: unknown, after: unknown) {
  if (
    before &&
    after &&
    typeof before === "object" &&
    typeof after === "object" &&
    !Array.isArray(before) &&
    !Array.isArray(after) &&
    "weight" in before &&
    "weight" in after
  ) {
    return `${String(before.weight)} → ${String(after.weight)}`;
  }
  return "查看详情";
}
