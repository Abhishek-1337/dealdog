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

export interface PricePoint {
  site: string;
  price: number;
  currency: string;
  link: string;
  recorded_at: string;
}

export interface TrackedProduct {
  product_id: number;
  title: string;
  attributes: Record<string, string>;
  best_price: number | null;
  currency: string;
  history: PricePoint[];
}

export interface ProductDetail {
  id: number;
  title: string;
  attributes: Record<string, string>;
  best_price: number | null;
  currency: string;
  history: PricePoint[];
}

export interface TrackResponse {
  product_id: number;
  tracked_product_id: number;
  reused_existing: boolean;
  title: string;
}
