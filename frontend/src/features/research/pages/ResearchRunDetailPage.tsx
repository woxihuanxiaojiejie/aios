import {
  Alert,
  Button,
  Card,
  Collapse,
  Descriptions,
  Space,
  Table,
  Tabs,
  Timeline,
  Typography,
} from "antd";
import type { ColumnsType } from "antd/es/table";
import { Link, useParams } from "react-router-dom";

import {
  EmptyState,
  ErrorState,
  LoadingState,
  StatusTag,
  formatDateTime,
  formatPercent,
} from "../../../shared/researchDisplay";
import { ApiError } from "../../../infrastructure/api/client";
import { DownstreamSections } from "../../explorer/pages/common";
import { useResearchRunDetail } from "../hooks";
import type { ResearchRunDetail } from "../types";
import type {
  AgentReport,
  Decision,
  Evidence,
  Hypothesis,
  TradePlan,
} from "../../../infrastructure/api/research";

export function ResearchRunDetailPage() {
  const { runId } = useParams();
  const detail = useResearchRunDetail(runId);

  if (detail.isLoading) return <LoadingState />;
  if (detail.error) return <ErrorState message={errorMessage(detail.error)} />;
  if (!detail.data) return <EmptyState description="Research Run 不存在" />;

  return (
    <section className="research-detail-page">
      <div className="page-heading">
        <div>
          <Typography.Title level={2}>Research Run 详情</Typography.Title>
          <Typography.Text copyable={{ text: detail.data.run.run_id }} type="secondary">
            {detail.data.run.run_id}
          </Typography.Text>
        </div>
        <Space>
          <Link to="/research">
            <Button>返回列表</Button>
          </Link>
          <Link to="/research/new">
            <Button type="primary">发起研究</Button>
          </Link>
        </Space>
      </div>
      <ResearchRunOverview detail={detail.data} />
      <EvidenceSection detail={detail.data} />
      <SkillReportsSection reports={detail.data.skill_reports} />
      <HypothesisSection hypotheses={detail.data.hypotheses} />
      <DiscussionSection detail={detail.data} />
      <DecisionSection decision={detail.data.decision} runStatus={detail.data.run.status} />
      <TradePlanSection tradePlan={detail.data.trade_plan} />
      <DownstreamSections
        detail={{
          research_run: detail.data.run,
          research_session: detail.data.session,
          decision: detail.data.decision,
          trade_plan: detail.data.trade_plan,
          simulated_execution: detail.data.simulated_execution,
          settlement: detail.data.settlement,
          evaluation: detail.data.evaluation,
          review: detail.data.review,
          learning_proposals: detail.data.learning_proposals,
        }}
      />
    </section>
  );
}

function ResearchRunOverview({ detail }: { detail: ResearchRunDetail }) {
  const run = detail.run;
  const market = detail.watchlist_item?.market ?? detail.session?.scope.market ?? "-";
  return (
    <Card className="tool-card" title="Research Run 概览">
      <Descriptions bordered column={{ xs: 1, sm: 2, lg: 3 }} size="small">
        <Descriptions.Item label="Run ID">{run.run_id}</Descriptions.Item>
        <Descriptions.Item label="股票代码">{run.symbol ?? "-"}</Descriptions.Item>
        <Descriptions.Item label="市场">{market}</Descriptions.Item>
        <Descriptions.Item label="状态"><StatusTag value={run.status} /></Descriptions.Item>
        <Descriptions.Item label="触发方式">
          {String(run.input_params.trigger_method ?? run.workflow)}
        </Descriptions.Item>
        <Descriptions.Item label="Workflow">{run.workflow}</Descriptions.Item>
        <Descriptions.Item label="创建时间">{formatDateTime(run.created_at)}</Descriptions.Item>
        <Descriptions.Item label="开始时间">{formatDateTime(run.created_at)}</Descriptions.Item>
        <Descriptions.Item label="完成时间">{formatDateTime(run.finished_at)}</Descriptions.Item>
        <Descriptions.Item label="当前阶段">{run.current_stage}</Descriptions.Item>
        <Descriptions.Item label="失败阶段">{run.failed_stage ?? "-"}</Descriptions.Item>
        <Descriptions.Item label="错误信息">{run.error ?? "-"}</Descriptions.Item>
        <Descriptions.Item label="Provider / Model">
          {[run.input_params.provider, run.input_params.model].filter(Boolean).join(" / ") || "-"}
        </Descriptions.Item>
      </Descriptions>
    </Card>
  );
}

