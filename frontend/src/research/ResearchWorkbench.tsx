import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  AlertCircle,
  CheckCircle2,
  FileText,
  ListPlus,
  Loader2,
  RefreshCw,
  Send,
} from "lucide-react";
import type { Dispatch, ReactNode, SetStateAction } from "react";
import { useEffect, useMemo, useState } from "react";

import type {
  AgentReport,
  AssemblySettlementResponse,
  Debate,
  DecisionAssembly,
  DecisionProposal,
  Evidence,
  Hypothesis,
  ResearchSession,
  RiskReview,
  WatchlistItem,
} from "./api";
import { ApiError, researchApi } from "./api";

type ChainState = {
  watchlist?: WatchlistItem;
  evidence?: Evidence;
  session?: ResearchSession;
  report?: AgentReport;
  hypothesis?: Hypothesis;
  debate?: Debate;
  proposal?: DecisionProposal;
  riskReview?: RiskReview;
  assembly?: DecisionAssembly;
  settlement?: AssemblySettlementResponse;
};

type StageKey = "watchlist" | "research" | "analysis" | "debate" | "decision";
type StageStatus = "等待" | "进行中" | "已完成" | "失败";

type OperationState = {
  stage: StageKey;
  label: string;
  phase: "进行中" | "完成" | "失败";
} | null;

const nowIso = () => new Date().toISOString();
const inHoursIso = (hours: number) =>
  new Date(Date.now() + hours * 60 * 60 * 1000).toISOString();

