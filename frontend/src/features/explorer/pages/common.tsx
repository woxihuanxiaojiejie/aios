import { Alert, Card, Descriptions, Space, Typography } from "antd";
import { Link } from "react-router-dom";

import {
  EmptyState,
  StatusTag,
  formatDateTime,
  formatPercent,
} from "../../../shared/researchDisplay";
import type { ExplorerDetail } from "../types";

export function IdText({ value }: { value: string | null | undefined }) {
  if (!value) return <>-</>;
  return (
    <Typography.Text copyable={{ text: value }} ellipsis>
      {value}
    </Typography.Text>
  );
}

export function ChainSections({ detail }: { detail: ExplorerDetail }) {
  return (
    <Space orientation="vertical" className="full-width" size="middle">
      <Card className="tool-card" title="Research">
        {detail.research_run ? (
          <Descriptions bordered size="small" column={2}>
            <Descriptions.Item label="Research Run">
              <Link to={`/research/${encodeURIComponent(detail.research_run.run_id)}`}>
                {detail.research_run.run_id}
              </Link>
            </Descriptions.Item>
            <Descriptions.Item label="Symbol">
              {detail.research_run.symbol ?? "-"}
            </Descriptions.Item>
            <Descriptions.Item label="Market">
              {detail.research_session?.scope.market ?? "-"}
            </Descriptions.Item>
            <Descriptions.Item label="Status">
              <StatusTag value={detail.research_run.status} />
            </Descriptions.Item>
          </Descriptions>
        ) : (
          <EmptyState description="尚未关联 Research Run" />
        )}
      </Card>

      <Card className="tool-card" title="Decision">
        {detail.decision ? (
          <Descriptions bordered size="small" column={2}>
            <Descriptions.Item label="Decision ID">
              <IdText value={detail.decision.decision_id} />
            </Descriptions.Item>
            <Descriptions.Item label="Action">{detail.decision.action}</Descriptions.Item>
            <Descriptions.Item label="Confidence">
              {formatPercent(detail.decision.confidence)}
            </Descriptions.Item>
            <Descriptions.Item label="Reason">
              {detail.decision.reasoning_summary}
            </Descriptions.Item>
          </Descriptions>
        ) : (
          <EmptyState description="Decision 尚未生成" />
        )}
      </Card>

      <Card className="tool-card" title="Trade Plan">
        {detail.trade_plan ? (
          <Descriptions bordered size="small" column={2}>
            <Descriptions.Item label="Trade Plan ID">
              <IdText value={detail.trade_plan.trade_plan_id} />
            </Descriptions.Item>
            <Descriptions.Item label="Status">
              <StatusTag value={detail.trade_plan.status} />
            </Descriptions.Item>
            <Descriptions.Item label="Position">
              {formatPercent(detail.trade_plan.planned_position)}
            </Descriptions.Item>
            <Descriptions.Item label="Entry">
              {detail.trade_plan.planned_entry.join(", ") || "-"}
            </Descriptions.Item>
          </Descriptions>
        ) : (
          <EmptyState description="未生成 Trade Plan" />
        )}
      </Card>

      <DownstreamSections detail={detail} />
    </Space>
  );
}

export function DownstreamSections({ detail }: { detail: ExplorerDetail }) {
  return (
    <Space orientation="vertical" className="full-width" size="middle">
      <Card className="tool-card" title="Simulated Execution">
        {detail.simulated_execution ? (
          <Descriptions bordered size="small" column={2}>
            <Descriptions.Item label="Execution ID">
              <Link
                to={`/executions/${encodeURIComponent(detail.simulated_execution.execution_id)}`}
              >
                {detail.simulated_execution.execution_id}
              </Link>
            </Descriptions.Item>
            <Descriptions.Item label="Status">
              <StatusTag value={detail.simulated_execution.execution_status} />
            </Descriptions.Item>
            <Descriptions.Item label="Entry">
              {detail.simulated_execution.executed_entry ?? detail.simulated_execution.planned_entry}
            </Descriptions.Item>
            <Descriptions.Item label="Return">
              {detail.simulated_execution.realized_return ?? "-"}
            </Descriptions.Item>
          </Descriptions>
        ) : (
          <EmptyState description="尚未模拟执行" />
        )}
      </Card>

      <Card className="tool-card" title="Settlement">
        {detail.settlement ? (
          <Descriptions bordered size="small" column={2}>
            <Descriptions.Item label="Settlement ID">
              <Link to={`/settlements/${encodeURIComponent(detail.settlement.outcome_id)}`}>
                {detail.settlement.outcome_id}
              </Link>
            </Descriptions.Item>
            <Descriptions.Item label="Status">
              <StatusTag value={detail.settlement.status} />
            </Descriptions.Item>
            <Descriptions.Item label="PnL">{detail.settlement.pnl ?? "-"}</Descriptions.Item>
            <Descriptions.Item label="Settled">
              {formatDateTime(detail.settlement.settled_at)}
            </Descriptions.Item>
          </Descriptions>
        ) : (
          <Alert type="info" showIcon title="等待结算" />
        )}
      </Card>

      <Card className="tool-card" title="Evaluation">
        {detail.evaluation ? (
          <Descriptions bordered size="small" column={2}>
            <Descriptions.Item label="Evaluation ID">
              <IdText value={detail.evaluation.evaluation_id} />
            </Descriptions.Item>
            <Descriptions.Item label="Final Result">
              <StatusTag value={detail.evaluation.final_result} />
            </Descriptions.Item>
            <Descriptions.Item label="Rules">
              {detail.evaluation.evaluation_rules_version}
            </Descriptions.Item>
            <Descriptions.Item label="Explanation">
              {detail.evaluation.explanation}
            </Descriptions.Item>
          </Descriptions>
        ) : (
          <EmptyState description="尚未生成 Evaluation" />
        )}
      </Card>

      <Card className="tool-card" title="Review">
        {detail.review ? (
          <Descriptions bordered size="small" column={2}>
            <Descriptions.Item label="Review ID">
              <IdText value={detail.review.review_id} />
            </Descriptions.Item>
            <Descriptions.Item label="Outcome">
              <StatusTag value={detail.review.outcome} />
            </Descriptions.Item>
            <Descriptions.Item label="Actual Return">
              {detail.review.actual_return ?? "-"}
            </Descriptions.Item>
            <Descriptions.Item label="Summary">
              {detail.review.review_summary}
            </Descriptions.Item>
          </Descriptions>
        ) : (
          <EmptyState description="尚未生成 Review" />
        )}
      </Card>

      <Card className="tool-card" title="Learning Proposal">
        {detail.learning_proposals.length ? (
          <Space orientation="vertical" className="full-width">
            {detail.learning_proposals.map((learning) => (
              <Descriptions key={learning.learning_id} bordered size="small" column={2}>
                <Descriptions.Item label="Proposal ID">
                  <IdText value={learning.learning_id} />
                </Descriptions.Item>
                <Descriptions.Item label="Status">
                  <StatusTag value={learning.approval_status} />
                </Descriptions.Item>
                <Descriptions.Item label="Target">{learning.target}</Descriptions.Item>
                <Descriptions.Item label="Reason">{learning.reason}</Descriptions.Item>
              </Descriptions>
            ))}
          </Space>
        ) : (
          <EmptyState description="尚无 Learning Proposal" />
        )}
      </Card>
    </Space>
  );
}
