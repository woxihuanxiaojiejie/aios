import { useState, type ReactNode } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { BarChart3, Brain, FilePlus2, RefreshCw, Search } from "lucide-react";

import {
  ApiError,
  researchApi,
  type DecisionRunResponse,
  type EvidenceImportResponse,
  type HistoryResponse,
  type MarketResponse,
  type SettlementResponse,
} from "./api";
import { CandlestickChart } from "./CandlestickChart";
import { HistoryTable } from "./HistoryTable";

const DEFAULT_SYMBOL = "000001.SZ";

export function ResearchWorkbench() {
  const [input, setInput] = useState(DEFAULT_SYMBOL);
  const [symbol, setSymbol] = useState(DEFAULT_SYMBOL);
  const [evidence, setEvidence] = useState<EvidenceImportResponse | null>(null);
  const [decision, setDecision] = useState<DecisionRunResponse | null>(null);
  const [settlement, setSettlement] = useState<SettlementResponse | null>(null);
  const queryClient = useQueryClient();

  const market = useQuery({
    queryKey: ["market", symbol],
    queryFn: () => researchApi.market(symbol),
  });

  const history = useQuery({
    queryKey: ["history", symbol],
    queryFn: () => researchApi.history(symbol),
  });

  const evidenceMutation = useMutation({
    mutationFn: () => researchApi.createEvidence(symbol),
    onSuccess: async (result) => {
      setEvidence(result);
      await queryClient.invalidateQueries({ queryKey: ["history", symbol] });
    },
  });

  const decisionMutation = useMutation({
    mutationFn: async () => {
      const evidenceIds =
        evidence?.evidence_ids ??
        history.data?.latest_experiment?.evidence_ids ??
        (history.data?.latest_evidence
          ? [history.data.latest_evidence.evidence_id]
          : []);
      if (evidenceIds.length === 0) {
        throw new ApiError(
          400,
          "missing_evidence",
          "Create Evidence before running AI analysis.",
        );
      }
      const experiment = await researchApi.createExperiment(symbol, evidenceIds);
      return researchApi.runDecision(experiment.experiment_id, symbol, "1d");
    },
    onSuccess: async (result) => {
      setDecision(result);
      setSettlement(null);
      await queryClient.invalidateQueries({ queryKey: ["history", symbol] });
    },
  });

  const settlementMutation = useMutation({
    mutationFn: () => {
      const decisionId =
        decision?.decision.decision_id ?? history.data?.latest_decision?.decision_id;
      if (!decisionId) {
        throw new ApiError(
          400,
          "missing_decision",
          "Create or select a Decision before settlement.",
        );
      }
      return researchApi.settleDecision(decisionId);
    },
    onSuccess: async (result) => {
      setSettlement(result);
      await queryClient.invalidateQueries({ queryKey: ["history", symbol] });
    },
  });

  const activeDecision = decision?.decision ?? history.data?.latest_decision ?? null;
  const activeSettlement = settlement ?? fromHistory(history.data);

  return (
    <main className="shell">
      <header className="toolbar">
        <div>
          <h1>AIOS Research</h1>
          <p>REAL MARKET DATA · REAL LLM · PostgreSQL-backed workflow</p>
        </div>
        <form
          className="symbol-form"
          onSubmit={(event) => {
            event.preventDefault();
            setSymbol(input.trim().toUpperCase());
            setEvidence(null);
            setDecision(null);
            setSettlement(null);
          }}
        >
          <label htmlFor="symbol">Stock Symbol</label>
          <input
            id="symbol"
            value={input}
            onChange={(event) => setInput(event.target.value)}
            placeholder="000001.SZ"
          />
          <button type="submit">
            <Search size={16} />
            Load
          </button>
        </form>
      </header>

      <section className="status-strip">
        <Status label="Symbol" value={symbol} />
        <Status label="Market" value={market.data?.market ?? "Unavailable"} />
        <Status label="Market data" value={market.data?.data_source ?? "Pending"} />
        <Status label="Source" value={market.data?.source ?? "Unavailable"} />
        <Status
          label="Updated"
          value={market.data ? formatDateTime(market.data.available_at) : "Pending"}
        />
      </section>

      <div className="grid">
        <section className="panel market-panel">
          <SectionHeader
            icon={<BarChart3 size={18} />}
            title="Market"
            action={
              <button
                type="button"
                onClick={() => market.refetch()}
                disabled={market.isFetching}
              >
                <RefreshCw size={16} />
                Refresh
              </button>
            }
          />
          <AsyncState query={market} />
          {market.data ? <MarketSection market={market.data} /> : null}
        </section>

        <section className="panel action-panel">
          <SectionHeader icon={<FilePlus2 size={18} />} title="Evidence" />
          <button
            type="button"
            onClick={() => evidenceMutation.mutate()}
            disabled={!market.data || evidenceMutation.isPending}
          >
            <FilePlus2 size={16} />
            Create Evidence
          </button>
          <MutationState mutation={evidenceMutation} />
          <EvidenceSection evidence={evidence} history={history.data} />
        </section>

        <section className="panel decision-panel">
          <SectionHeader icon={<Brain size={18} />} title="AI Decision" />
          <button
            type="button"
            onClick={() => decisionMutation.mutate()}
            disabled={decisionMutation.isPending}
          >
            <Brain size={16} />
            Run AI Analysis
          </button>
          <MutationState mutation={decisionMutation} />
          <DecisionSection decision={decision} history={history.data} />
        </section>

        <section className="panel settlement-panel">
          <SectionHeader title="Settlement / Review" />
          <button
            type="button"
            onClick={() => settlementMutation.mutate()}
            disabled={!activeDecision || settlementMutation.isPending}
          >
            Settle Decision
          </button>
          {activeDecision ? (
            <p className="hint">
              Valid until {formatDateTime(activeDecision.valid_until)}. If this
              Decision is not due, the backend will reject settlement.
            </p>
          ) : null}
          <MutationState mutation={settlementMutation} />
          <SettlementSection settlement={activeSettlement} />
        </section>
      </div>

      <section className="panel history-panel">
        <SectionHeader title="History" />
        <AsyncState query={history} />
        <HistoryTable rows={history.data?.rows ?? []} />
      </section>
    </main>
  );
}

