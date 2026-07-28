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
            <Descriptions.Item label="Horizon">{detail.decision.horizon}</Descriptions.Item>
            <Descriptions.Item label="Status">
              <StatusTag value={detail.decision.status} />
            </Descriptions.Item>
            <Descriptions.Item label="Created">
              {formatDateTime(detail.decision.created_at)}
            </Descriptions.Item>
            <Descriptions.Item label="Valid Until">
              {formatDateTime(detail.decision.valid_until)}
            </Descriptions.Item>
            <Descriptions.Item label="Supporting Evidence">
              {listText(detail.decision.evidence_ids)}
            </Descriptions.Item>
            <Descriptions.Item label="Reason">
              {detail.decision.reasoning_summary}
            </Descriptions.Item>
            <Descriptions.Item label="Risks">
              {listText(detail.decision.risk_factors)}
            </Descriptions.Item>
            <Descriptions.Item label="Invalidating Conditions">
              {listText(detail.decision.invalidation_conditions)}
            </Descriptions.Item>
            <Descriptions.Item label="No Trade / Downgrade Reasons">
              {listText([...detail.decision.unavailable_fields, ...detail.decision.downgrade_reasons])}
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
            <Descriptions.Item label="Entry Conditions">
              {listText(detail.trade_plan.entry_conditions)}
            </Descriptions.Item>
            <Descriptions.Item label="Target">
              {detail.trade_plan.target?.join(" - ") ?? "-"}
            </Descriptions.Item>
            <Descriptions.Item label="Stop Loss">
              {detail.trade_plan.stop_loss ?? "-"}
            </Descriptions.Item>
            <Descriptions.Item label="Holding Period">
              {detail.trade_plan.horizon}
            </Descriptions.Item>
            <Descriptions.Item label="Invalidation">
              {listText(detail.trade_plan.invalidation_conditions)}
            </Descriptions.Item>
            <Descriptions.Item label="Risk Budget">
              {detail.trade_plan.planned_position === null
                ? "-"
                : formatPercent(detail.trade_plan.planned_position)}
            </Descriptions.Item>
            <Descriptions.Item label="No Trade Reasons">
              {listText(detail.trade_plan.no_trade_reasons)}
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
            <Descriptions.Item label="Action">
              {detail.simulated_execution.direction}
            </Descriptions.Item>
            <Descriptions.Item label="Quantity">
              {detail.simulated_execution.position_size}
            </Descriptions.Item>
            <Descriptions.Item label="Simulated Price">
              {detail.simulated_execution.executed_entry ?? "-"}
            </Descriptions.Item>
            <Descriptions.Item label="Execution Time">
              {formatDateTime(detail.simulated_execution.execution_date)}
            </Descriptions.Item>
            <Descriptions.Item label="Trade Plan ID">
              <IdText value={detail.simulated_execution.trade_plan_id} />
            </Descriptions.Item>
            <Descriptions.Item label="Decision ID">
              <IdText value={detail.simulated_execution.decision_id} />
            </Descriptions.Item>
            <Descriptions.Item label="Research Session ID">
              <IdText value={detail.simulated_execution.research_session_id} />
            </Descriptions.Item>
            <Descriptions.Item label="Market Data Source">
              {detail.simulated_execution.market_data_source ?? "-"}
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
            <Descriptions.Item label="Entry Price">
              {detail.settlement.entry_price ?? "-"}
            </Descriptions.Item>
            <Descriptions.Item label="Exit Price">
              {detail.settlement.exit_price ?? "-"}
            </Descriptions.Item>
            <Descriptions.Item label="Entry Time">
              {formatDateTime(detail.settlement.observation_started_at)}
            </Descriptions.Item>
            <Descriptions.Item label="Exit Time">
              {formatDateTime(detail.settlement.observation_ended_at)}
            </Descriptions.Item>
            <Descriptions.Item label="Return">
              {detail.settlement.return_rate ?? detail.settlement.realized_return ?? "-"}
            </Descriptions.Item>
            <Descriptions.Item label="PnL">{detail.settlement.pnl ?? "-"}</Descriptions.Item>
            <Descriptions.Item label="Outcome">{detail.settlement.horizon_semantics}</Descriptions.Item>
            <Descriptions.Item label="Basis">
              {detail.settlement.exit_reason ?? detail.settlement.market_data_source}
            </Descriptions.Item>
            <Descriptions.Item label="Market Data Reference">
              {detail.settlement.market_data_source}
            </Descriptions.Item>
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
            <Descriptions.Item label="Direction Accuracy">
              <StatusTag value={detail.evaluation.directional_result} />
            </Descriptions.Item>
            <Descriptions.Item label="Return Evaluation">
              <StatusTag value={detail.evaluation.return_result} />
            </Descriptions.Item>
            <Descriptions.Item label="Risk Evaluation">
              <StatusTag value={detail.evaluation.risk_result} />
            </Descriptions.Item>
            <Descriptions.Item label="Rules">
              {detail.evaluation.evaluation_rules_version}
            </Descriptions.Item>
            <Descriptions.Item label="Scores">
              {[
                detail.evaluation.prediction_accuracy,
                detail.evaluation.timing_accuracy,
                detail.evaluation.risk_control,
                detail.evaluation.execution_quality,
              ].filter(Boolean).join(", ") || "-"}
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
            <Descriptions.Item label="Success Reasons">
              {listText(detail.review.success_reasons)}
            </Descriptions.Item>
            <Descriptions.Item label="Failure Reasons">
              {listText(detail.review.failure_reasons)}
            </Descriptions.Item>
            <Descriptions.Item label="Cause Tags">
              {listText(detail.review.cause_tags)}
            </Descriptions.Item>
            <Descriptions.Item label="Evidence Issues">
              {listText(detail.review.effective_evidence_ids)}
            </Descriptions.Item>
            <Descriptions.Item label="Decision Issues">
              {listText(detail.review.mistaken_judgement_ids)}
            </Descriptions.Item>
            <Descriptions.Item label="Risk Issues">
              {detail.review.risk_limit_breached === null
                ? "-"
                : String(detail.review.risk_limit_breached)}
            </Descriptions.Item>
            <Descriptions.Item label="Reference IDs">
              <pre className="json-block">{JSON.stringify(detail.review.reference_ids, null, 2)}</pre>
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
                <Descriptions.Item label="Proposal Type">
                  {learning.learning_type}
                </Descriptions.Item>
                <Descriptions.Item label="Current Value">
                  <pre className="json-block">{JSON.stringify(learning.before, null, 2)}</pre>
                </Descriptions.Item>
                <Descriptions.Item label="Proposed Value">
                  <pre className="json-block">{JSON.stringify(learning.after, null, 2)}</pre>
                </Descriptions.Item>
                <Descriptions.Item label="Reason">{learning.reason}</Descriptions.Item>
                <Descriptions.Item label="Supporting Review">
                  <IdText value={learning.review_id} />
                </Descriptions.Item>
                <Descriptions.Item label="Supporting Evidence">-</Descriptions.Item>
                <Descriptions.Item label="Expected Effect">-</Descriptions.Item>
                <Descriptions.Item label="Risks">-</Descriptions.Item>
                <Descriptions.Item label="Created Time">
                  {formatDateTime(learning.created_at)}
                </Descriptions.Item>
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

function listText(values: readonly string[]) {
  return values.length ? values.join(", ") : "-";
}
