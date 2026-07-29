import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Button, Card, Descriptions, Popconfirm, Space, Typography, message } from "antd";
import { Link, useParams } from "react-router-dom";

import {
  BusinessStatusTag,
  EmptyBusinessState,
  LongText,
  TechnicalDetails,
  UserReadableError,
} from "../../../shared/businessComponents";
import {
  displayAction,
  displayLearningType,
  displayStatus,
} from "../../../shared/displayMappings";
import { formatDateTime, formatPercent, formatValue } from "../../../shared/formatters";
import { learningApi } from "../api";
import type { LearningDetail } from "../types";

type ReviewAction = "approve" | "reject" | "defer";

export function LearningDetailPage() {
  const { learningId } = useParams();
  const queryClient = useQueryClient();
  const [messageApi, contextHolder] = message.useMessage();
  const detail = useQuery({
    queryKey: ["learning-detail", learningId],
    queryFn: () => learningApi.detail(learningId!),
    enabled: Boolean(learningId),
  });
  const review = useMutation({
    mutationFn: (action: ReviewAction) => runReviewAction(action, learningId!),
    onSuccess: async () => {
      messageApi.success("学习建议审核状态已更新");
      await queryClient.invalidateQueries({ queryKey: ["learning-detail", learningId] });
      await queryClient.invalidateQueries({ queryKey: ["learning-proposals"] });
    },
    onError: () => {
      messageApi.error("审核失败，请刷新后重试");
    },
  });

  if (detail.isLoading) return <Typography.Text>正在加载...</Typography.Text>;
  if (detail.error) return <UserReadableError error={detail.error} />;
  if (!detail.data) return <EmptyBusinessState description="没有找到学习建议" />;

  return (
    <section className="learning-detail-page">
      {contextHolder}
      <div className="page-heading">
        <div>
          <Typography.Title level={2}>学习建议详情</Typography.Title>
          <Typography.Text type="secondary">
            proposal_only：审核只改变建议状态，不会自动修改长期权重。
          </Typography.Text>
        </div>
        <Space>
          <Link to="/learning">
            <Button>返回学习列表</Button>
          </Link>
          <ReviewButtons
            disabled={detail.data.learning.approval_status !== "pending"}
            loading={review.isPending}
            onAction={(action) => review.mutate(action)}
          />
        </Space>
      </div>

      <Space orientation="vertical" className="full-width" size="middle">
        <LearningSummary detail={detail.data} />
        <ReadableDiff detail={detail.data} />
        <SupportContext detail={detail.data} />
        <TechnicalDetails data={safeTechnical(detail.data.technical_details)} />
      </Space>
    </section>
  );
}

function LearningSummary({ detail }: { detail: LearningDetail }) {
  const learning = detail.learning;
  return (
    <Card className="tool-card" title="建议摘要">
      <Descriptions bordered size="small" column={2}>
        <Descriptions.Item label="建议类型">
          {displayLearningType(learning.learning_type)}
        </Descriptions.Item>
        <Descriptions.Item label="审核状态">
          <BusinessStatusTag value={learning.approval_status} />
        </Descriptions.Item>
        <Descriptions.Item label="调整对象">{learning.target}</Descriptions.Item>
        <Descriptions.Item label="创建时间">
          {formatDateTime(learning.created_at)}
        </Descriptions.Item>
        <Descriptions.Item label="建议原因">
          <LongText text={learning.reason} />
        </Descriptions.Item>
      </Descriptions>
    </Card>
  );
}

