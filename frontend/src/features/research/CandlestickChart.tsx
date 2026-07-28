import type { MarketBar } from "../../infrastructure/api/research";

type Props = {
  bars: MarketBar[];
};

const chartWidth = 920;
const chartHeight = 500;
const volumeHeight = 86;
const padding = {
  top: 26,
  right: 52,
  bottom: 34,
  left: 18,
};

export function CandlestickChart({ bars }: Props) {
  const prices = bars.flatMap((bar) => [Number(bar.high), Number(bar.low)]);
  const volumes = bars.map((bar) => Number(bar.volume));
  const maxPrice = Math.max(...prices);
  const minPrice = Math.min(...prices);
  const maxVolume = Math.max(...volumes);
  const plotTop = padding.top;
  const plotBottom = chartHeight - padding.bottom - volumeHeight;
  const plotHeight = plotBottom - plotTop;
  const plotWidth = chartWidth - padding.left - padding.right;
  const step = plotWidth / bars.length;
  const candleWidth = Math.max(12, step * 0.54);
  const volumeTop = plotBottom + 24;

  const yForPrice = (price: number) =>
    plotTop + ((maxPrice - price) / (maxPrice - minPrice)) * plotHeight;

  const yForVolume = (volume: number) =>
    volumeTop + (1 - volume / maxVolume) * volumeHeight;

  return (
    <div className="chart" aria-label="日K线图">
      <svg
        role="img"
        viewBox={`0 0 ${chartWidth} ${chartHeight}`}
        preserveAspectRatio="none"
      >
        <title>日K线图</title>
        {[0, 1, 2, 3].map((line) => {
          const y = plotTop + (plotHeight / 3) * line;
          return <line className="chart-grid" key={line} x1="0" x2="920" y1={y} y2={y} />;
        })}
        {[minPrice, (minPrice + maxPrice) / 2, maxPrice].map((price) => (
          <text
            className="chart-label"
            key={price}
            x={chartWidth - 6}
            y={yForPrice(price)}
          >
            {price.toFixed(2)}
          </text>
        ))}
        {bars.map((bar, index) => {
          const open = Number(bar.open);
          const close = Number(bar.close);
          const high = Number(bar.high);
          const low = Number(bar.low);
          const volume = Number(bar.volume);
          const x = padding.left + step * index + step / 2;
          const rising = close >= open;
          const top = yForPrice(Math.max(open, close));
          const bottom = yForPrice(Math.min(open, close));
          const colorClass = rising ? "candle-rise" : "candle-fall";
          const bodyHeight = Math.max(3, bottom - top);

          return (
            <g key={bar.trade_date}>
              <line
                className={colorClass}
                x1={x}
                x2={x}
                y1={yForPrice(high)}
                y2={yForPrice(low)}
              />
              <rect
                className={colorClass}
                x={x - candleWidth / 2}
                y={top}
                width={candleWidth}
                height={bodyHeight}
                rx="2"
              />
              <rect
                className={rising ? "volume-rise" : "volume-fall"}
                x={x - candleWidth / 2}
                y={yForVolume(volume)}
                width={candleWidth}
                height={volumeTop + volumeHeight - yForVolume(volume)}
                rx="2"
              />
            </g>
          );
        })}
        {bars
          .filter((_, index) => index === 0 || index === bars.length - 1)
          .map((bar, index) => (
            <text
              className="chart-label date-label"
              key={bar.trade_date}
              x={index === 0 ? padding.left : chartWidth - padding.right}
              y={chartHeight - 8}
            >
              {bar.trade_date.slice(5)}
            </text>
          ))}
      </svg>
    </div>
  );
}