export function ResearchWorkbench() {
  const queryClient = useQueryClient();
  const [chain, setChain] = useState<ChainState>({});
  const [operation, setOperation] = useState<OperationState>(null);
  const [error, setError] = useState<string | null>(null);
  const [watchSymbol, setWatchSymbol] = useState("600519");
  const [watchMarket, setWatchMarket] = useState("CN");
  const [watchNote, setWatchNote] = useState("人工验收");
  const [watchAutoResearch, setWatchAutoResearch] = useState(false);
  const [watchScheduleTime, setWatchScheduleTime] = useState("15:00:00");
  const [watchScheduleTimezone, setWatchScheduleTimezone] =
    useState("Asia/Shanghai");
  const [evidenceSummary, setEvidenceSummary] = useState("人工验收证据");
  const [evidenceHash, setEvidenceHash] = useState(() => `manual-${Date.now()}`);
  const [sessionAsOf, setSessionAsOf] = useState(inHoursIso(1));
  const [horizonDays, setHorizonDays] = useState(3);
  const [reportSummary, setReportSummary] = useState("技术报告支持假设");
  const [hypothesisText, setHypothesisText] = useState("价格趋势支持上行");
  const [proposalThesis, setProposalThesis] = useState("基于证据和辩论形成买入提案");
  const [settleAsOf, setSettleAsOf] = useState("");

  const watchlistQuery = useQuery({
    queryKey: ["watchlist"],
    queryFn: () => researchApi.listWatchlist(),
  });
  const evidenceQuery = useQuery({
    queryKey: ["evidence"],
    queryFn: () => researchApi.listEvidence(),
  });
  const sessionQuery = useQuery({
    queryKey: ["sessions"],
    queryFn: () => researchApi.listSessions(),
  });
  const reportsQuery = useQuery({
    queryKey: ["reports", chain.session?.research_session_id],
    queryFn: () => researchApi.listAgentReports(chain.session!.research_session_id),
    enabled: Boolean(chain.session),
  });
  const hypothesesQuery = useQuery({
    queryKey: ["hypotheses", chain.session?.research_session_id],
    queryFn: () => researchApi.listHypotheses(chain.session!.research_session_id),
    enabled: Boolean(chain.session),
  });
  const debatesQuery = useQuery({
    queryKey: ["debates", chain.session?.research_session_id],
    queryFn: () => researchApi.listDebates(chain.session!.research_session_id),
    enabled: Boolean(chain.session),
  });

  const loading =
    watchlistQuery.isLoading ||
    evidenceQuery.isLoading ||
    sessionQuery.isLoading;

  const mutations = useLifecycleMutations({
    chain,
    setChain,
    setError,
    setEvidenceHash,
    setOperation,
    invalidate: () =>
      queryClient.invalidateQueries({
        predicate: (query) =>
          ["watchlist", "evidence", "sessions"].includes(
            String(query.queryKey[0]),
          ),
      }),
  });

  const watchlistItems = useMemo(
    () => sortByCreatedAt(watchlistQuery.data?.items ?? []),
    [watchlistQuery.data?.items],
  );

  useEffect(() => {
    if (!chain.watchlist) return;
    setWatchAutoResearch(chain.watchlist.auto_research_enabled);
    setHorizonDays(chain.watchlist.research_horizon_days);
    setWatchScheduleTime(chain.watchlist.schedule_time);
    setWatchScheduleTimezone(chain.watchlist.schedule_timezone);
  }, [chain.watchlist]);
  const evidenceItems = useMemo(
    () => sortByCreatedAt(evidenceQuery.data?.items ?? []),
    [evidenceQuery.data?.items],
  );
  const sessionItems = useMemo(
    () => sortByCreatedAt(sessionQuery.data?.items ?? []),
    [sessionQuery.data?.items],
  );
  const reportItems = useMemo(
    () => sortByCreatedAt(reportsQuery.data?.items ?? []),
    [reportsQuery.data?.items],
  );
  const hypothesisItems = useMemo(
    () => sortByCreatedAt(hypothesesQuery.data?.items ?? []),
    [hypothesesQuery.data?.items],
  );
  const debateItems = useMemo(
    () => sortByCreatedAt(debatesQuery.data?.items ?? []),
    [debatesQuery.data?.items],
  );

  useEffect(() => {
    if (!chain.session && sessionItems[0]) {
      setChain((current) => ({ ...current, session: sessionItems[0] }));
    }
  }, [chain.session, sessionItems]);

  useEffect(() => {
    if (!chain.session) return;
    const watchlist = watchlistItems.find(
      (item) => item.watchlist_item_id === chain.session?.scope.watchlist_item_id,
    );
    const evidence = evidenceItems.find((item) =>
      chain.session?.evidence_ids.includes(item.evidence_id),
    );
    setChain((current) => ({
      ...current,
      watchlist: current.watchlist ?? watchlist,
      evidence: current.evidence ?? evidence,
    }));
  }, [chain.session, evidenceItems, watchlistItems]);

  useEffect(() => {
    if (!chain.session) return;
    setChain((current) => ({
      ...current,
      report: current.report ?? reportItems[0],
      hypothesis: current.hypothesis ?? hypothesisItems[0],
      debate: current.debate ?? debateItems[0],
    }));
  }, [chain.session, debateItems, hypothesisItems, reportItems]);

  const currentStep = useMemo(
    () =>
      currentStatus(
        chain,
        reportItems.length,
        hypothesisItems.length,
        debateItems.length,
        operation,
      ),
    [chain, debateItems.length, hypothesisItems.length, operation, reportItems.length],
  );

  const operationText = operation
    ? `${operation.label}${operation.phase}`
    : "等待操作";

  const settlementNotDue = isSettlementNotDue(chain, settleAsOf);
  const finalizeReason = !chain.proposal
    ? "请先创建决策建议。"
    : !chain.riskReview
      ? "请先完成风险审核。"
      : undefined;
  const settlementReason = !chain.assembly
    ? "请先生成最终决策。"
    : settlementNotDue
      ? "尚未到达预测截止时间"
      : undefined;

  return (
    <main className="acceptance-page">
      <header className="acceptance-header">
        <div>
          <h1>AIOS 人工验收工作台</h1>
          <p>用于手动验证从自选股票到学习记录的完整流程。</p>
        </div>
        <div className="status-strip">
          {loading ? <Loader2 className="spin" size={18} /> : <CheckCircle2 size={18} />}
          <span>当前状态：{currentStep}</span>
        </div>
      </header>

      <section className="ops-bar">
        <button type="button" onClick={() => void refreshAll(queryClient)}>
          <RefreshCw size={16} />
          刷新
        </button>
        <span>{operationText}</span>
      </section>

      {error ? (
        <section className="error-banner" role="alert">
          <AlertCircle size={18} />
          <span>{error}</span>
        </section>
      ) : null}

      <section className="flow-guide" aria-label="研究闭环流程">
        <span>① 自选股票</span>
        <b>↓</b>
        <span>② 证据与研究</span>
        <b>↓</b>
        <span>③ Agent 汇报与策略假设</span>
        <b>↓</b>
        <span>④ 辩论、决策建议、风险审核</span>
        <b>↓</b>
        <span>⑤ 最终决策、结算、学习</span>
      </section>

      <section className="acceptance-grid">
        <Panel
          title="1 自选股票"
          icon={<ListPlus size={18} />}
          status={stageStatus("watchlist", Boolean(chain.watchlist), operation)}
        >
          <div className="form-grid">
            <label>
              股票
              <input
                value={watchSymbol}
                onChange={(event) => setWatchSymbol(event.target.value)}
              />
            </label>
            <label>
              市场
              <input
                value={watchMarket}
                onChange={(event) => setWatchMarket(event.target.value)}
              />
            </label>
            <label className="wide-field">
              备注
              <input
                value={watchNote}
                onChange={(event) => setWatchNote(event.target.value)}
              />
            </label>
          </div>
          <ActionButton
            label="新增股票"
            pending={mutations.addWatchlist.isPending}
            onClick={() =>
              mutations.addWatchlist.mutate({
                symbol: watchSymbol,
                market: watchMarket,
                note: watchNote,
              })
            }
          />
          <div className="form-grid">
            <label className="inline-option">
              <input
                type="checkbox"
                checked={watchAutoResearch}
                onChange={(event) => setWatchAutoResearch(event.target.checked)}
              />
              自动研究
            </label>
            <label>
              研究周期
              <select
                value={horizonDays}
                onChange={(event) => setHorizonDays(Number(event.target.value))}
              >
                <option value={1}>1d</option>
                <option value={3}>3d</option>
                <option value={7}>1w</option>
              </select>
            </label>
            <label>
              运行时间
              <input
                value={watchScheduleTime}
                onChange={(event) => setWatchScheduleTime(event.target.value)}
              />
            </label>
            <label>
              时区
              <input
                value={watchScheduleTimezone}
                onChange={(event) =>
                  setWatchScheduleTimezone(event.target.value)
                }
              />
            </label>
          </div>
          <ActionButton
            label="保存调度"
            pending={mutations.updateWatchlist.isPending}
            disabledReason={
              chain.watchlist ? undefined : "请先新增或选择自选股票。"
            }
            onClick={() =>
              mutations.updateWatchlist.mutate({
                auto_research_enabled: watchAutoResearch,
                research_horizon_days: horizonDays,
                schedule_time: watchScheduleTime,
                schedule_timezone: watchScheduleTimezone,
              })
            }
          />
          <ActionButton
            label="手动运行研究"
            pending={mutations.runWatchlist.isPending}
            disabledReason={
              chain.watchlist ? undefined : "请先新增或选择自选股票。"
            }
            onClick={() => mutations.runWatchlist.mutate(undefined)}
          />
          <EntityList
            items={watchlistItems}
            getId={(item) => item.watchlist_item_id}
            getTitle={(item) => `${item.symbol} / ${item.market}`}
            getCreatedAt={(item) => item.created_at}
            getStatus={(item) => translateStatus(item.status)}
            selectedId={chain.watchlist?.watchlist_item_id}
            onSelect={(item) => selectWatchlist(item, setChain)}
          />
          <AdvancedInfo
            rows={[
              ["自选股票内部编号", chain.watchlist?.watchlist_item_id],
              ["状态原值", chain.watchlist?.status],
              [
                "自动研究",
                chain.watchlist?.auto_research_enabled ? "已开启" : "已关闭",
              ],
              ["研究周期", chain.watchlist?.research_horizon_days],
              ["运行时间", chain.watchlist?.schedule_time],
              ["调度时区", chain.watchlist?.schedule_timezone],
              ["下次运行", formatOptionalDateTime(chain.watchlist?.next_run_at)],
              ["上次运行", formatOptionalDateTime(chain.watchlist?.last_run_at)],
            ]}
          />
        </Panel>

        <Panel
          title="2 证据与研究"
          icon={<FileText size={18} />}
          status={stageStatus(
            "research",
            Boolean(chain.evidence && chain.session),
            operation,
          )}
        >
          <label>
            证据摘要
            <textarea
              value={evidenceSummary}
              onChange={(event) => setEvidenceSummary(event.target.value)}
            />
          </label>
          <ActionButton
            label="创建证据"
            pending={mutations.createEvidence.isPending}
            onClick={() =>
              mutations.createEvidence.mutate({
                summary: evidenceSummary,
                hash: evidenceHash,
              })
            }
          />
          <div className="form-grid">
            <label>
              研究时间
              <input
                value={sessionAsOf}
                onChange={(event) => setSessionAsOf(event.target.value)}
              />
            </label>
            <label>
              预测天数
              <input
                type="number"
                value={horizonDays}
                onChange={(event) => setHorizonDays(Number(event.target.value))}
              />
            </label>
          </div>
          <ActionButton
            label="创建研究会话"
            pending={mutations.createSession.isPending}
            disabledReason={sessionDisabledReason(chain)}
            onClick={() =>
              mutations.createSession.mutate({
                asOf: sessionAsOf,
                horizonDays,
              })
            }
          />
          <EntityList
            items={evidenceItems}
            getId={(item) => item.evidence_id}
            getTitle={(item) => item.summary}
            getCreatedAt={(item) => item.created_at}
            getStatus={() => "已创建"}
            selectedId={chain.evidence?.evidence_id}
            onSelect={(item) => selectEvidence(item, setChain)}
          />
          <EntityList
            items={sessionItems}
            getId={(item) => item.research_session_id}
            getTitle={(item) => `${item.scope.symbol} / ${translateStatus(item.status)}`}
            getCreatedAt={(item) => item.created_at}
            getStatus={(item) => translateStatus(item.status)}
            selectedId={chain.session?.research_session_id}
            onSelect={(item) => selectSession(item, setChain)}
          />
          <AdvancedInfo
            rows={[
              ["证据内部编号", chain.evidence?.evidence_id],
              ["证据唯一标识", chain.evidence?.content_hash],
              ["研究会话内部编号", chain.session?.research_session_id],
              ["预测截止时间", chain.session?.scope.valid_until],
            ]}
          />
        </Panel>

        <Panel
          title="3 Agent 汇报与假设"
          status={stageStatus(
            "analysis",
            Boolean(chain.report && chain.hypothesis),
            operation,
          )}
        >
          <label>
            Agent 汇报摘要
            <textarea
              value={reportSummary}
              onChange={(event) => setReportSummary(event.target.value)}
            />
          </label>
          <ActionButton
            label="提交 Agent 汇报"
            pending={mutations.createReport.isPending}
            disabledReason={reportDisabledReason(chain)}
            onClick={() => mutations.createReport.mutate(reportSummary)}
          />
          <label>
            策略假设
            <textarea
              value={hypothesisText}
              onChange={(event) => setHypothesisText(event.target.value)}
            />
          </label>
          <ActionButton
            label="提交策略假设"
            pending={mutations.createHypothesis.isPending}
            disabledReason={hypothesisDisabledReason(chain)}
            onClick={() => mutations.createHypothesis.mutate(hypothesisText)}
          />
          <EntityList
            items={reportItems}
            getId={(item) => item.report_id}
            getTitle={(item) => `${translateRole(item.role)}：${item.summary}`}
            getCreatedAt={(item) => item.created_at}
            getStatus={(item) => translateStatus(item.status)}
            selectedId={chain.report?.report_id}
            onSelect={(item) => setChain((current) => ({ ...current, report: item }))}
          />
          <EntityList
            items={hypothesisItems}
            getId={(item) => item.hypothesis_id}
            getTitle={(item) => item.statement}
            getCreatedAt={(item) => item.created_at}
            getStatus={(item) => translateStatus(item.status)}
            selectedId={chain.hypothesis?.hypothesis_id}
            onSelect={(item) =>
              setChain((current) => ({ ...current, hypothesis: item }))
            }
          />
          <AdvancedInfo
            rows={[
              ["Agent 汇报内部编号", chain.report?.report_id],
              ["策略假设内部编号", chain.hypothesis?.hypothesis_id],
              ["置信度", chain.hypothesis?.confidence],
            ]}
          />
        </Panel>

        <Panel
          title="4 辩论、建议与风险审核"
          status={stageStatus(
            "debate",
            Boolean(chain.debate && chain.proposal && chain.riskReview),
            operation,
          )}
        >
          <ActionButton
            label="创建辩论"
            pending={mutations.createDebate.isPending}
            disabledReason={!chain.session ? "请先创建研究会话。" : undefined}
            onClick={() => mutations.createDebate.mutate(undefined)}
          />
          <ActionButton
            label="提交辩论意见"
            pending={mutations.addStatement.isPending}
            disabledReason={statementDisabledReason(chain)}
            onClick={() => mutations.addStatement.mutate(undefined)}
          />
          <label>
            决策建议说明
            <textarea
              value={proposalThesis}
              onChange={(event) => setProposalThesis(event.target.value)}
            />
          </label>
          <ActionButton
            label="创建决策建议"
            pending={mutations.createProposal.isPending}
            disabledReason={proposalDisabledReason(chain)}
            onClick={() => mutations.createProposal.mutate(proposalThesis)}
          />
          <ActionButton
            label="提交风险审核"
            pending={mutations.createRiskReview.isPending}
            disabledReason={
              !chain.proposal ? "请先创建决策建议，再提交风险审核。" : undefined
            }
            onClick={() => mutations.createRiskReview.mutate(undefined)}
          />
          <EntityList
            items={debateItems}
            getId={(item) => item.debate_id}
            getTitle={(item) => `辩论状态：${translateStatus(item.status)}`}
            getCreatedAt={(item) => item.created_at}
            getStatus={(item) => translateStatus(item.status)}
            selectedId={chain.debate?.debate_id}
            onSelect={(item) => setChain((current) => ({ ...current, debate: item }))}
          />
          <AdvancedInfo
            rows={[
              ["辩论内部编号", chain.debate?.debate_id],
              ["决策建议内部编号", chain.proposal?.proposal_id],
              ["风险审核内部编号", chain.riskReview?.risk_review_id],
            ]}
          />
        </Panel>

        <Panel
          title="5 决策、结算与学习"
          status={stageStatus(
            "decision",
            Boolean(chain.assembly && chain.settlement),
            operation,
          )}
        >
          <ActionButton
            label="生成最终决策"
            pending={mutations.finalize.isPending}
            disabledReason={finalizeReason}
            onClick={() => mutations.finalize.mutate(undefined)}
          />
          <div className="settlement-status">
            <span>预测截止时间</span>
            <strong>{chain.session?.scope.valid_until || "等待研究会话"}</strong>
          </div>
          <div className="settlement-status">
            <span>当前结算状态</span>
            <strong>{settlementStatus(chain, settleAsOf)}</strong>
          </div>
          <div className="settlement-status">
            <span>预计可结算时间：</span>
            <strong>{chain.session?.scope.valid_until || "等待研究会话"}</strong>
          </div>
          <label>
            结算时间
            <input
              placeholder="留空使用后端当前时间"
              value={settleAsOf}
              onChange={(event) => setSettleAsOf(event.target.value)}
            />
          </label>
          <ActionButton
            label="执行结算"
            pending={mutations.settle.isPending}
            disabledReason={settlementReason}
            onClick={() => mutations.settle.mutate(settleAsOf || undefined)}
          />
          <DetailChain chain={chain} />
        </Panel>
      </section>
    </main>
  );
}