function MarketSection({ market }: { market: MarketResponse }) {
  return (
    <>
      <div className="quote-grid">
        <Metric label="Latest Price" value={market.latest.close} />
        <Metric label="Open" value={market.latest.open} />
        <Metric label="High" value={market.latest.high} />
        <Metric label="Low" value={market.latest.low} />
        <Metric label="Close" value={market.latest.close} />
        <Metric label="Change" value={market.change ?? "Unavailable"} />
        <Metric
          label="Change %"
          value={
            market.change_percent
              ? `${(Number(market.change_percent) * 100).toFixed(2)}%`
              : "Unavailable"
          }
        />
        <Metric label="Volume" value={market.latest.volume} />
        <Metric label="Observed" value={market.latest.trade_date} />
        <Metric label="Available" value={formatDateTime(market.available_at)} />
      </div>
      <CandlestickChart bars={market.bars} />
    </>
  );
}

function EvidenceSection({
  evidence,
  history,
}: {
  evidence: EvidenceImportResponse | null;
  history: HistoryResponse | undefined;
}) {
  const latest = evidence?.latest_evidence ?? history?.latest_evidence ?? null;
  if (!latest) {
    return <div className="empty-state">No Evidence has been created yet.</div>;
  }
  return (
    <dl className="detail-list">
      <Detail label="Evidence ID" value={latest.evidence_id} />
      <Detail label="Source" value={latest.source} />
      <Detail label="Observed" value={latest.published_at} />
      <Detail label="Available" value={latest.available_at} />
      <Detail label="Summary" value={latest.summary} />
    </dl>
  );
}

function DecisionSection({
  decision,
  history,
}: {
  decision: DecisionRunResponse | null;
  history: HistoryResponse | undefined;
}) {
  const active = decision?.decision ?? history?.latest_decision ?? null;
  const generation = decision?.generation ?? null;
  if (!active) {
    return <div className="empty-state">Run AI analysis to create a Decision.</div>;
  }
  const isNoTrade = ["hold", "observe", "no_trade"].includes(active.action);
  return (
    <dl className="detail-list">
      <Detail label="Symbol" value={active.symbol} />
      <Detail label="Direction" value={active.action} />
      <Detail label="No trade / abstain" value={isNoTrade ? "Yes" : "No"} />
      <Detail label="Confidence" value={`${Math.round(active.confidence * 100)}%`} />
      <Detail label="Horizon" value={active.horizon} />
      <Detail label="Thesis" value={active.reasoning_summary} />
      <Detail label="Evidence" value={active.evidence_ids.join(", ")} />
      <Detail label="Provider" value={generation?.provider ?? "Unavailable"} />
      <Detail label="Model" value={generation?.model ?? "Unavailable"} />
      <Detail label="Request ID" value={generation?.request_id ?? "Unavailable"} />
      <Detail label="Created" value={formatDateTime(active.created_at)} />
      <Detail label="Status" value={active.status} />
    </dl>
  );
}

