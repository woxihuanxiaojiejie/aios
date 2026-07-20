import {
  Bell,
  Building2,
  LineChart,
  Newspaper,
  Search,
  Sparkles,
} from "lucide-react";
import type { ReactNode } from "react";

import { CandlestickChart } from "./CandlestickChart";
import { HistoryTable } from "./HistoryTable";
import type { HistoryRow, MarketBar } from "./api";

const symbol = "000001.SZ";

const bars: MarketBar[] = [
  bar("2026-06-29", "10.22", "10.32", "10.02", "10.24", "112413978"),
  bar("2026-06-30", "10.22", "10.22", "10.04", "10.05", "111135281"),
  bar("2026-07-01", "10.05", "10.18", "9.99", "10.16", "90688982"),
  bar("2026-07-02", "10.20", "10.36", "10.17", "10.28", "100474867"),
  bar("2026-07-03", "10.29", "10.40", "10.18", "10.29", "86332664"),
  bar("2026-07-06", "10.25", "10.52", "10.22", "10.50", "106104863"),
  bar("2026-07-07", "10.46", "10.51", "10.35", "10.47", "80522115"),
  bar("2026-07-08", "10.44", "10.63", "10.34", "10.60", "95076022"),
  bar("2026-07-09", "10.55", "10.59", "10.43", "10.49", "74719101"),
  bar("2026-07-10", "10.50", "10.51", "10.40", "10.45", "95732035"),
  bar("2026-07-13", "10.42", "10.55", "10.38", "10.54", "92474624"),
  bar("2026-07-14", "10.53", "10.70", "10.48", "10.69", "119371535"),
  bar("2026-07-15", "10.65", "10.87", "10.63", "10.84", "98142155"),
  bar("2026-07-16", "10.85", "10.93", "10.72", "10.77", "80076623"),
  bar("2026-07-17", "10.75", "10.88", "10.72", "10.78", "107549901"),
];

const historyRows: HistoryRow[] = [
  {
    time: "2026-07-17T15:00:00Z",
    type: "预测",
    decision_id: "dc_1",
    direction: "观望",
    confidence: 0.8,
    realized_return: "--",
    review_outcome: "等待验证",
    status: "进行中",
  },
  {
    time: "2026-07-10T15:00:00Z",
    type: "预测",
    decision_id: "dc_2",
    direction: "谨慎看多",
    confidence: 0.6,
    realized_return: "+1.2%",
    review_outcome: "符合预期",
    status: "已复盘",
  },
  {
    time: "2026-07-03T15:00:00Z",
    type: "预测",
    decision_id: "dc_3",
    direction: "观望",
    confidence: 0.7,
    realized_return: "0.0%",
    review_outcome: "维持判断",
    status: "已复盘",
  },
];

export function ResearchWorkbench() {
  return (
    <main className="research-page">
      <header className="research-hero">
        <div className="search-shell">
          <Search className="search-icon" size={22} />
          <input
            aria-label="搜索股票"
            className="stock-search"
            placeholder="搜索股票（名称/代码）"
          />
          <button className="primary-action" type="button">
            开始研究
          </button>
        </div>
      </header>

      <section className="main-stage">
        <section className="market-workspace">
          <div className="section-title">
            <LineChart size={20} />
            <h2>行情与K线</h2>
          </div>
          <div className="ticker-summary">
            <div>
              <span>股票</span>
              <strong>平安银行 {symbol}</strong>
            </div>
            <div>
              <span>最新价</span>
              <strong>10.78</strong>
            </div>
            <div>
              <span>涨跌幅</span>
              <strong className="rise">+0.09%</strong>
            </div>
            <div>
              <span>成交量</span>
              <strong>1.08亿</strong>
            </div>
          </div>
          <CandlestickChart bars={bars} />
        </section>

        <aside className="research-report">
          <div className="section-title">
            <Sparkles size={20} />
            <h2>AI研究报告</h2>
          </div>
          <ReportBlock label="建议">
            <strong className="recommendation">观望</strong>
          </ReportBlock>
          <ReportBlock label="AI信心">
            <div className="stars" aria-label="四星信心">
              ★★★★☆
            </div>
          </ReportBlock>
          <ReportBlock label="主要观点">
            <p>近期价格维持窄幅震荡，量能尚未出现明确放大，趋势信号仍需等待确认。</p>
          </ReportBlock>
          <ReportBlock label="风险">
            <p>短线波动可能受大盘情绪和银行板块估值修复节奏影响。</p>
          </ReportBlock>
          <ReportBlock label="重点关注">
            <p>关注成交量变化、前高压力位表现，以及后续公告中的资产质量信息。</p>
          </ReportBlock>
        </aside>
      </section>

      <section className="insight-grid">
        <InfoPanel icon={<Newspaper size={18} />} title="新闻">
          <InfoLine label="今日新闻" value="暂无数据" />
          <InfoLine label="今天公告" value="暂无数据" />
        </InfoPanel>

        <InfoPanel icon={<Building2 size={18} />} title="公司信息">
          <InfoLine label="公司简介" value="--" />
          <InfoLine label="所属行业" value="--" />
          <InfoLine label="主营业务" value="--" />
          <InfoLine label="市值" value="--" />
          <InfoLine label="PE" value="--" />
          <InfoLine label="PB" value="--" />
        </InfoPanel>

        <InfoPanel title="历史预测" wide>
          <HistoryTable rows={historyRows} />
        </InfoPanel>

        <InfoPanel icon={<Bell size={18} />} title="AI复盘">
          <InfoLine label="收益" value="--" />
          <InfoLine label="评价" value="--" />
          <InfoLine label="原因" value="--" />
        </InfoPanel>
      </section>
    </main>
  );
}

function ReportBlock({
  label,
  children,
}: {
  label: string;
  children: ReactNode;
}) {
  return (
    <section className="report-block">
      <h3>{label}</h3>
      {children}
    </section>
  );
}

function InfoPanel({
  icon,
  title,
  wide = false,
  children,
}: {
  icon?: ReactNode;
  title: string;
  wide?: boolean;
  children: ReactNode;
}) {
  return (
    <section className={wide ? "info-panel wide-panel" : "info-panel"}>
      <div className="panel-heading">
        {icon}
        <h2>{title}</h2>
      </div>
      {children}
    </section>
  );
}

function InfoLine({ label, value }: { label: string; value: string }) {
  return (
    <div className="info-line">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function bar(
  tradeDate: string,
  open: string,
  high: string,
  low: string,
  close: string,
  volume: string,
): MarketBar {
  return {
    symbol,
    market: "CN_A",
    trade_date: tradeDate,
    open,
    high,
    low,
    close,
    volume,
    amount: null,
    adjustment: "none",
    source: "前端静态展示",
    fetched_at: "2026-07-19T10:00:00Z",
  };
}