function useLifecycleMutations({
  chain,
  setChain,
  setError,
  setEvidenceHash,
  setOperation,
  invalidate,
}: {
  chain: ChainState;
  setChain: Dispatch<SetStateAction<ChainState>>;
  setError: (error: string | null) => void;
  setEvidenceHash: (hash: string) => void;
  setOperation: (operation: OperationState) => void;
  invalidate: () => Promise<unknown>;
}) {
  return {
    addWatchlist: useLifecycleMutation(
      "新增自选股票",
      "watchlist",
      (input: { symbol: string; market: string; note: string }) =>
        researchApi.addWatchlist(input.symbol, input.market, input.note),
      (watchlist) => setChain((current) => ({ ...current, watchlist })),
      setError,
      setOperation,
      invalidate,
    ),
    updateWatchlist: useLifecycleMutation(
      "保存自选股票调度",
      "watchlist",
      (input: {
        auto_research_enabled: boolean;
        research_horizon_days: number;
        schedule_time: string;
        schedule_timezone: string;
      }) =>
        researchApi.updateWatchlist(chain.watchlist!.watchlist_item_id, input),
      (watchlist) => setChain((current) => ({ ...current, watchlist })),
      setError,
      setOperation,
      invalidate,
    ),
    runWatchlist: useLifecycleMutation(
      "手动运行研究",
      "research",
      () => researchApi.runWatchlist(chain.watchlist!.watchlist_item_id),
      () => undefined,
      setError,
      setOperation,
      invalidate,
    ),
    createEvidence: useLifecycleMutation(
      "创建证据",
      "research",
      (input: { summary: string; hash: string }) =>
        researchApi.createManualEvidence({
          evidence_type: "manual_acceptance",
          source: "manual",
          symbols: [chain.watchlist?.symbol || "UNKNOWN"],
          published_at: nowIso(),
          available_at: nowIso(),
          summary: input.summary,
          reliability: 0.8,
          content_hash: input.hash,
          metadata: { acceptance_page: true },
        }),
      (evidence) => {
        setChain((current) => ({ ...current, evidence }));
        setEvidenceHash(`manual-${Date.now()}`);
      },
      setError,
      setOperation,
      invalidate,
    ),
    createSession: useLifecycleMutation(
      "创建研究会话",
      "research",
      (input: { asOf: string; horizonDays: number }) =>
        researchApi.createSession({
          watchlist_item_id: chain.watchlist!.watchlist_item_id,
          horizon_days: input.horizonDays,
          as_of: input.asOf,
          evidence_ids: [chain.evidence!.evidence_id],
        }),
      (session) => setChain((current) => ({ ...current, session })),
      setError,
      setOperation,
      invalidate,
    ),
    createReport: useLifecycleMutation(
      "提交 Agent 汇报",
      "analysis",
      (summary: string) =>
        researchApi.createAgentReport(chain.session!.research_session_id, {
          role: "technical",
          summary,
          stance: "buy",
          confidence: 0.7,
          evidence_ids: [chain.evidence!.evidence_id],
          source: "manual",
        }),
      (report) => setChain((current) => ({ ...current, report })),
      setError,
      setOperation,
      invalidate,
    ),
    createHypothesis: useLifecycleMutation(
      "提交策略假设",
      "analysis",
      (statement: string) =>
        researchApi.createHypothesis(chain.session!.research_session_id, {
          statement,
          rationale: "人工验收报告支持该假设",
          direction: "bullish",
          horizon_days: chain.session!.scope.horizon_days,
          confidence: 0.7,
          supporting_report_ids: [chain.report!.report_id],
          supporting_evidence_ids: [chain.evidence!.evidence_id],
        }),
      (hypothesis) => setChain((current) => ({ ...current, hypothesis })),
      setError,
      setOperation,
      invalidate,
    ),
    createDebate: useLifecycleMutation(
      "创建辩论",
      "debate",
      () => researchApi.createDebate(chain.session!.research_session_id),
      (debate) => setChain((current) => ({ ...current, debate })),
      setError,
      setOperation,
      invalidate,
    ),
    addStatement: useLifecycleMutation(
      "提交辩论意见",
      "debate",
      () =>
        researchApi.addDebateStatement(chain.debate!.debate_id, {
          agent_report_id: chain.report!.report_id,
          hypothesis_id: chain.hypothesis!.hypothesis_id,
          stance: "support",
          reasoning: "人工验收：报告支持假设",
          evidence_ids: chain.evidence ? [chain.evidence.evidence_id] : [],
          confidence_before: 0.5,
          confidence_after: 0.7,
        }),
      () => undefined,
      setError,
      setOperation,
      invalidate,
    ),
    createProposal: useLifecycleMutation(
      "创建决策建议",
      "debate",
      (thesis: string) =>
        researchApi.createProposal(chain.debate!.debate_id, {
          conclusion: "buy",
          confidence: 0.7,
          thesis,
          supporting_hypothesis_ids: [chain.hypothesis!.hypothesis_id],
          rejected_hypothesis_ids: [],
          evidence_ids: [chain.evidence!.evidence_id],
          risk_notes: ["人工验收风险记录"],
        }),
      (proposal) => setChain((current) => ({ ...current, proposal })),
      setError,
      setOperation,
      invalidate,
    ),
    createRiskReview: useLifecycleMutation(
      "提交风险审核",
      "debate",
      () =>
        researchApi.createRiskReview(chain.proposal!.proposal_id, {
          verdict: "approve",
          final_conclusion: "buy",
          final_confidence: 0.7,
          reasons: ["人工验收通过风险复核"],
        }),
      (riskReview) => setChain((current) => ({ ...current, riskReview })),
      setError,
      setOperation,
      invalidate,
    ),
    finalize: useLifecycleMutation(
      "生成最终决策",
      "decision",
      () => researchApi.finalizeProposal(chain.proposal!.proposal_id),
      (assembly) => setChain((current) => ({ ...current, assembly })),
      setError,
      setOperation,
      invalidate,
    ),
    settle: useLifecycleMutation(
      "执行结算",
      "decision",
      (asOf?: string) => researchApi.settleAssembly(chain.assembly!.assembly_id, asOf),
      (settlement) => setChain((current) => ({ ...current, settlement })),
      setError,
      setOperation,
      invalidate,
    ),
  };
}