function ReadableDiff({ detail }: { detail: LearningDetail }) {
  return (
    <Card className="tool-card" title="当前配置与建议配置">
      <Descriptions bordered size="small" column={2}>
        <Descriptions.Item label="当前配置">
          {detail.current_value_summary}
        </Descriptions.Item>
        <Descriptions.Item label="建议配置">
          {detail.proposed_value_summary}
        </Descriptions.Item>
        <Descriptions.Item label="差异对比">{detail.change_summary}</Descriptions.Item>
        <Descriptions.Item label="预期效果">
          {formatValue(detail.technical_details.expected_effect)}
        </Descriptions.Item>
        <Descriptions.Item label="潜在风险">
          {formatValue(detail.technical_details.risks)}
        </Descriptions.Item>
        <Descriptions.Item label="样本量说明">
          {formatValue(detail.technical_details.sample_size)}
        </Descriptions.Item>
      </Descriptions>
    </Card>
  );
}

function SupportContext({ detail }: { detail: LearningDetail }) {
  return (
    <Card className="tool-card" title="支持依据与关联记录">
      <Descriptions bordered size="small" column={2}>
        <Descriptions.Item label="对应研究">
          {detail.research_run ? (
            <Link to={`/research/${encodeURIComponent(detail.research_run.run_id)}`}>
              查看研究
            </Link>
          ) : (
            "-"
          )}
        </Descriptions.Item>
        <Descriptions.Item label="对应决策">
          {detail.decision ? displayAction(detail.decision.action) : "-"}
        </Descriptions.Item>
        <Descriptions.Item label="对应结算">
          {detail.settlement ? (
            <Link to={`/reviews/${encodeURIComponent(detail.settlement.outcome_id)}`}>
              查看复盘
            </Link>
          ) : (
            "-"
          )}
        </Descriptions.Item>
        <Descriptions.Item label="对应复盘">
          {detail.review?.review_summary ?? "-"}
        </Descriptions.Item>
        <Descriptions.Item label="方向评价">
          {detail.evaluation ? displayStatus(detail.evaluation.directional_result) : "-"}
        </Descriptions.Item>
        <Descriptions.Item label="收益评价">
          {detail.evaluation ? displayStatus(detail.evaluation.return_result) : "-"}
        </Descriptions.Item>
        <Descriptions.Item label="风控评价">
          {detail.evaluation ? displayStatus(detail.evaluation.risk_result) : "-"}
        </Descriptions.Item>
        <Descriptions.Item label="实际收益率">
          {formatPercent(detail.settlement?.return_rate)}
        </Descriptions.Item>
      </Descriptions>
    </Card>
  );
}

function ReviewButtons({
  disabled,
  loading,
  onAction,
}: {
  disabled: boolean;
  loading: boolean;
  onAction: (action: ReviewAction) => void;
}) {
  return (
    <Space>
      <Popconfirm
        title="确认批准这条学习建议？"
        description="批准只更新审核状态，不会自动修改长期权重。"
        okText="批准"
        cancelText="取消"
        onConfirm={() => onAction("approve")}
        disabled={disabled}
      >
        <Button type="primary" loading={loading} disabled={disabled}>
          批准
        </Button>
      </Popconfirm>
      <Popconfirm
        title="确认拒绝这条学习建议？"
        okText="拒绝"
        cancelText="取消"
        onConfirm={() => onAction("reject")}
        disabled={disabled}
      >
        <Button danger loading={loading} disabled={disabled}>
          拒绝
        </Button>
      </Popconfirm>
      <Popconfirm
        title="确认暂缓这条学习建议？"
        okText="暂缓"
        cancelText="取消"
        onConfirm={() => onAction("defer")}
        disabled={disabled}
      >
        <Button loading={loading} disabled={disabled}>
          暂缓
        </Button>
      </Popconfirm>
    </Space>
  );
}

function runReviewAction(action: ReviewAction, learningId: string) {
  if (action === "approve") return learningApi.approve(learningId);
  if (action === "reject") return learningApi.reject(learningId);
  return learningApi.defer(learningId);
}

function safeTechnical(value: Record<string, unknown>) {
  return Object.fromEntries(
    Object.entries(value).filter(([key]) => !/api_key|secret|token|password/i.test(key)),
  );
}
