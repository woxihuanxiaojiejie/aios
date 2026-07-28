import {
  Alert,
  Button,
  Card,
  Checkbox,
  Form,
  Input,
  InputNumber,
  Space,
  Table,
  Tabs,
  Tag,
  Typography,
  message,
} from "antd";
import type { ColumnsType } from "antd/es/table";
import { useState } from "react";

import { ApiError } from "../../infrastructure/api/client";
import { useWatchlist, useWatchlistMutations } from "./hooks";
import type {
  WatchlistCreateInput,
  WatchlistItem,
  WatchlistStatus,
} from "./types";

type EditState = {
  itemId: string;
  note: string;
};

export function WatchlistPage() {
  const [status, setStatus] = useState<WatchlistStatus>("active");
  const [edit, setEdit] = useState<EditState | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [form] = Form.useForm<WatchlistCreateInput>();
  const watchlist = useWatchlist(status);
  const mutations = useWatchlistMutations();

  const items = watchlist.data?.items ?? [];
  const busy =
    mutations.create.isPending ||
    mutations.update.isPending ||
    mutations.archive.isPending ||
    mutations.restore.isPending ||
    mutations.run.isPending;

  const columns: ColumnsType<WatchlistItem> = [
      {
        title: "Symbol",
        dataIndex: "symbol",
        width: 120,
        render: (symbol: string) => <Typography.Text strong>{symbol}</Typography.Text>,
      },
      { title: "Market", dataIndex: "market", width: 100 },
      {
        title: "Status",
        dataIndex: "status",
        width: 110,
        render: (value: WatchlistStatus) => (
          <Tag color={value === "active" ? "green" : "default"}>{value}</Tag>
        ),
      },
      {
        title: "Auto Research",
        dataIndex: "auto_research_enabled",
        width: 140,
        render: (enabled: boolean) => (enabled ? "Enabled" : "Disabled"),
      },
      { title: "Horizon", dataIndex: "research_horizon_days", width: 100 },
      {
        title: "Note",
        dataIndex: "note",
        render: (_note: string | null, item) =>
          edit?.itemId === item.watchlist_item_id ? (
            <div className="watchlist-edit-form">
              <label className="inline-edit-label" htmlFor={`note-${item.watchlist_item_id}`}>
                Edit note
              </label>
              <Input
                id={`note-${item.watchlist_item_id}`}
                value={edit.note}
                onChange={(event) =>
                  setEdit({ itemId: item.watchlist_item_id, note: event.target.value })
                }
              />
              <Button
                type="primary"
                disabled={busy}
                loading={mutations.update.isPending}
                onClick={() => void saveEdit(item.watchlist_item_id)}
              >
                Save
              </Button>
              <Button disabled={busy} onClick={() => setEdit(null)}>
                Cancel
              </Button>
            </div>
          ) : (
            item.note || "-"
          ),
      },
      {
        title: "Actions",
        key: "actions",
        width: 260,
        render: (_value, item) => (
          <Space wrap>
            <Button
              disabled={busy}
              onClick={() => {
                setEdit({ itemId: item.watchlist_item_id, note: item.note ?? "" });
              }}
            >
              Edit
            </Button>
            {item.status === "active" ? (
              <Button
                disabled={busy}
                loading={mutations.archive.isPending}
                onClick={() => void runAction(() => mutations.archive.mutateAsync(item.watchlist_item_id))}
              >
                Archive
              </Button>
            ) : (
              <Button
                disabled={busy}
                loading={mutations.restore.isPending}
                onClick={() => void runAction(() => mutations.restore.mutateAsync(item.watchlist_item_id))}
              >
                Restore
              </Button>
            )}
            {item.status === "active" ? (
              <Button
                disabled={busy}
                loading={mutations.run.isPending}
                onClick={() => void runAction(() => mutations.run.mutateAsync(item.watchlist_item_id))}
              >
                Run research
              </Button>
            ) : null}
          </Space>
        ),
      },
  ];

  async function createItem(values: WatchlistCreateInput) {
    setError(null);
    try {
      await mutations.create.mutateAsync({
        ...values,
        note: values.note?.trim() || null,
        auto_research_enabled: values.auto_research_enabled ?? false,
        research_horizon_days: values.research_horizon_days ?? 3,
        schedule_time: values.schedule_time || "15:00:00",
        schedule_timezone: values.schedule_timezone || "Asia/Shanghai",
      });
      form.resetFields();
      message.success("Watchlist item created");
    } catch (caught) {
      setError(errorMessage(caught));
    }
  }

  async function saveEdit(itemId: string) {
    setError(null);
    try {
      await mutations.update.mutateAsync({
        itemId,
        payload: { note: edit?.note.trim() || null },
      });
      setEdit(null);
      message.success("Watchlist item updated");
    } catch (caught) {
      setError(errorMessage(caught));
    }
  }

  async function runAction(action: () => Promise<unknown>) {
    setError(null);
    try {
      await action();
    } catch (caught) {
      setError(errorMessage(caught));
    }
  }

  const queryError = watchlist.error ? errorMessage(watchlist.error) : null;

  return (
    <section className="watchlist-page">
      <div className="page-heading">
        <Typography.Title level={2}>Watchlist</Typography.Title>
        <Typography.Text type="secondary">
          Backed by the current AIOS backend Watchlist API.
        </Typography.Text>
      </div>

      {error || queryError ? (
        <Alert
          type="error"
          showIcon
          title={error ?? queryError}
          className="page-alert"
        />
      ) : null}

      <Card title="Create watchlist item" className="tool-card">
        <Form
          form={form}
          layout="vertical"
          onFinish={(values) => void createItem(values)}
          initialValues={{
            auto_research_enabled: false,
            research_horizon_days: 3,
            schedule_time: "15:00:00",
            schedule_timezone: "Asia/Shanghai",
          }}
        >
          <div className="watchlist-form-grid">
            <Form.Item name="symbol" label="Symbol" rules={[{ required: true }]}>
              <Input autoComplete="off" />
            </Form.Item>
            <Form.Item name="market" label="Market" rules={[{ required: true }]}>
              <Input autoComplete="off" />
            </Form.Item>
            <Form.Item name="note" label="Note">
              <Input />
            </Form.Item>
            <Form.Item name="research_horizon_days" label="Research horizon">
              <InputNumber min={1} max={365} className="full-width" />
            </Form.Item>
            <Form.Item name="schedule_time" label="Schedule time">
              <Input />
            </Form.Item>
            <Form.Item name="schedule_timezone" label="Schedule timezone">
              <Input />
            </Form.Item>
            <Form.Item
              name="auto_research_enabled"
              valuePropName="checked"
              className="watchlist-checkbox"
            >
              <Checkbox>Auto research enabled</Checkbox>
            </Form.Item>
          </div>
          <Button
            type="primary"
            htmlType="submit"
            disabled={busy}
            loading={mutations.create.isPending}
          >
            Create
          </Button>
        </Form>
      </Card>

      <Tabs
        activeKey={status}
        onChange={(key) => setStatus(key as WatchlistStatus)}
        items={[
          { key: "active", label: "Active" },
          { key: "archived", label: "Archived" },
        ]}
      />
      <Table
        rowKey="watchlist_item_id"
        columns={columns}
        dataSource={items}
        loading={watchlist.isFetching}
        pagination={false}
        scroll={{ x: 980 }}
      />
    </section>
  );
}

function errorMessage(error: unknown) {
  if (error instanceof ApiError) return error.readableMessage;
  if (error instanceof Error) return error.message;
  return "Request failed.";
}
