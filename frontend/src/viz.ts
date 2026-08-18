import type { PriceHistory, SiteSeries } from "./types";

/**
 * Categorical series colors, in fixed slot order.
 *
 * Validated against the app's white chart surface: lightness band, chroma floor,
 * adjacent-pair CVD separation and normal-vision separation all pass. Three of
 * the hues sit below 3:1 contrast on white, so the chart must always ship a
 * labelled legend (and, on the detail view, the price table) — identity is never
 * carried by color alone.
 *
 * Never cycle or generate a 9th hue. Past eight sites, fold the tail into
 * "Other".
 */
const SERIES_COLORS = [
  "#2a78d6", // blue
  "#eb6834", // orange
  "#1baf7a", // aqua
  "#eda100", // yellow
  "#e87ba4", // magenta
  "#008300", // green
  "#4a3aa7", // violet
  "#e34948", // red
] as const;

export const CHART_INK = {
  grid: "#e1e0d9",
  axis: "#c3c2b7",
  muted: "#898781",
  surface: "#ffffff",
};

/**
 * Retailers we know about, pinned to a slot each.
 *
 * Color follows the retailer, not its position in the current result set — so
 * hiding a site or reordering the list never repaints the others. Amazon stays
 * blue everywhere in the app.
 */
const PINNED_SITES = ["amazon", "bestbuy", "walmart", "newegg", "target", "costco"];

function stableIndex(site: string, slots: number): number {
  let hash = 0;
  for (let i = 0; i < site.length; i += 1) {
    hash = (hash * 31 + site.charCodeAt(i)) % 100000;
  }
  return hash % slots;
}

export function siteColor(site: string): string {
  const key = site.toLowerCase();
  const pinned = PINNED_SITES.indexOf(key);
  if (pinned !== -1) return SERIES_COLORS[pinned];
  // Unknown retailers take a slot past the pinned ones, chosen from the name so
  // it stays the same across renders and sessions.
  const tail = SERIES_COLORS.slice(PINNED_SITES.length);
  return tail[stableIndex(key, tail.length)];
}

export interface ChartRow {
  t: number;
  [site: string]: number | undefined;
}

/**
 * Flatten per-site series into rows the chart can plot on a shared time axis.
 *
 * Sites are scraped at their own moments, so most rows carry a single site's
 * price and the lines are drawn through the gaps (`connectNulls`) — a missing
 * observation is missing knowledge, not a price change. Failed scrapes have no
 * price and so contribute no point at all.
 */
export function toChartRows(sites: SiteSeries[]): ChartRow[] {
  const rows = new Map<number, ChartRow>();
  for (const series of sites) {
    for (const point of series.points) {
      if (!point.scrape_success || point.price === null) continue;
      const t = new Date(point.recorded_at).getTime();
      const row = rows.get(t) ?? { t };
      row[series.site] = point.price;
      rows.set(t, row);
    }
  }
  return [...rows.values()].sort((a, b) => a.t - b.t);
}

/** Sites that actually have a plottable point, in fixed name order. */
export function plottableSites(sites: SiteSeries[]): SiteSeries[] {
  return sites.filter((s) => s.points.some((p) => p.scrape_success && p.price !== null));
}

/** A padded y-domain — price lines don't need a zero baseline, but do need air. */
export function priceDomain(rows: ChartRow[], sites: SiteSeries[]): [number, number] {
  const values: number[] = [];
  for (const row of rows) {
    for (const series of sites) {
      const v = row[series.site];
      if (typeof v === "number") values.push(v);
    }
  }
  if (values.length === 0) return [0, 1];
  const min = Math.min(...values);
  const max = Math.max(...values);
  const pad = (max - min) * 0.15 || Math.max(max * 0.05, 1);
  return [Math.max(0, min - pad), max + pad];
}

export function totalObservations(history: PriceHistory): number {
  return history.records.length;
}
