import { Alert, Button, Card, Descriptions, Space, Table, Typography } from "antd";
import type { ColumnsType } from "antd/es/table";
import { Link, useParams } from "react-router-dom";

import type {
  Decision,
  Evaluation,
  Evidence,
  Learning,
  Outcome,
  Review,
  SimulatedExecution,
  TradePlan,
} from "../../../infrastructure/api/research";
import {
  BusinessStatusTag,
  CopyableId,
  EmptyBusinessState,
  LongText,
  TechnicalDetails,
  UserReadableError,
} from "../../../shared/businessComponents";
import {
  displayAction,
  displayDirection,
  displayLearningType,
  displayResearchStage,
  displayStatus,
  displayTriggerMethod,
} from "../../../shared/displayMappings";
import {
  formatBoolean,
  formatDateTime,
  formatPercent,
  formatValue,
} from "../../../shared/formatters";
import { useResearchRunDetail } from "../hooks";
import type { ResearchRunDetail } from "../types";

const SKILL_ORDER = [
  { key: "technical_trend", name: "技术趋势分析" },
  { key: "sector_strength", name: "板块强度分析" },
  { key: "policy_impact", name: "政策影响分析" },
  { key: "announcement_risk", name: "公告风险分析" },
  { key: "market_sentiment", name: "市场情绪分析" },
] as const;

export function ResearchRunDetailPage() {
  const { runId } = useParams();
  const detail = useResearchRunDetail(runId);

  if (detail.isLoading) return <Typography.Text>正在加载...</Typography.Text>;
  if (detail.error) return <UserReadableError error={detail.error} />;
  if (!detail.data) return <EmptyBusinessState description="没有找到这次研究" />;

  return (
    <section className="research-detail-page">
      <div className="page-heading">
        <div>
          <Typography.Title level={2}>研究详情</Typography.Title>
          <Typography.Text type="secondary">
            {businessSubject(detail.data)} 的完整 AIOS 闭环记录
          </Typography.Text>
        </div>
        <Space>
          <Link to="/research">
            <Button>返回研究列表</Button>
          </Link>
          <Link to="/research/new">
            <Button type="primary">发起人工研究</Button>
          </Link>
        </Space>
      </div>

      <Space orientation="vertical" className="full-width" size="middle">
        <OverviewSection detail={detail.data} />
        <TriggerHypothesisSection detail={detail.data} />
        <EvidenceSection detail={detail.data} />
        <SkillAnalysisSection detail={detail.data} />
        <ConflictSection detail={detail.data} />
        <EvidenceReviewSection detail={detail.data} />
        <CounterReviewSection detail={detail.data} />
        <RevisionSection detail={detail.data} />
        <FinalDecisionSection decision={detail.data.decision} />
        <TradePlanSection tradePlan={detail.data.trade_plan} />
        <ExecutionSection execution={detail.data.simulated_execution} />
        <SettlementSection settlement={detail.data.settlement} />
        <EvaluationReviewSection
          evaluation={detail.data.evaluation}
          review={detail.data.review}
          settlement={detail.data.settlement}
        />
        <LearningSection learnings={detail.data.learning_proposals} />
      </Space>
    </section>
  );
}

function OverviewSection({ detail }: { detail: ResearchRunDetail }) {
  const run = detail.run;
  const session = detail.session;
  return (
    <Card className="tool-card" title="1. 研究概况">
      <Descriptions bordered column={{ xs: 1, sm: 2, lg: 3 }} size="small">
        <Descriptions.Item label="股票">{businessSubject(detail)}</Descriptions.Item>
        <Descriptions.Item label="市场">
          {detail.watchlist_item?.market ?? session?.scope.market ?? "-"}
        </Descriptions.Item>
        <Descriptions.Item label="当前状态">
          <BusinessStatusTag value={run.status} />
        </Descriptions.Item>
        <Descriptions.Item label="当前阶段">
          {displayResearchStage(run.current_stage)}
        </Descriptions.Item>
        <Descriptions.Item label="研究时间">
          {formatDateTime(run.created_at)} 至 {formatDateTime(run.finished_at)}
        </Descriptions.Item>
        <Descriptions.Item label="研究周期">{researchHorizon(detail)}</Descriptions.Item>
        <Descriptions.Item label="触发方式">
          {displayTriggerMethod(triggerMethod(detail))}
        </Descriptions.Item>
        <Descriptions.Item label="失败原因">
          {run.error_type || run.error ? displayStatus(run.error_type) : "-"}
        </Descriptions.Item>
      </Descriptions>
      <TechnicalDetails
        data={{
          run_id: run.run_id,
          research_session_id: session?.research_session_id ?? null,
          watchlist_item_id: run.watchlist_item_id,
          workflow: run.workflow,
          raw_status: run.status,
          input_params: run.input_params,
          error: run.error,
        }}
      />
    </Card>
  );
}

