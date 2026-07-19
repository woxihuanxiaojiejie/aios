import { useEffect, useRef } from "react";
import {
  createChart,
  type CandlestickData,
  type HistogramData,
  type IChartApi,
  type UTCTimestamp,
} from "lightweight-charts";

import type { MarketBar } from "./api";

type Props = {
  bars: MarketBar[];
};

export function CandlestickChart({ bars }: Props) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const chartRef = useRef<IChartApi | null>(null);

  useEffect(() => {
    if (!containerRef.current) {
      return;
    }
    const chart = createChart(containerRef.current, {
      height: 360,
      layout: {
        background: { color: "#ffffff" },
        textColor: "#253040",
      },
      grid: {
        vertLines: { color: "#edf1f5" },
        horzLines: { color: "#edf1f5" },
      },
      rightPriceScale: {
        borderColor: "#d8dee8",
      },
      timeScale: {
        borderColor: "#d8dee8",
        timeVisible: false,
      },
    });
    chartRef.current = chart;

    const resizeObserver = new ResizeObserver(([entry]) => {
      chart.applyOptions({ width: entry.contentRect.width });
    });
    resizeObserver.observe(containerRef.current);

    return () => {
      resizeObserver.disconnect();
      chart.remove();
      chartRef.current = null;
    };
  }, []);

  useEffect(() => {
    const chart = chartRef.current;
    if (!chart) {
      return;
    }
    const candleSeries = chart.addCandlestickSeries({
      upColor: "#16835f",
      downColor: "#c2413a",
      borderVisible: false,
      wickUpColor: "#16835f",
      wickDownColor: "#c2413a",
    });
    const volumeSeries = chart.addHistogramSeries({
      color: "#9aa6b2",
      priceFormat: { type: "volume" },
      priceScaleId: "",
    });
    volumeSeries.priceScale().applyOptions({
      scaleMargins: {
        top: 0.82,
        bottom: 0,
      },
    });
    candleSeries.setData(
      bars.map(
        (bar): CandlestickData => ({
          time: toTimestamp(bar.trade_date),
          open: Number(bar.open),
          high: Number(bar.high),
          low: Number(bar.low),
          close: Number(bar.close),
        }),
      ),
    );
    volumeSeries.setData(
      bars.map(
        (bar): HistogramData => ({
          time: toTimestamp(bar.trade_date),
          value: Number(bar.volume),
          color: Number(bar.close) >= Number(bar.open) ? "#9fcbb9" : "#e4aaa4",
        }),
      ),
    );
    chart.timeScale().fitContent();

    return () => {
      chart.removeSeries(candleSeries);
      chart.removeSeries(volumeSeries);
    };
  }, [bars]);

  return (
    <div
      ref={containerRef}
      className="chart"
      aria-label="Daily candlestick chart"
    />
  );
}

function toTimestamp(value: string): UTCTimestamp {
  return (Date.parse(`${value}T00:00:00Z`) / 1000) as UTCTimestamp;
}