function useLifecycleMutation<TInput, TResult>(
  label: string,
  stage: StageKey,
  action: (input: TInput) => Promise<TResult>,
  onSuccess: (result: TResult) => void,
  setError: (error: string | null) => void,
  setOperation: (operation: OperationState) => void,
  invalidate: () => Promise<unknown>,
) {
  return useMutation({
    mutationFn: action,
    onMutate: () => {
      setError(null);
      setOperation({ stage, label, phase: "进行中" });
    },
    onSuccess: async (result) => {
      onSuccess(result);
      setOperation({ stage, label, phase: "完成" });
      await invalidate();
    },
    onError: (err) => {
      setError(formatError(err));
      setOperation(
        isSettlementNotReadyError(err) ? null : { stage, label, phase: "失败" },
      );
    },
  });
}

function Panel({
  title,
  icon,
  status,
  children,
}: {
  title: string;
  icon?: ReactNode;
  status: StageStatus;
  children: ReactNode;
}) {
  return (
    <section className="acceptance-panel">
      <div className="acceptance-panel-title">
        <div className="panel-title-text">
          <span className="panel-heading">
            {icon}
            <h2>{title}</h2>
          </span>
          <StatusBadge status={status} />
        </div>
      </div>
      {children}
    </section>
  );
}

function StatusBadge({ status }: { status: StageStatus }) {
  return <span className={`stage-badge ${statusClass(status)}`}>{status}</span>;
}