function EvidenceSection({ detail }: { detail: ResearchRunDetail }) {
  const referencedBy = evidenceReferences(detail.skill_reports);
  const columns: ColumnsType<Evidence> = [
    { title: "Evidence ID", dataIndex: "evidence_id", width: 190 },
    { title: "类型", dataIndex: "evidence_type", width: 120 },
    { title: "来源", dataIndex: "source", width: 150 },
    { title: "质量", dataIndex: "reliability", width: 100 },
    { title: "可信度", dataIndex: "credibility", width: 100, render: nullable },
    {
      title: "标题",
      dataIndex: "title",
      width: 180,
      render: (value: string | null) => value || "-",
    },
    {
      title: "摘要",
      dataIndex: "summary",
      render: (value: string) => value || <EmptyState description="摘要为空" />,
    },
    {
      title: "发布时间",
      dataIndex: "published_at",
      width: 180,
      render: formatDateTime,
    },
    { title: "关联标的", dataIndex: "symbols", width: 150, render: listText },
    { title: "原始来源标识", dataIndex: "source_identifier", width: 170, render: nullable },
    { title: "Content Hash", dataIndex: "content_hash", width: 180 },
    { title: "处理状态", dataIndex: "processing_status", width: 120 },
    {
      title: "原始链接",
      dataIndex: "source_url",
      width: 130,
      render: (value: string | null) =>
        value ? (
          <a href={value} target="_blank" rel="noreferrer noopener">
            打开
          </a>
        ) : "-",
    },
    {
      title: "被 Skill 引用",
      width: 180,
      render: (_value, record) => referencedBy.get(record.evidence_id)?.join(", ") || "-",
    },
  ];
  return (
    <Card className="tool-card" title="Evidence">
      <Table
        rowKey="evidence_id"
        columns={columns}
        dataSource={detail.evidence}
        pagination={false}
        locale={{ emptyText: <EmptyState description="暂无 Evidence" /> }}
        scroll={{ x: 1200 }}
      />
    </Card>
  );
}

function SkillReportsSection({ reports }: { reports: AgentReport[] }) {
  return (
    <Card className="tool-card" title="Skill Reports">
      {!reports.length ? <EmptyState description="暂无 Skill Report" /> : null}
      <Collapse
        defaultActiveKey={reports
          .filter((report) => isReportFailure(report))
          .map((report) => report.report_id)}
        items={reports.map((report) => ({
          key: report.report_id,
          label: `${skillName(report.role)} / ${report.report_id}`,
          children: (
            <Space orientation="vertical" className="full-width" size="middle">
              {isReportFailure(report) ? (
                <Alert type="warning" showIcon title={report.raw_reference ?? report.summary} />
              ) : null}
              <Descriptions bordered size="small" column={2}>
                <Descriptions.Item label="Skill 名称">{skillName(report.role)}</Descriptions.Item>
                <Descriptions.Item label="状态"><StatusTag value={report.status} /></Descriptions.Item>
                <Descriptions.Item label="结论或摘要">{report.summary}</Descriptions.Item>
                <Descriptions.Item label="信号或方向">{report.stance}</Descriptions.Item>
                <Descriptions.Item label="置信度">{formatPercent(report.confidence)}</Descriptions.Item>
                <Descriptions.Item label="Evidence 引用">
                  {report.evidence_ids.join(", ") || "-"}
                </Descriptions.Item>
                <Descriptions.Item label="来源">{report.source}</Descriptions.Item>
                <Descriptions.Item label="创建时间">
                  {formatDateTime(report.created_at)}
                </Descriptions.Item>
                <Descriptions.Item label="失败原因">
                  {isReportFailure(report) ? report.raw_reference ?? report.summary : "-"}
                </Descriptions.Item>
              </Descriptions>
              <Collapse
                ghost
                items={[
                  {
                    key: "json",
                    label: "结构化输出",
                    children: <pre className="json-block">{JSON.stringify(report, null, 2)}</pre>,
                  },
                ]}
              />
            </Space>
          ),
        }))}
      />
    </Card>
  );
}

