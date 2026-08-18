import { useMemo } from "react";
import {
  CartesianGrid,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { formatPrice } from "../lib";
import type { PriceHistory } from "../types";
import { CHART_INK, plottableSites, priceDomain, siteColor, toChartRows } from "../viz";

const TICK = { fill: CHART_INK.muted, fontSize: 11 };

function ChartTooltip({
  active,
  payload,
  label,
  currency,
}: {
  active?: boolean;
  payload?: { name?: string; value?: number; color?: string }[];
  label?: number;
  currency: string;
}) {
  if (!active || !payload?.length) return null;
  return (
    <div className="chart-tooltip">
      <div className="chart-tooltip-time">
        {new Date(label ?? 0).toLocaleString("en-US", {
          month: "short",
          day: "numeric",
          hour: "numeric",
          minute: "2-digit",
        })}
      </div>
      {payload.map((entry) => (
        <div key={entry.name} className="chart-tooltip-row">
          <span className="site-dot" style={{ background: entry.color }} />
          <span className="chart-tooltip-site">{entry.name}</span>
          <span className="chart-tooltip-price">{formatPrice(entry.value, currency)}</span>
        </div>
      ))}
    </div>
  );
}

export default function PriceChart({
  history,
  height = 260,
  compact = false,
}: {
  history: PriceHistory;
  height?: number;
  /** Card-sized variant: no axes or reference line, just the shape of the trend. */
  compact?: boolean;
}) {
  const sites = useMemo(() => plottableSites(history.sites), [history.sites]);
  const rows = useMemo(() => toChartRows(sites), [sites]);
  const domain = useMemo(() => priceDomain(rows, sites), [rows, sites]);

  if (rows.length === 0) {
    return <div className="chart-empty">No prices recorded yet.</div>;
  }

  // A single observation has no trend to draw — say the number instead of
  // plotting a lone dot on an empty grid.
  if (rows.length === 1) {
    return (
      <div className="chart-empty">
        One price recorded so far — refresh to start a trend.
      </div>
    );
  }

  return (
    <ResponsiveContainer width="100%" height={height}>
      <LineChart data={rows} margin={{ top: 8, right: compact ? 4 : 12, bottom: 0, left: compact ? 4 : 0 }}>
        {!compact && <CartesianGrid stroke={CHART_INK.grid} strokeWidth={1} vertical={false} />}
        <XAxis
          dataKey="t"
          type="number"
          scale="time"
          domain={["dataMin", "dataMax"]}
          hide={compact}
          tickLine={false}
          axisLine={{ stroke: CHART_INK.axis }}
          tick={TICK}
          minTickGap={32}
          tickFormatter={(t: number) =>
            new Date(t).toLocaleDateString("en-US", { month: "short", day: "numeric" })
          }
        />
        <YAxis
          domain={domain}
          hide={compact}
          width={56}
          tickLine={false}
          axisLine={false}
          tick={TICK}
          tickFormatter={(v: number) => formatPrice(v, history.currency)}
        />
        {/* The compact card is itself a link to the detail view, where the
            crosshair tooltip and the full price table live — a tooltip here would
            fight the click and be clipped by the card. */}
        {!compact && (
          <Tooltip
            content={<ChartTooltip currency={history.currency} />}
            cursor={{ stroke: CHART_INK.axis, strokeWidth: 1 }}
          />
        )}
        {!compact && history.lowest_price !== null && (
          <ReferenceLine
            y={history.lowest_price}
            stroke={CHART_INK.axis}
            strokeWidth={1}
            label={{
              value: `All-time low ${formatPrice(history.lowest_price, history.currency)}`,
              position: "insideBottomLeft",
              fill: CHART_INK.muted,
              fontSize: 11,
            }}
          />
        )}
        {sites.map((series) => (
          <Line
            key={series.site}
            type="monotone"
            dataKey={series.site}
            name={series.site}
            stroke={siteColor(series.site)}
            strokeWidth={2}
            strokeLinecap="round"
            strokeLinejoin="round"
            // Sites are scraped at their own moments, so each row holds one
            // site's price; joining across the gaps draws one line per site.
            connectNulls
            dot={compact ? false : { r: 4, fill: siteColor(series.site), stroke: CHART_INK.surface, strokeWidth: 2 }}
            activeDot={{ r: 5, fill: siteColor(series.site), stroke: CHART_INK.surface, strokeWidth: 2 }}
            isAnimationActive={false}
          />
        ))}
      </LineChart>
    </ResponsiveContainer>
  );
}
