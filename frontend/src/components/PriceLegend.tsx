import { formatPrice } from "../lib";
import type { PriceHistory } from "../types";
import { plottableSites, siteColor } from "../viz";

/**
 * The chart's identity channel. Always rendered alongside a multi-site chart:
 * three of the series hues sit below 3:1 contrast on white, so the reader gets
 * a named row per site rather than having to match colors by eye.
 *
 * It doubles as the direct-label layer — each site's latest price lives here
 * instead of beside the line's endpoint, where five labels would collide.
 */
export default function PriceLegend({
  history,
  compact = false,
}: {
  history: PriceHistory;
  compact?: boolean;
}) {
  const sites = plottableSites(history.sites);
  if (sites.length === 0) return null;

  return (
    <ul className={compact ? "chart-legend chart-legend-compact" : "chart-legend"}>
      {sites.map((series) => (
        <li key={series.site}>
          <span className="site-dot" style={{ background: siteColor(series.site) }} />
          <span className="chart-legend-site">{series.site}</span>
          <span className="chart-legend-price">
            {formatPrice(series.latest_price, history.currency)}
          </span>
          {series.drop && (
            <span className="drop-tag" title={`Down from a ${formatPrice(series.baseline_average, history.currency)} average`}>
              ↓ {series.drop.percent}%
            </span>
          )}
        </li>
      ))}
    </ul>
  );
}