function TriggerHypothesisSection({ detail }: { detail: ResearchRunDetail }) {
  const hypothesis = detail.hypotheses[0] ?? null;
  return (
    <Card className="tool-card" title="2. 触发原因与初始假设">
      <Descriptions bordered size="small" column={2}>
        <Descriptions.Item label="触发来源">
          {triggerReason(detail) ?? "该次研究未记录触发原因。"}
        </Descriptions.Item>
        <Descriptions.Item label="假设来源">
          {hypothesis?.supporting_report_ids.join("、") ||
            detail.analysis_task?.task_id ||
            "未记录"}
        </Descriptions.Item>
        <Descriptions.Item label="初始假设正文">
          <LongText text={hypothesis?.statement ?? initialHypothesis(detail)} />
        </Descriptions.Item>
        <Descriptions.Item label="假设待验证条件">
          <LongText text={hypothesis?.rationale ?? "该次研究未记录待验证条件。"} />
        </Descriptions.Item>
        <Descriptions.Item label="方向">
          {displayDirection(hypothesis?.direction)}
        </Descriptions.Item>
        <Descriptions.Item label="置信度">
          {formatPercent(hypothesis?.confidence)}
        </Descriptions.Item>
      </Descriptions>
      {!hypothesis ? <MissingStage name="初始假设" /> : null}
    </Card>
  );
}

function EvidenceSection({ detail }: { detail: ResearchRunDetail }) {
  const columns: ColumnsType<Evidence> = [
    { title: "证据类型", dataIndex: "evidence_type", width: 120 },
    {
      title: "标题",
      dataIndex: "title",
      width: 180,
      render: (value: string | null) => value || "-",
    },
    {
      title: "摘要",
      dataIndex: "summary",
      width: 260,
      render: (value: string) => <LongText text={value} maxLength={80} />,
    },
    { title: "来源", dataIndex: "source", width: 140 },
    { title: "时间", dataIndex: "published_at", width: 170, render: formatDateTime },
    { title: "可靠性", dataIndex: "reliability", width: 100, render: formatPercent },
    {
      title: "与假设关系",
      width: 120,
      render: (_value, record) => evidenceRelation(detail, record.evidence_id),
    },
    {
      title: "原始引用",
      width: 120,
      render: (_value, record) =>
        record.source_url ? (
          <a href={record.source_url} target="_blank" rel="noreferrer noopener">
            打开引用
          </a>
        ) : (
          formatValue(record.source_identifier)
        ),
    },
  ];
  return (
    <Card className="tool-card" title="3. 证据材料">
      <Table
        rowKey="evidence_id"
        columns={columns}
        dataSource={detail.evidence}
        pagination={false}
        expandable={{
          expandedRowRender: (record) => (
            <Space orientation="vertical" className="full-width">
              <LongText text={record.raw_content ?? undefined} maxLength={240} />
              <CopyableId value={record.evidence_id} label="证据编号" />
              <TechnicalDetails
                data={{
                  evidence_id: record.evidence_id,
                  content_hash: record.content_hash,
                  metadata: record.metadata,
                  raw_response: record.raw_response,
                }}
              />
            </Space>
          ),
        }}
        locale={{ emptyText: <EmptyBusinessState description="该次研究没有证据材料" /> }}
        scroll={{ x: 1100 }}
      />
    </Card>
  );
}

