import { useQuery } from "@tanstack/react-query";
import { Card, Descriptions, Space, Table, Typography } from "antd";
import type { ColumnsType } from "antd/es/table";

import { ApiError } from "../../../infrastructure/api/client";
import { researchApi, type Learning } from "../../../infrastructure/api/research";
import {
  EmptyState,
  ErrorState,
  StatusTag,
  formatDateTime,
} from "../../../shared/researchDisplay";
import { IdText } from "./common";

export function LearningProposalsPage() {
  const list = useQuery({
    queryKey: ["learning-proposals"],
    queryFn: () => researchApi.listLearnings(),
  });
  const rows = (list.data?.items ?? []).filter(
    (learning) => learning.approval_status === "pending",
  );
  const error = list.error ?? list.failureReason;

  const columns: ColumnsType<Learning> = [
    {
      title: "Proposal ID",
      dataIndex: "learning_id",
      width: 210,
      render: (value: string) => <IdText value={value} />,
    },
    { title: "Proposal Type", dataIndex: "learning_type", width: 170 },
    {
      title: "Status",
      dataIndex: "approval_status",
      width: 120,
      render: (value: string) => <StatusTag value={value} />,
    },
    { title: "Target", dataIndex: "target", width: 180 },
    {
      title: "Current Value",
      width: 220,
      render: (_value, record) => (
        <Typography.Text>{JSON.stringify(record.before)}</Typography.Text>
      ),
    },
    {
      title: "Proposed Value",
      width: 220,
      render: (_value, record) => (
        <Typography.Text>{JSON.stringify(record.after)}</Typography.Text>
      ),
    },
    {
      title: "Proposed Change",
      width: 260,
      render: (_value, record) => (
        <Typography.Text>
          {JSON.stringify(record.after)}
        </Typography.Text>
      ),
    },
    { title: "Reason", dataIndex: "reason", width: 240 },
    { title: "Supporting Evidence", width: 180, render: () => "-" },
    { title: "Expected Effect", width: 180, render: () => "-" },
    { title: "Risks", width: 120, render: () => "-" },
    {
      title: "Review Source",
      dataIndex: "review_id",
      width: 210,
      render: (value: string) => <IdText value={value} />,
    },
    { title: "Created Time", dataIndex: "created_at", width: 180, render: formatDateTime },
  ];

  return (
    <section className="research-page">
      <div className="page-heading">
        <Typography.Title level={2}>Learning Proposals</Typography.Title>
      </div>
      {error ? <ErrorState message={errorMessage(error)} /> : null}
      <Card className="tool-card">
        <Table
          rowKey="learning_id"
          columns={columns}
          dataSource={rows}
          loading={list.isLoading || list.isFetching}
          locale={{ emptyText: <EmptyState description="暂无 pending Learning Proposal" /> }}
          expandable={{
            expandedRowRender: (record) => (
              <Space orientation="vertical" className="full-width">
                <Descriptions bordered size="small" column={2}>
                  <Descriptions.Item label="Before">
                    <pre className="json-block">{JSON.stringify(record.before, null, 2)}</pre>
                  </Descriptions.Item>
                  <Descriptions.Item label="After">
                    <pre className="json-block">{JSON.stringify(record.after, null, 2)}</pre>
                  </Descriptions.Item>
                  <Descriptions.Item label="Evidence / Reasoning">
                    {record.reason}
                  </Descriptions.Item>
                </Descriptions>
              </Space>
            ),
          }}
          pagination={{ pageSize: 10, showSizeChanger: false }}
          scroll={{ x: 1300 }}
        />
      </Card>
    </section>
  );
}

function errorMessage(error: unknown) {
  if (error instanceof ApiError) return error.readableMessage;
  if (error instanceof Error) return error.message;
  return "Backend request failed";
}