function HypothesisSection({ hypotheses }: { hypotheses: Hypothesis[] }) {
  return (
    <Card className="tool-card" title="Hypothesis">
      {!hypotheses.length ? <EmptyState description="暂无 Hypothesis" /> : null}
      <Space orientation="vertical" className="full-width">
        {hypotheses.map((hypothesis) => (
          <Descriptions key={hypothesis.hypothesis_id} bordered size="small" column={2}>
            <Descriptions.Item label="内容">{hypothesis.statement}</Descriptions.Item>
            <Descriptions.Item label="假设来源">
              {hypothesis.supporting_report_ids.join(", ") || "-"}
            </Descriptions.Item>
            <Descriptions.Item label="Rationale">{hypothesis.rationale}</Descriptions.Item>
            <Descriptions.Item label="方向">{hypothesis.direction}</Descriptions.Item>
            <Descriptions.Item label="时间周期">{hypothesis.horizon_days} 天</Descriptions.Item>
            <Descriptions.Item label="支持证据">
              {hypothesis.supporting_evidence_ids.join(", ") || "-"}
            </Descriptions.Item>
            <Descriptions.Item label="反对证据">-</Descriptions.Item>
            <Descriptions.Item label="初始置信度">
              {formatPercent(hypothesis.confidence)}
            </Descriptions.Item>
            <Descriptions.Item label="修订状态"><StatusTag value={hypothesis.status} /></Descriptions.Item>
            <Descriptions.Item label="关键条件">-</Descriptions.Item>
            <Descriptions.Item label="预期时间范围">
              {hypothesis.horizon_days} 天
            </Descriptions.Item>
          </Descriptions>
        ))}
      </Space>
    </Card>
  );
}

function DiscussionSection({ detail }: { detail: ResearchRunDetail }) {
  const discussion = detail.discussion;
  return (
    <Card className="tool-card" title="Discussion">
      <Tabs
        defaultActiveKey="review"
        items={[
          {
            key: "blind",
            label: "第一阶段：盲报",
            children: (
              <Timeline
                items={detail.skill_reports.map((report) => ({
                  content: `${skillName(report.role)}: ${report.summary}`,
                }))}
              />
            ),
          },
          {
            key: "review",
            label: "第二阶段：讨论与修订",
            children: (
              <Space orientation="vertical" className="full-width">
                {discussion.statements.map((statement) => (
                  <Alert
                    key={statement.statement_id}
                    type="info"
                    showIcon
                    title={`${statement.stance}: ${statement.reasoning}`}
                    description={`confidence ${formatPercent(statement.confidence_before)} -> ${formatPercent(statement.confidence_after)}`}
                  />
                ))}
                <Descriptions bordered size="small" column={2}>
                  <Descriptions.Item label="冲突识别">
                    {discussion.debates.map((debate) => debate.status).join(", ") || "-"}
                  </Descriptions.Item>
                  <Descriptions.Item label="证据复核">
                    {discussion.proposal?.evidence_ids.join(", ") || "-"}
                  </Descriptions.Item>
                  <Descriptions.Item label="反方审查">
                    {discussion.risk_review?.reasons.join(", ") || "-"}
                  </Descriptions.Item>
                  <Descriptions.Item label="修订建议">
                    {discussion.risk_review?.condition_changes.join(", ") || "-"}
                  </Descriptions.Item>
                  <Descriptions.Item label="最终总结">
                    {discussion.proposal?.thesis ?? "-"}
                  </Descriptions.Item>
                  <Descriptions.Item label="Proposal">
                    {discussion.proposal
                      ? `${discussion.proposal.proposal_id}: ${discussion.proposal.conclusion}`
                      : "-"}
                  </Descriptions.Item>
                  <Descriptions.Item label="Risk Review">
                    {discussion.risk_review
                      ? `${discussion.risk_review.risk_review_id}: ${discussion.risk_review.verdict}`
                      : "-"}
                  </Descriptions.Item>
                  <Descriptions.Item label="Assembly">
                    {discussion.assembly
                      ? `${discussion.assembly.assembly_id}: ${discussion.assembly.conclusion}`
                      : "-"}
                  </Descriptions.Item>
                  <Descriptions.Item label="最终置信度">
                    {formatPercent(discussion.risk_review?.final_confidence)}
                  </Descriptions.Item>
                </Descriptions>
              </Space>
            ),
          },
        ]}
      />
    </Card>
  );
}

