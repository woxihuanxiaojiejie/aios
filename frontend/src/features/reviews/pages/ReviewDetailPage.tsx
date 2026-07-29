import { useQuery } from "@tanstack/react-query";
import { Button, Card, Descriptions, Space, Typography } from "antd";
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
  displayDirection,
  displayLearningType,
  displayStatus,
} from "../../../shared/displayMappings";
import {
  formatBoolean,
  formatDateTime,
  formatPercent,
  formatValue,
} from "../../../shared/formatters";
import { reviewsApi } from "../api";
import type { ReviewDetail } from "../types";

export function ReviewDetailPage() {
  const { settlementId } = useParams();
  const detail = useQuery({
    queryKey: ["review-detail", settlementId],
    queryFn: () => reviewsApi.detail(settlementId!),
    enabled: Boolean(settlementId),
  });

  if (detail.isLoading) return <Typography.Text>正在加载...</Typography.Text>;
  if (detail.error) return <UserReadableError error={detail.error} />;
  if (!detail.data) return <EmptyBusinessState description="没有找到复盘记录" />;

  return (
    <section className="review-detail-page">
      <div className="page-heading">
        <div>
          <Typography.Title level={2}>复盘详情</Typography.Title>
          <Typography.Text type="secondary">
            {subject(detail.data)} 的预测、执行、结算和复盘结果。
          </Typography.Text>
        </div>
        <Link to="/reviews">
          <Button>返回复盘列表</Button>
        </Link>
      </div>
      <Space orientation="vertical" className="full-width" size="middle">
        <OriginalDecision detail={detail.data} />
        <OriginalTradePlan detail={detail.data} />
        <ExecutionSection detail={detail.data} />
        <SettlementSection detail={detail.data} />
        <ComparisonSection detail={detail.data} />
        <ReviewSection detail={detail.data} />
        <LearningSection detail={detail.data} />
      </Space>
    </section>
  );
}

function OriginalDecision({ detail }: { detail: ReviewDetail }) {
  const decision = detail.decision;
  return (
    <Card className="tool-card" title="原始研究结论">
      {!decision ? (
        <EmptyBusinessState description="没有原始决策记录" />
      ) : (
        <Descriptions bordered size="small" column={2}>
          <Descriptions.Item label="股票">{subject(detail)}</Descriptions.Item>
          <Descriptions.Item label="原始决策">
            {displayAction(decision.action)}
          </Descriptions.Item>
          <Descriptions.Item label="置信度">
            {formatPercent(decision.confidence)}
          </Descriptions.Item>
          <Descriptions.Item label="研究周期">{decision.horizon}</Descriptions.Item>
          <Descriptions.Item label="原始结论">
            <LongText text={decision.reasoning_summary} />
          </Descriptions.Item>
          <Descriptions.Item label="主要风险">
            {decision.risk_factors.join("、") || "-"}
          </Descriptions.Item>
        </Descriptions>
      )}
    </Card>
  );
}

function OriginalTradePlan({ detail }: { detail: ReviewDetail }) {
  const plan = detail.trade_plan;
  return (
    <Card className="tool-card" title="原始交易计划">
      {!plan ? (
        <EmptyBusinessState description="没有交易计划记录" />
      ) : (
        <Descriptions bordered size="small" column={2}>
          <Descriptions.Item label="方向">{displayDirection(plan.direction)}</Descriptions.Item>
          <Descriptions.Item label="入场条件">
            {plan.entry_conditions.join("、") || plan.planned_entry.join("、") || "-"}
          </Descriptions.Item>
          <Descriptions.Item label="建议仓位">
            {formatPercent(plan.planned_position)}
          </Descriptions.Item>
          <Descriptions.Item label="止损条件">{formatValue(plan.stop_loss)}</Descriptions.Item>
          <Descriptions.Item label="止盈条件">
            {plan.target?.join(" - ") ?? "-"}
          </Descriptions.Item>
          <Descriptions.Item label="退出条件">
            {plan.invalidation_conditions.join("、") || "-"}
          </Descriptions.Item>
        </Descriptions>
      )}
    </Card>
  );
}

function ExecutionSection({ detail }: { detail: ReviewDetail }) {
  const execution = detail.simulated_execution;
  return (
    <Card className="tool-card" title="模拟执行">
      {!execution ? (
        <EmptyBusinessState description="没有模拟执行记录" />
      ) : (
        <Descriptions bordered size="small" column={2}>
          <Descriptions.Item label="执行方向">
            {displayDirection(execution.direction)}
          </Descriptions.Item>
          <Descriptions.Item label="执行状态">
            <BusinessStatusTag value={execution.execution_status} />
          </Descriptions.Item>
          <Descriptions.Item label="入场价格">
            {formatValue(execution.executed_entry ?? execution.planned_entry)}
          </Descriptions.Item>
          <Descriptions.Item label="仓位">
            {formatValue(execution.position_size)}
          </Descriptions.Item>
          <Descriptions.Item label="执行时间">
            {formatDateTime(execution.execution_date)}
          </Descriptions.Item>
          <Descriptions.Item label="数据来源">
            {formatValue(execution.market_data_source)}
          </Descriptions.Item>
        </Descriptions>
      )}
    </Card>
  );
}