function ActionButton({
  label,
  pending,
  disabledReason,
  onClick,
}: {
  label: string;
  pending: boolean;
  disabledReason?: string;
  onClick: () => void;
}) {
  const disabled = Boolean(disabledReason) || pending;
  return (
    <div className="action-block">
      <button
        className="acceptance-action"
        type="button"
        disabled={disabled}
        onClick={onClick}
      >
        {pending ? <Loader2 className="spin" size={15} /> : <Send size={15} />}
        {label}
      </button>
      {disabledReason ? <p className="disabled-reason">{disabledReason}</p> : null}
    </div>
  );
}

function EntityList<T>({
  items,
  getId,
  getTitle,
  getCreatedAt,
  getStatus,
  selectedId,
  onSelect,
}: {
  items: T[];
  getId: (item: T) => string;
  getTitle: (item: T) => string;
  getCreatedAt: (item: T) => string;
  getStatus: (item: T) => string;
  selectedId?: string;
  onSelect: (item: T) => void;
}) {
  if (!items.length) {
    return <p className="muted">暂无记录</p>;
  }
  return (
    <div className="entity-list">
      {items.map((item) => {
        const id = getId(item);
        return (
          <button
            className={id === selectedId ? "entity-row selected" : "entity-row"}
            key={id}
            type="button"
            onClick={() => onSelect(item)}
          >
            <strong>{getTitle(item)}</strong>
            <span>创建时间：{formatDateTime(getCreatedAt(item))}</span>
            <span>状态：{getStatus(item)}</span>
            <span>{id === selectedId ? "当前选中" : "点击选中"}</span>
          </button>
        );
      })}
    </div>
  );
}