function SkillAnalysisSection({ detail }: { detail: ResearchRunDetail }) {
  const rows = SKILL_ORDER.map((skill) => skillRow(detail, skill.key, skill.name));
  const columns: ColumnsType<SkillDisplayRow> = [
    { title: "分析能力", dataIndex: "name", width: 140 },
    {
      title: "分析状态",
      dataIndex: "status",
      width: 120,
      render: (value: string | null) => <BusinessStatusTag value={value} />,
    },
    {
      title: "方向",
      dataIndex: "direction",
      width: 100,
      render: displayDirection,
    },
    {
      title: "置信度",
      dataIndex: "confidence",
      width: 100,
      render: formatPercent,
    },
    {
      title: "核心结论",
      dataIndex: "conclusion",
      width: 220,
      render: (value: string | null) => <LongText text={value} maxLength={80} />,
    },
    {
      title: "主要理由",
      dataIndex: "reason",
      width: 220,
      render: (value: string | null) => <LongText text={value} maxLength={80} />,
    },
    { title: "引用证据", dataIndex: "evidence", width: 160, render: formatValue },
    { title: "风险", dataIndex: "risk", width: 180, render: formatValue },
    { title: "不确定项", dataIndex: "uncertainty", width: 180, render: formatValue },
    {
      title: "失败原因",
      dataIndex: "error",
      width: 180,
      render: (value: string | null) => value || "-",
    },
  ];
  return (
    <Card className="tool-card" title="4. 五项独立分析">
      <Table
        rowKey="key"
        columns={columns}
        dataSource={rows}
        pagination={false}
        expandable={{
          expandedRowRender: (record) =>
            record.technical ? <TechnicalDetails data={record.technical} /> : null,
        }}
        scroll={{ x: 1400 }}
      />
    </Card>
  );
}

function ConflictSection({ detail }: { detail: ResearchRunDetail }) {
  const conflicts = detail.discussion_result?.conflicts ?? [];
  return (
    <Card className="tool-card" title="5. 冲突识别">
      {conflicts.length ? (
        <DescriptionList rows={conflicts.map(summarizeObject)} />
      ) : (
        <MissingStage name="冲突识别" />
      )}
    </Card>
  );
}

function EvidenceReviewSection({ detail }: { detail: ResearchRunDetail }) {
  const reviews = detail.discussion_result?.evidence_reviews ?? [];
  return (
    <Card className="tool-card" title="6. 证据复核">
      {reviews.length ? (
        <DescriptionList rows={reviews.map(summarizeObject)} />
      ) : (
        <MissingStage name="证据复核" />
      )}
    </Card>
  );
}

function CounterReviewSection({ detail }: { detail: ResearchRunDetail }) {
  const counters = detail.discussion_result?.counter_arguments ?? [];
  return (
    <Card className="tool-card" title="7. 反方审查">
      {counters.length ? (
        <DescriptionList rows={counters.map(summarizeObject)} />
      ) : detail.discussion.risk_review ? (
        <Descriptions bordered size="small" column={2}>
          <Descriptions.Item label="最强反对理由">
            {detail.discussion.risk_review.opposing_arguments.join("、") || "-"}
          </Descriptions.Item>
          <Descriptions.Item label="被忽略风险">
            {detail.discussion.risk_review.reasons.join("、") || "-"}
          </Descriptions.Item>
          <Descriptions.Item label="可能失败的条件">
            {detail.discussion.risk_review.condition_changes.join("、") || "-"}
          </Descriptions.Item>
          <Descriptions.Item label="反方置信度">
            {formatPercent(detail.discussion.risk_review.final_confidence)}
          </Descriptions.Item>
        </Descriptions>
      ) : (
        <MissingStage name="反方审查" />
      )}
    </Card>
  );
}

function RevisionSection({ detail }: { detail: ResearchRunDetail }) {
  const revisions = detail.discussion_result?.revision_suggestions ?? [];
  return (
    <Card className="tool-card" title="8. 讨论修订">
      <Descriptions bordered size="small" column={2}>
        <Descriptions.Item label="初始分析结论">
          {detail.skill_results.map((item) => item.conclusion).join("；") || "-"}
        </Descriptions.Item>
        <Descriptions.Item label="修订后的结论">
          {detail.discussion_result?.discussion_summary ??
            detail.discussion.proposal?.thesis ??
            "-"}
        </Descriptions.Item>
        <Descriptions.Item label="修改原因">
          {revisions.map(summarizeObject).join("；") || "未记录"}
        </Descriptions.Item>
        <Descriptions.Item label="哪些证据导致修改">
          {detail.discussion.proposal?.evidence_ids.join("、") ||
            detail.decision_result?.supporting_reasons.map(summarizeObject).join("；") ||
            "-"}
        </Descriptions.Item>
        <Descriptions.Item label="置信度变化">
          {confidenceChange(detail)}
        </Descriptions.Item>
      </Descriptions>
      {!detail.discussion_result && !detail.discussion.proposal ? (
        <MissingStage name="讨论修订" />
      ) : null}
    </Card>
  );
}