function SettlementSection({ detail }: { detail: ReviewDetail }) {
  const settlement = detail.settlement;
  return (
    <Card className="tool-card" title="结算结果">
      {!settlement ? (
        <EmptyBusinessState description="没有结算记录" />
      ) : (
        <Descriptions bordered size="small" column={2}>
          <Descriptions.Item label="入场价格">
            {formatValue(settlement.entry_price)}
          </Descriptions.Item>
          <Descriptions.Item label="退出价格">
            {formatValue(settlement.exit_price)}
          </Descriptions.Item>
          <Descriptions.Item label="实际收益率">
            {formatPercent(settlement.return_rate)}
          </Descriptions.Item>
          <Descriptions.Item label="收益金额">{formatValue(settlement.pnl)}</Descriptions.Item>
          <Descriptions.Item label="最大有利波动">
            {formatPercent(settlement.max_favorable_excursion)}
          </Descriptions.Item>
          <Descriptions.Item label="最大不利波动">
            {formatPercent(settlement.maximum_adverse_excursion)}
          </Descriptions.Item>
          <Descriptions.Item label="结算时间">
            {formatDateTime(settlement.settled_at)}
          </Descriptions.Item>
          <Descriptions.Item label="结算状态">
            <BusinessStatusTag value={settlement.status} />
          </Descriptions.Item>
        </Descriptions>
      )}
    </Card>
  );
}

function ComparisonSection({ detail }: { detail: ReviewDetail }) {
  const evaluation = detail.evaluation;
  return (
    <Card className="tool-card" title="预测与实际对比">
      {!evaluation ? (
        <EmptyBusinessState description="没有评价记录" />
      ) : (
        <Descriptions bordered size="small" column={2}>
          <Descriptions.Item label="方向评价">
            {displayStatus(evaluation.directional_result)}
          </Descriptions.Item>
          <Descriptions.Item label="收益评价">
            {displayStatus(evaluation.return_result)}
          </Descriptions.Item>
          <Descriptions.Item label="风控评价">
            {displayStatus(evaluation.risk_result)}
          </Descriptions.Item>
          <Descriptions.Item label="整体结果">
            {displayStatus(evaluation.final_result)}
          </Descriptions.Item>
          <Descriptions.Item label="评估理由">
            <LongText text={evaluation.explanation} />
          </Descriptions.Item>
        </Descriptions>
      )}
    </Card>
  );
}

function ReviewSection({ detail }: { detail: ReviewDetail }) {
  const review = detail.review;
  return (
    <Card className="tool-card" title="错误归因与改进建议">
      {!review ? (
        <EmptyBusinessState description="没有复盘记录" />
      ) : (
        <Descriptions bordered size="small" column={2}>
          <Descriptions.Item label="判断是否正确">
            {formatBoolean(review.direction_correct)}
          </Descriptions.Item>
          <Descriptions.Item label="风控是否突破">
            {formatBoolean(review.risk_limit_breached)}
          </Descriptions.Item>
          <Descriptions.Item label="做对了什么">
            {review.success_reasons.join("、") || "-"}
          </Descriptions.Item>
          <Descriptions.Item label="主要错误">
            {review.failure_reasons.join("、") || "-"}
          </Descriptions.Item>
          <Descriptions.Item label="错误归因">
            {review.cause_tags.join("、") || "-"}
          </Descriptions.Item>
          <Descriptions.Item label="改进建议">
            <LongText text={review.review_summary} />
          </Descriptions.Item>
        </Descriptions>
      )}
    </Card>
  );
}

function LearningSection({ detail }: { detail: ReviewDetail }) {
  return (
    <Card className="tool-card" title="对应学习建议">
      {!detail.learning_proposals.length ? (
        <EmptyBusinessState description="没有对应学习建议" />
      ) : (
        <Space orientation="vertical" className="full-width">
          {detail.learning_proposals.map((learning) => (
            <Descriptions key={learning.learning_id} bordered size="small" column={2}>
              <Descriptions.Item label="建议类型">
                {displayLearningType(learning.learning_type)}
              </Descriptions.Item>
              <Descriptions.Item label="审核状态">
                <BusinessStatusTag value={learning.approval_status} />
              </Descriptions.Item>
              <Descriptions.Item label="调整对象">{learning.target}</Descriptions.Item>
              <Descriptions.Item label="原因">
                <LongText text={learning.reason} />
              </Descriptions.Item>
              <Descriptions.Item label="详情">
                <Link to={`/learning/${encodeURIComponent(learning.learning_id)}`}>
                  查看学习建议
                </Link>
              </Descriptions.Item>
            </Descriptions>
          ))}
        </Space>
      )}
      <TechnicalDetails
        data={{
          settlement_id: detail.settlement?.outcome_id ?? null,
          research_run_id: detail.research_run?.run_id ?? null,
          decision_id: detail.decision?.decision_id ?? null,
        }}
      />
    </Card>
  );
}

function subject(detail: ReviewDetail) {
  return detail.settlement?.symbol ?? detail.decision?.symbol ?? detail.research_run?.symbol ?? "-";
}