function SettlementSection({
  settlement,
}: {
  settlement: SettlementResponse | null;
}) {
  if (!settlement) {
    return <div className="empty-state">No Settlement or Review yet.</div>;
  }
  return (
    <div className="settlement-grid">
      <dl className="detail-list">
        <h3>Outcome</h3>
        <Detail label="Entry" value={settlement.outcome.entry_price} />
        <Detail label="Exit" value={settlement.outcome.exit_price} />
        <Detail label="Return" value={settlement.outcome.realized_return} />
        <Detail label="Adverse" value={settlement.outcome.maximum_adverse_excursion} />
        <Detail label="Favorable" value={settlement.outcome.maximum_favorable_excursion} />
        <Detail label="Status" value={settlement.outcome.status} />
        <Detail label="Settled" value={formatDateTime(settlement.outcome.settled_at)} />
      </dl>
      <dl className="detail-list">
        <h3>Evaluation</h3>
        <Detail label="Direction" value={settlement.evaluation.directional_result} />
        <Detail label="Risk" value={settlement.evaluation.risk_result} />
        <Detail label="Final" value={settlement.evaluation.final_result} />
        <Detail label="Summary" value={settlement.evaluation.explanation} />
      </dl>
      <dl className="detail-list">
        <h3>Review</h3>
        <Detail label="Actual Return" value={settlement.review.actual_return} />
        <Detail
          label="Direction Correct"
          value={nullableBoolean(settlement.review.direction_correct)}
        />
        <Detail
          label="Risk Breached"
          value={nullableBoolean(settlement.review.risk_limit_breached)}
        />
        <Detail label="Outcome" value={settlement.review.outcome} />
        <Detail label="Tags" value={settlement.review.cause_tags.join(", ")} />
        <Detail label="Summary" value={settlement.review.review_summary} />
      </dl>
    </div>
  );
}

function fromHistory(history: HistoryResponse | undefined): SettlementResponse | null {
  if (
    !history?.latest_outcome ||
    !history.latest_evaluation ||
    !history.latest_review
  ) {
    return null;
  }
  return {
    outcome: history.latest_outcome,
    evaluation: history.latest_evaluation,
    review: history.latest_review,
  };
}

function AsyncState({
  query,
}: {
  query: { isLoading: boolean; isFetching: boolean; error: Error | null };
}) {
  if (query.isLoading) {
    return <div className="state">Loading...</div>;
  }
  if (query.error) {
    return <ErrorMessage error={query.error} />;
  }
  if (query.isFetching) {
    return <div className="state subtle">Refreshing...</div>;
  }
  return null;
}

function MutationState({
  mutation,
}: {
  mutation: { isPending: boolean; error: Error | null; isSuccess: boolean };
}) {
  if (mutation.isPending) {
    return <div className="state">Loading...</div>;
  }
  if (mutation.error) {
    return <ErrorMessage error={mutation.error} />;
  }
  if (mutation.isSuccess) {
    return <div className="state success">Saved.</div>;
  }
  return null;
}

function ErrorMessage({ error }: { error: Error }) {
  if (error instanceof ApiError) {
    return (
      <div className="state error">
        {error.code}: {error.message}
      </div>
    );
  }
  return <div className="state error">{error.message}</div>;
}

function SectionHeader({
  icon,
  title,
  action,
}: {
  icon?: ReactNode;
  title: string;
  action?: ReactNode;
}) {
  return (
    <div className="section-header">
      <h2>
        {icon}
        {title}
      </h2>
      {action}
    </div>
  );
}

function Status({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="metric">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function Detail({
  label,
  value,
}: {
  label: string;
  value: string | number | boolean | null;
}) {
  return (
    <>
      <dt>{label}</dt>
      <dd>{value === null || value === "" ? "Unavailable" : String(value)}</dd>
    </>
  );
}

function nullableBoolean(value: boolean | null) {
  if (value === null) {
    return "Unavailable";
  }
  return value ? "Yes" : "No";
}

function formatDateTime(value: string) {
  return new Intl.DateTimeFormat(undefined, {
    year: "numeric",
    month: "short",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));
}