function FinalDecisionSection({ decision }: { decision: Decision | null }) {
  return (
    <Card className="tool-card" title="9. 最终决策">
      {!decision ? (
        <MissingStage name="最终决策" />
      ) : (
        <Descriptions bordered size="small" column={2}>
          <Descriptions.Item label="决策">
            {displayAction(decision.action)}
          </Descriptions.Item>
          <Descriptions.Item label="置信度">
            {formatPercent(decision.confidence)}
          </Descriptions.Item>
          <Descriptions.Item label="决策摘要">
            <LongText text={decision.reasoning_summary} />
          </Descriptions.Item>
          <Descriptions.Item label="核心支持理由">
            {decision.entry_conditions.join("、") || "-"}
          </Descriptions.Item>
          <Descriptions.Item label="主要反对理由">
            {decision.dissenting_opinions.join("、") || "-"}
          </Descriptions.Item>
          <Descriptions.Item label="风险因素">
            {decision.risk_factors.join("、") || "-"}
          </Descriptions.Item>
          <Descriptions.Item label="决策失效条件">
            {decision.invalidation_conditions.join("、") || "-"}
          </Descriptions.Item>
          <Descriptions.Item label="不交易原因">
            {[...decision.unavailable_fields, ...decision.downgrade_reasons].join("、") ||
              "-"}
          </Descriptions.Item>
          <Descriptions.Item label="状态">
            <BusinessStatusTag value={decision.status} />
          </Descriptions.Item>
          <Descriptions.Item label="决策时间">
            {formatDateTime(decision.created_at)}
          </Descriptions.Item>
        </Descriptions>
      )}
    </Card>
  );
}

function TradePlanSection({ tradePlan }: { tradePlan: TradePlan | null }) {
  return (
    <Card className="tool-card" title="10. 交易计划">
      {!tradePlan ? (
        <MissingStage name="交易计划" />
      ) : (
        <Descriptions bordered size="small" column={2}>
          <Descriptions.Item label="是否生成交易计划">是</Descriptions.Item>
          <Descriptions.Item label="状态">
            <BusinessStatusTag value={tradePlan.status} />
          </Descriptions.Item>
          <Descriptions.Item label="入场条件">
            {tradePlan.entry_conditions.join("、") ||
              tradePlan.planned_entry.join("、") ||
              "-"}
          </Descriptions.Item>
          <Descriptions.Item label="建议仓位">
            {formatPercent(tradePlan.planned_position)}
          </Descriptions.Item>
          <Descriptions.Item label="止损条件">
            {formatValue(tradePlan.stop_loss)}
          </Descriptions.Item>
          <Descriptions.Item label="止盈条件">
            {tradePlan.target?.join(" - ") ?? "-"}
          </Descriptions.Item>
          <Descriptions.Item label="持有周期">{tradePlan.horizon}</Descriptions.Item>
          <Descriptions.Item label="退出条件">
            {tradePlan.invalidation_conditions.join("、") || "-"}
          </Descriptions.Item>
          <Descriptions.Item label="不执行原因">
            {tradePlan.no_trade_reasons.join("、") || "-"}
          </Descriptions.Item>
        </Descriptions>
      )}
    </Card>
  );
}

function ExecutionSection({ execution }: { execution: SimulatedExecution | null }) {
  return (
    <Card className="tool-card" title="11. 模拟执行">
      {!execution ? (
        <MissingStage name="模拟执行" />
      ) : (
        <Descriptions bordered size="small" column={2}>
          <Descriptions.Item label="是否执行">是</Descriptions.Item>
          <Descriptions.Item label="当前状态">
            <BusinessStatusTag value={execution.execution_status} />
          </Descriptions.Item>
          <Descriptions.Item label="执行方向">
            {displayDirection(execution.direction)}
          </Descriptions.Item>
          <Descriptions.Item label="模拟价格">
            {formatValue(execution.executed_entry ?? execution.planned_entry)}
          </Descriptions.Item>
          <Descriptions.Item label="模拟数量或仓位">
            {formatValue(execution.position_size)}
          </Descriptions.Item>
          <Descriptions.Item label="执行时间">
            {formatDateTime(execution.execution_date)}
          </Descriptions.Item>
        </Descriptions>
      )}
    </Card>
  );
}