function DetailChain({
  chain,
}: {
  chain: ChainState;
}) {
  const currentSettlement =
    chain.settlement?.record.research_session_id === chain.session?.research_session_id
      ? chain.settlement
      : undefined;
  const learningCount = currentSettlement?.learnings.length ?? 0;
  return (
    <div className="detail-chain">
      <Detail label="自选股票" done={Boolean(chain.watchlist)} />
      <Detail label="证据" done={Boolean(chain.evidence)} />
      <Detail label="研究会话" done={Boolean(chain.session)} />
      <Detail label="Agent 汇报" done={Boolean(chain.report)} />
      <Detail label="策略假设" done={Boolean(chain.hypothesis)} />
      <Detail label="辩论" done={Boolean(chain.debate)} />
      <Detail label="决策建议" done={Boolean(chain.proposal)} />
      <Detail label="风险审核" done={Boolean(chain.riskReview)} />
      <Detail label="最终决策" done={Boolean(chain.assembly)} />
      <Detail label="结算" done={Boolean(currentSettlement)} />
      <Detail label="评估" done={Boolean(currentSettlement?.evaluation)} />
      <Detail label="复盘" done={Boolean(currentSettlement?.review)} />
      <Detail
        label="学习记录"
        done={learningCount > 0}
        note={learningCount > 0 ? `${learningCount} 条` : "暂无学习记录"}
      />
      <AdvancedInfo
        rows={[
          ["最终决策内部编号", chain.assembly?.decision_id],
          ["结算记录内部编号", currentSettlement?.record.research_settlement_id],
          ["评估内部编号", currentSettlement?.evaluation.evaluation_id],
          ["复盘内部编号", currentSettlement?.review.review_id],
          [
            "学习记录内部编号",
            currentSettlement?.learnings
              .map((learning) => learning.learning_id)
              .join(", "),
          ],
        ]}
      />
    </div>
  );
}

