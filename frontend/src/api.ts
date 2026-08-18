import type {
  PriceHistory,
  ProductDetail,
  SearchResponse,
  TrackedProduct,
  TrackResponse,
} from "./types";

const BASE = "/api";

async function handle<T>(resp: Response): Promise<T> {
  if (!resp.ok) {
    const text = await resp.text();
    throw new Error(text || resp.statusText);
  }
  return resp.json() as Promise<T>;
}

export async function searchProducts(query: string): Promise<SearchResponse> {
  const resp = await fetch(`${BASE}/search?q=${encodeURIComponent(query)}`);
  return handle<SearchResponse>(resp);
}

export async function trackProduct(payload: {
  attributes: Record<string, string>;
  listings: { site: string; title: string; price: number; currency: string; link: string }[];
  product_id: number | null;
}): Promise<TrackResponse> {
  const resp = await fetch(`${BASE}/track`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  return handle<TrackResponse>(resp);
}

export async function getTracked(): Promise<TrackedProduct[]> {
  const resp = await fetch(`${BASE}/tracked`);
  return handle<TrackedProduct[]>(resp);
}

export async function getProduct(id: number): Promise<ProductDetail> {
  const resp = await fetch(`${BASE}/products/${id}`);
  return handle<ProductDetail>(resp);
}

export async function getPriceHistory(id: number): Promise<PriceHistory> {
  const resp = await fetch(`${BASE}/products/${id}/history`);
  return handle<PriceHistory>(resp);
}

/** Run a scrape round: appends a new observation per site, never overwrites. */
export async function refreshPrices(id: number): Promise<PriceHistory> {
  const resp = await fetch(`${BASE}/products/${id}/history`, { method: "POST" });
  return handle<PriceHistory>(resp);
}