function SettlementSection({ settlement }: { settlement: Outcome | null }) {
  return (
    <Card className="tool-card" title="12. 结果结算">
      {!settlement ? (
        <MissingStage name="结果结算" />
      ) : (
        <Descriptions bordered size="small" column={2}>
          <Descriptions.Item label="入场价格">
            {formatValue(settlement.entry_price)}
          </Descriptions.Item>
          <Descriptions.Item label="退出价格">
            {formatValue(settlement.exit_price)}
          </Descriptions.Item>
          <Descriptions.Item label="收益率">
            {formatPercent(settlement.return_rate)}
          </Descriptions.Item>
          <Descriptions.Item label="收益金额">{formatValue(settlement.pnl)}</Descriptions.Item>
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

function EvaluationReviewSection({
  evaluation,
  review,
  settlement,
}: {
  evaluation: Evaluation | null;
  review: Review | null;
  settlement: Outcome | null;
}) {
  return (
    <Card className="tool-card" title="13. 评价与复盘">
      {!evaluation && !review ? <MissingStage name="评价与复盘" /> : null}
      <Descriptions bordered size="small" column={2}>
        <Descriptions.Item label="方向是否正确">
          {evaluation ? displayStatus(evaluation.directional_result) : "-"}
        </Descriptions.Item>
        <Descriptions.Item label="预期收益是否达到">
          {evaluation ? displayStatus(evaluation.return_result) : "-"}
        </Descriptions.Item>
        <Descriptions.Item label="最大有利波动">
          {formatPercent(settlement?.max_favorable_excursion)}
        </Descriptions.Item>
        <Descriptions.Item label="最大不利波动">
          {formatPercent(settlement?.maximum_adverse_excursion)}
        </Descriptions.Item>
        <Descriptions.Item label="风控是否有效">
          {evaluation ? displayStatus(evaluation.risk_result) : "-"}
        </Descriptions.Item>
        <Descriptions.Item label="主要错误归因">
          {review?.failure_reasons.join("、") || "-"}
        </Descriptions.Item>
        <Descriptions.Item label="哪个分析环节出现问题">
          {review?.mistaken_judgement_ids.join("、") || "-"}
        </Descriptions.Item>
        <Descriptions.Item label="哪项证据失效">
          {review?.effective_evidence_ids.join("、") || "-"}
        </Descriptions.Item>
        <Descriptions.Item label="是否忽略反方意见">
          {formatBoolean(review?.risk_limit_breached)}
        </Descriptions.Item>
        <Descriptions.Item label="复盘摘要">
          <LongText text={review?.review_summary ?? evaluation?.explanation ?? null} />
        </Descriptions.Item>
      </Descriptions>
    </Card>
  );
}

function LearningSection({ learnings }: { learnings: Learning[] }) {
  return (
    <Card className="tool-card" title="14. 学习建议">
      {!learnings.length ? (
        <MissingStage name="学习建议" />
      ) : (
        <Space orientation="vertical" className="full-width">
          {learnings.map((learning) => (
            <Descriptions
              key={learning.learning_id}
              bordered
              size="small"
              column={2}
            >
              <Descriptions.Item label="是否生成学习建议">是</Descriptions.Item>
              <Descriptions.Item label="建议类型">
                {displayLearningType(learning.learning_type)}
              </Descriptions.Item>
              <Descriptions.Item label="调整对象">{learning.target}</Descriptions.Item>
              <Descriptions.Item label="当前值">
                {summarizeValue(learning.before)}
              </Descriptions.Item>
              <Descriptions.Item label="建议值">
                {summarizeValue(learning.after)}
              </Descriptions.Item>
              <Descriptions.Item label="原因">
                <LongText text={learning.reason} />
              </Descriptions.Item>
              <Descriptions.Item label="审核状态">
                <BusinessStatusTag value={learning.approval_status} />
              </Descriptions.Item>
              <Descriptions.Item label="创建时间">
                {formatDateTime(learning.created_at)}
              </Descriptions.Item>
            </Descriptions>
          ))}
        </Space>
      )}
    </Card>
  );
}

function MissingStage({ name }: { name: string }) {
  return (
    <Alert
      type="info"
      showIcon
      title={`该次研究未产生${name}的结构化记录。`}
    />
  );
}

function DescriptionList({ rows }: { rows: string[] }) {
  return (
    <Space orientation="vertical" className="full-width">
      {rows.map((row, index) => (
        <Alert key={`${index}:${row}`} type="info" showIcon title={row} />
      ))}
    </Space>
  );
}

type SkillDisplayRow = {
  key: string;
  name: string;
  status: string | null;
  direction: string | null;
  confidence: number | null;
  conclusion: string | null;
  reason: string | null;
  evidence: string;
  risk: string;
  uncertainty: string;
  error: string | null;
  technical: unknown;
};

function skillRow(
  detail: ResearchRunDetail,
  key: string,
  name: string,
): SkillDisplayRow {
  const result = detail.skill_results.find((item) => normalizedSkill(item.skill_id) === key);
  const execution = detail.skill_executions.find(
    (item) => normalizedSkill(item.skill_id) === key,
  );
  const report = detail.skill_reports.find((item) => normalizedSkill(item.role) === key);
  return {
    key,
    name,
    status: execution?.status ?? report?.status ?? null,
    direction: result?.direction ?? report?.stance ?? null,
    confidence: result?.confidence ?? report?.confidence ?? null,
    conclusion: result?.conclusion ?? report?.summary ?? null,
    reason: result?.reasoning_summary ?? report?.summary ?? null,
    evidence:
      result?.supporting_evidence_ids.join("、") ??
      report?.evidence_ids.join("、") ??
      "-",
    risk: result?.risk_factors.join("、") || "-",
    uncertainty: result?.missing_information.join("、") || "-",
    error: execution?.error ?? report?.raw_reference ?? null,
    technical: { result, execution, report },
  };
}

function normalizedSkill(value: string) {
  const mapping: Record<string, string> = {
    technical: "technical_trend",
    technical_trend: "technical_trend",
    sector: "sector_strength",
    sector_strength: "sector_strength",
    fundamental: "sector_strength",
    policy: "policy_impact",
    policy_impact: "policy_impact",
    capital_flow: "policy_impact",
    announcement: "announcement_risk",
    announcement_risk: "announcement_risk",
    news: "announcement_risk",
    sentiment: "market_sentiment",
    market_sentiment: "market_sentiment",
  };
  return mapping[value] ?? value;
}

function businessSubject(detail: ResearchRunDetail) {
  return detail.watchlist_item?.symbol ?? detail.session?.scope.symbol ?? detail.run.symbol ?? "-";
}

function researchHorizon(detail: ResearchRunDetail) {
  const days = detail.session?.scope.horizon_days ?? detail.run.input_params.horizon_days;
  if (typeof days === "number" || typeof days === "string") return `${days} 天`;
  return detail.decision?.horizon ?? detail.analysis_task?.horizon ?? "-";
}

function triggerMethod(detail: ResearchRunDetail) {
  return stringInput(detail, "trigger_method") ?? detail.run.workflow;
}

function triggerReason(detail: ResearchRunDetail) {
  return (
    stringInput(detail, "trigger_reason") ??
    stringInput(detail, "source") ??
    detail.watchlist_item?.note ??
    null
  );
}

function initialHypothesis(detail: ResearchRunDetail) {
  return (
    stringInput(detail, "initial_hypothesis") ??
    stringInput(detail, "hypothesis") ??
    null
  );
}

function stringInput(detail: ResearchRunDetail, key: string) {
  const value = detail.run.input_params[key];
  return typeof value === "string" && value ? value : null;
}

function evidenceRelation(detail: ResearchRunDetail, evidenceId: string) {
  if (
    detail.skill_results.some((item) =>
      item.supporting_evidence_ids.includes(evidenceId),
    ) ||
    detail.hypotheses.some((item) => item.supporting_evidence_ids.includes(evidenceId))
  ) {
    return "支持";
  }
  if (
    detail.skill_results.some((item) =>
      item.contradicting_evidence_ids.includes(evidenceId),
    )
  ) {
    return "反对";
  }
  return "中性";
}

function confidenceChange(detail: ResearchRunDetail) {
  const before = detail.skill_results[0]?.confidence ?? detail.hypotheses[0]?.confidence;
  const after =
    detail.discussion_result?.discussion_confidence ??
    detail.discussion.risk_review?.final_confidence ??
    detail.decision?.confidence;
  if (before === undefined && after === undefined) return "-";
  return `${formatPercent(before)} → ${formatPercent(after)}`;
}

function summarizeObject(value: Record<string, unknown>) {
  const preferred = [
    "summary",
    "reason",
    "rationale",
    "description",
    "conclusion",
    "issue",
    "recommendation",
  ];
  for (const key of preferred) {
    const current = value[key];
    if (typeof current === "string" && current) return current;
  }
  return Object.entries(value)
    .slice(0, 4)
    .map(([key, current]) => `${key}：${formatValue(current)}`)
    .join("；");
}

function summarizeValue(value: unknown) {
  if (value && typeof value === "object" && !Array.isArray(value)) {
    return Object.entries(value)
      .slice(0, 4)
      .map(([key, current]) => `${key}：${formatValue(current)}`)
      .join("；");
  }
  return formatValue(value);
}