function Detail({
  label,
  done,
  note,
}: {
  label: string;
  done: boolean;
  note?: string;
}) {
  return (
    <div className="detail-row">
      <span>{label}</span>
      <strong>{done ? "已生成" : "未生成"}</strong>
      {note ? <em>{note}</em> : null}
    </div>
  );
}

function AdvancedInfo({
  rows,
}: {
  rows: Array<[label: string, value: string | number | null | undefined]>;
}) {
  const [open, setOpen] = useState(false);
  const visibleRows = rows.filter(([, value]) => value !== undefined && value !== null);
  if (!visibleRows.length) return null;
  return (
    <div className="advanced-info">
      <button type="button" onClick={() => setOpen((current) => !current)}>
        高级信息
      </button>
      {open ? (
        <div className="advanced-info-body">
          {visibleRows.map(([label, value]) => (
            <div className="advanced-row" key={label}>
              <span>{label}</span>
              <strong>{String(value)}</strong>
            </div>
          ))}
        </div>
      ) : null}
    </div>
  );
}

async function refreshAll(queryClient: ReturnType<typeof useQueryClient>) {
  await queryClient.invalidateQueries();
}

function stageStatus(
  stage: StageKey,
  completed: boolean,
  operation: OperationState,
): StageStatus {
  if (operation?.stage === stage && operation.phase === "进行中") return "进行中";
  if (operation?.stage === stage && operation.phase === "失败") return "失败";
  if (completed) return "已完成";
  return "等待";
}

function statusClass(status: StageStatus) {
  return {
    等待: "stage-waiting",
    进行中: "stage-running",
    已完成: "stage-completed",
    失败: "stage-failed",
  }[status];
}

function currentStatus(
  chain: ChainState,
  reportCount: number,
  hypothesisCount: number,
  debateCount: number,
  operation: OperationState,
) {
  if (operation?.phase === "失败") return "失败";
  const currentSettlement =
    chain.settlement?.record.research_session_id === chain.session?.research_session_id
      ? chain.settlement
      : undefined;
  if (currentSettlement) return "已完成";
  if (chain.assembly) return "等待结算";
  if (chain.proposal && !chain.riskReview) return "等待风险审核";
  if (chain.riskReview) return "等待结算";
  if (chain.debate || debateCount > 0) return "辩论中";
  if (chain.session || reportCount > 0 || hypothesisCount > 0) return "研究中";
  if (chain.evidence) return "已创建证据";
  if (chain.watchlist) return "已创建自选股票";
  return "未开始";
}