function DecisionSection({
  decision,
  runStatus,
}: {
  decision: Decision | null;
  runStatus: string;
}) {
  return (
    <Card className="tool-card" title="Decision">
      {!decision ? (
        <Alert
          type={runStatus === "failed" ? "warning" : "info"}
          showIcon
          title={runStatus === "failed" ? "Decision 生成失败" : "Decision 尚未生成"}
        />
      ) : (
        <Descriptions bordered size="small" column={2}>
          <Descriptions.Item label="Decision ID">{decision.decision_id}</Descriptions.Item>
          <Descriptions.Item label="Decision">{decision.action}</Descriptions.Item>
          <Descriptions.Item label="置信度">{formatPercent(decision.confidence)}</Descriptions.Item>
          <Descriptions.Item label="时间周期">{decision.horizon}</Descriptions.Item>
          <Descriptions.Item label="决策理由">{decision.reasoning_summary}</Descriptions.Item>
          <Descriptions.Item label="入场条件">{decision.entry_conditions.join(", ") || "-"}</Descriptions.Item>
          <Descriptions.Item label="失效条件">
            {decision.invalidation_conditions.join(", ") || "-"}
          </Descriptions.Item>
          <Descriptions.Item label="风险说明">{decision.risk_factors.join(", ") || "-"}</Descriptions.Item>
          <Descriptions.Item label="Evidence 引用">{decision.evidence_ids.join(", ")}</Descriptions.Item>
          <Descriptions.Item label="no_trade 原因">
            {[...decision.unavailable_fields, ...decision.downgrade_reasons].join(", ") || "-"}
          </Descriptions.Item>
          <Descriptions.Item label="状态"><StatusTag value={decision.status} /></Descriptions.Item>
          <Descriptions.Item label="创建时间">{formatDateTime(decision.created_at)}</Descriptions.Item>
        </Descriptions>
      )}
    </Card>
  );
}

function TradePlanSection({ tradePlan }: { tradePlan: TradePlan | null }) {
  return (
    <Card className="tool-card" title="Trade Plan">
      {!tradePlan ? (
        <EmptyState description="暂无 Trade Plan" />
      ) : (
        <Descriptions bordered size="small" column={2}>
          <Descriptions.Item label="Trade Plan ID">{tradePlan.trade_plan_id}</Descriptions.Item>
          <Descriptions.Item label="方向">{tradePlan.direction}</Descriptions.Item>
          <Descriptions.Item label="标的">{tradePlan.symbol}</Descriptions.Item>
          <Descriptions.Item label="入场计划">
            {tradePlan.planned_entry.join(", ") || "-"}
          </Descriptions.Item>
          <Descriptions.Item label="Entry Price 或价格区间">
            {tradePlan.target?.join(" - ") ?? "-"}
          </Descriptions.Item>
          <Descriptions.Item label="风险条件">
            {tradePlan.invalidation_conditions.join(", ") || "-"}
          </Descriptions.Item>
          <Descriptions.Item label="目标周期">{tradePlan.horizon}</Descriptions.Item>
          <Descriptions.Item label="Stop Loss">{tradePlan.stop_loss ?? "-"}</Descriptions.Item>
          <Descriptions.Item label="Take Profit">
            {tradePlan.target?.join(" - ") ?? "-"}
          </Descriptions.Item>
          <Descriptions.Item label="失效条件">
            {tradePlan.invalidation_conditions.join(", ") || "-"}
          </Descriptions.Item>
          <Descriptions.Item label="仓位或规模">
            {tradePlan.planned_position === null ? "-" : formatPercent(tradePlan.planned_position)}
          </Descriptions.Item>
          <Descriptions.Item label="状态"><StatusTag value={tradePlan.status} /></Descriptions.Item>
          <Descriptions.Item label="Risk Budget">
            {tradePlan.planned_position === null ? "-" : formatPercent(tradePlan.planned_position)}
          </Descriptions.Item>
        </Descriptions>
      )}
    </Card>
  );
}

function evidenceReferences(reports: AgentReport[]) {
  const result = new Map<string, string[]>();
  for (const report of reports) {
    for (const evidenceId of report.evidence_ids) {
      result.set(evidenceId, [...(result.get(evidenceId) ?? []), skillName(report.role)]);
    }
  }
  return result;
}

function skillName(role: string) {
  const mapping: Record<string, string> = {
    technical: "technical_trend",
    fundamental: "sector_strength",
    news: "announcement_risk",
    sentiment: "market_sentiment",
    capital_flow: "policy_impact",
  };
  return mapping[role] ?? role;
}

function isReportFailure(report: AgentReport) {
  return Boolean(report.raw_reference?.toLowerCase().includes("error")) || report.confidence === 0;
}

function listText(values: string[]) {
  return values.join(", ") || "-";
}

function nullable(value: unknown) {
  return value ?? "-";
}

function errorMessage(error: unknown) {
  if (error instanceof ApiError) return error.readableMessage;
  if (error instanceof Error) return error.message;
  return "Backend request failed";
}
