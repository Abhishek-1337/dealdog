export interface Listing {
  site: string;
  title: string;
  price: number;
  currency: string;
  link: string;
  best: boolean;
}

export type MatchStatus = "matched" | "needs_confirmation" | "new";

export interface Group {
  attributes: Record<string, string>;
  canonical_title: string;
  match_status: MatchStatus;
  existing_product_id: number | null;
  candidate_product_id: number | null;
  similarity: number | null;
  confidence: number;
  listings: Listing[];
}

export interface SearchResponse {
  query: string;
  groups: Group[];
}

/** One append-only observation. `price` is null when that scrape failed. */
export interface PricePoint {
  site: string;
  price: number | null;
  currency: string;
  link: string;
  recorded_at: string;
  scrape_success: boolean;
}

export interface PriceDrop {
  site: string;
  current_price: number;
  baseline_average: number;
  percent: number;
  absolute: number;
  recorded_at: string;
}

export interface SiteSeries {
  site: string;
  points: PricePoint[];
  latest_price: number | null;
  latest_at: string | null;
  baseline_average: number | null;
  drop: PriceDrop | null;
}

export interface PriceHistory {
  product_id: number;
  currency: string;
  sites: SiteSeries[];
  /** Cheapest site right now — min over each site's latest successful price. */
  best_price: number | null;
  best_site: string | null;
  /** The floor across every site and every point in time. */
  lowest_price: number | null;
  lowest_site: string | null;
  lowest_at: string | null;
  drops: PriceDrop[];
  records: PricePoint[];
}

export interface TrackedProduct {
  product_id: number;
  title: string;
  attributes: Record<string, string>;
  price_history: PriceHistory;
}

export interface ProductDetail {
  id: number;
  title: string;
  attributes: Record<string, string>;
  price_history: PriceHistory;
}

export interface TrackResponse {
  product_id: number;
  tracked_product_id: number;
  reused_existing: boolean;
  title: string;
}