function selectWatchlist(
  watchlist: WatchlistItem,
  setChain: Dispatch<SetStateAction<ChainState>>,
) {
  setChain((current) => ({
    ...current,
    watchlist,
    session: undefined,
    report: undefined,
    hypothesis: undefined,
    debate: undefined,
    proposal: undefined,
    riskReview: undefined,
    assembly: undefined,
    settlement: undefined,
  }));
}

function selectEvidence(
  evidence: Evidence,
  setChain: Dispatch<SetStateAction<ChainState>>,
) {
  setChain((current) => ({
    ...current,
    evidence,
    session: undefined,
    report: undefined,
    hypothesis: undefined,
    debate: undefined,
    proposal: undefined,
    riskReview: undefined,
    assembly: undefined,
    settlement: undefined,
  }));
}

function selectSession(
  session: ResearchSession,
  setChain: Dispatch<SetStateAction<ChainState>>,
) {
  setChain((current) => ({
    ...current,
    session,
    report: undefined,
    hypothesis: undefined,
    debate: undefined,
    proposal: undefined,
    riskReview: undefined,
    assembly: undefined,
    settlement: undefined,
  }));
}

function sortByCreatedAt<T extends { created_at: string }>(items: T[]) {
  return [...items].sort(
    (left, right) =>
      new Date(right.created_at).getTime() - new Date(left.created_at).getTime(),
  );
}

function formatDateTime(value: string) {
  return new Date(value).toLocaleString("zh-CN", {
    hour12: false,
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function formatOptionalDateTime(value: string | null | undefined) {
  return value ? formatDateTime(value) : undefined;
}

function sessionDisabledReason(chain: ChainState) {
  if (!chain.watchlist) return "请先新增或选择自选股票。";
  if (!chain.evidence) return "请先创建或选择证据。";
  return undefined;
}

function reportDisabledReason(chain: ChainState) {
  if (!chain.session) return "请先创建研究会话。";
  if (!chain.evidence) return "请先创建或选择证据。";
  return undefined;
}

function hypothesisDisabledReason(chain: ChainState) {
  if (!chain.session) return "请先创建研究会话。";
  if (!chain.report) return "请先提交 Agent 汇报。";
  if (!chain.evidence) return "请先创建或选择证据。";
  return undefined;
}

function statementDisabledReason(chain: ChainState) {
  if (!chain.debate) return "请先创建辩论。";
  if (!chain.report) return "请先提交 Agent 汇报。";
  if (!chain.hypothesis) return "请先提交策略假设。";
  return undefined;
}

function proposalDisabledReason(chain: ChainState) {
  if (!chain.debate) return "请先创建辩论。";
  if (!chain.hypothesis) return "请先提交策略假设。";
  if (!chain.evidence) return "请先创建或选择证据。";
  return undefined;
}

function formatError(error: unknown) {
  if (error instanceof ApiError) {
    if (isSettlementNotReadyError(error)) {
      return "尚未到达预测截止时间，暂时不能结算。";
    }
    if (
      error.message.includes(
        "DecisionProposal must have RiskReview before finalization",
      )
    ) {
      return "请先完成风险审核，再生成最终决策。";
    }
    if (error.code === "invalid_state_transition") {
      return "当前流程状态不允许执行此操作。";
    }
    if (error.code === "not_found") {
      return "未找到对应记录。";
    }
    if (error.code === "conflict") {
      return "当前记录已存在或操作发生冲突。";
    }
    return `操作失败：${error.message}`;
  }
  if (error instanceof Error) {
    return `操作失败：${error.message}`;
  }
  return "操作失败：未知错误";
}

function isSettlementNotDue(chain: ChainState, settleAsOf = "") {
  if (!chain.assembly || chain.settlement || !chain.session) return false;
  const validUntil = new Date(chain.session.scope.valid_until).getTime();
  if (!Number.isFinite(validUntil)) return false;
  const settlementTime = settleAsOf ? new Date(settleAsOf).getTime() : Date.now();
  if (!Number.isFinite(settlementTime)) return true;
  return settlementTime < validUntil;
}

function settlementStatus(chain: ChainState, settleAsOf = "") {
  if (chain.settlement) return "已结算";
  if (!chain.assembly) return "未结算";
  if (isSettlementNotDue(chain, settleAsOf)) return "尚未到期";
  return "可结算";
}

function isSettlementNotReadyError(error: unknown) {
  if (!(error instanceof ApiError)) return false;
  const message = error.message.toLowerCase();
  return (
    message.includes("session not ready") ||
    message.includes("not ready") ||
    message.includes("valid_until") ||
    message.includes("settlement time") ||
    message.includes("not reached") ||
    message.includes("not due")
  );
}

function translateStatus(status: string) {
  return (
    {
      active: "有效",
      archived: "已归档",
      cancelled: "已取消",
      open: "进行中",
      finalized: "已完成",
    }[status] ?? status
  );
}

function translateRole(role: string) {
  return (
    {
      technical: "技术分析",
      fundamental: "基本面分析",
      risk: "风险分析",
    }[role] ?? role
  );
}
