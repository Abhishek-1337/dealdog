import { useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import { searchProducts, trackProduct } from "../api";
import { useToast } from "../components/Toast";
import { brandColor, formatPrice, shade } from "../lib";
import { siteColor } from "../viz";
import { navigate } from "../useRoute";
import type { Group, MatchStatus, SearchResponse } from "../types";

const BADGES: Record<MatchStatus, { label: string; className: string }> = {
  matched: { label: "Saved", className: "saved" },
  needs_confirmation: { label: "Possible match", className: "pending" },
  new: { label: "New", className: "new" },
};

function coverLabel(group: Group): string {
  return (
    group.attributes.model || group.attributes.chip || group.canonical_title || "Product"
  );
}

function bestListing(group: Group) {
  return group.listings.find((l) => l.best) ?? group.listings[0];
}

function PinCard({ group, onSaved }: { group: Group; onSaved: (msg: string) => void }) {
  const [busy, setBusy] = useState(false);
  const [resolve, setResolve] = useState<"yes" | "no" | null>(null);

  const status = BADGES[group.match_status];
  const best = bestListing(group);
  const brand = group.attributes.brand ?? "";
  const color = brandColor(brand);
  const needsConfirm = group.match_status === "needs_confirmation";
  const saveDisabled = busy || (needsConfirm && resolve === null);

  const doSave = async () => {
    let productId: number | null = null;
    if (group.match_status === "matched") productId = group.existing_product_id;
    else if (needsConfirm) productId = resolve === "yes" ? group.candidate_product_id : null;

    setBusy(true);
    try {
      const result = await trackProduct({
        attributes: group.attributes,
        listings: group.listings.map((l) => ({
          site: l.site,
          title: l.title,
          price: l.price,
          currency: l.currency,
          link: l.link,
        })),
        product_id: productId,
      });
      onSaved(result.reused_existing ? "Saved to an existing product" : "Saved");
      navigate(`/track/${result.product_id}`);
    } catch (e) {
      onSaved(`Save failed: ${(e as Error).message}`);
    } finally {
      setBusy(false);
    }
  };

  return (
    <article className="pin">
      <div
        className="pin-cover"
        style={{ background: `linear-gradient(160deg, ${color} 0%, ${shade(color, -0.35)} 100%)` }}
      >
        {brand && <span className="pin-watermark">{brand}</span>}
        <span className={`pin-badge ${status.className}`}>{status.label}</span>
        <div className="pin-cover-text">
          <span className="pin-cover-label">{coverLabel(group)}</span>
          <span className="pin-cover-price">{formatPrice(best?.price, best?.currency)}</span>
        </div>
      </div>

      <div className="pin-body">
        {Object.keys(group.attributes).length > 0 && (
          <div className="pin-section">
            <span className="section-label">Specs</span>
            <div className="pin-chips">
              {Object.entries(group.attributes).map(([k, v]) => (
                <span key={k} className="chip">
                  <span>{k}</span>
                  {v}
                </span>
              ))}
            </div>
          </div>
        )}

        <div className="pin-section pin-section-grow">
          <span className="section-label">Available at</span>
          <div className="pin-listings">
            {group.listings.map((l) => (
              <div key={`${l.site}-${l.link}`} className={`listing${l.best ? " best" : ""}`}>
                <a
                  className="listing-site"
                  href={l.link}
                  target="_blank"
                  rel="noreferrer"
                  title={`Open on ${l.site}`}
                >
                  <span className="site-dot" style={{ background: siteColor(l.site) }} />
                  {l.site}
                </a>
                <span className="listing-title" title={l.title}>
                  {l.title}
                </span>
                <span className="listing-price">{formatPrice(l.price, l.currency)}</span>
                {l.best && <span className="best-tag">Best</span>}
              </div>
            ))}
          </div>
        </div>

        {needsConfirm && (
          <div className="confirm">
            <span>
              Looks like a saved product ({(group.similarity ?? 0).toFixed(2)} similar). Same
              item?
            </span>
            <div className="confirm-row">
              <button
                className="confirm-btn confirm-yes"
                onClick={() => setResolve("yes")}
                disabled={busy}
              >
                Yes
              </button>
              <button
                className="confirm-btn confirm-no"
                onClick={() => setResolve("no")}
                disabled={busy}
              >
                No
              </button>
            </div>
          </div>
        )}

        <button className="save-btn" onClick={doSave} disabled={saveDisabled}>
          {busy ? <span className="spinner" /> : "Save"}
        </button>
      </div>
    </article>
  );
}

function columnCount(width: number): number {
  return Math.max(1, Math.min(3, Math.floor(width / 360)));
}

function roundRobin(n: number, cols: number): number[][] {
  const buckets: number[][] = Array.from({ length: cols }, () => []);
  for (let i = 0; i < n; i++) buckets[i % cols].push(i);
  return buckets;
}

function Masonry({
  items,
  render,
}: {
  items: Group[];
  render: (g: Group, i: number) => ReactNode;
}) {
  const ref = useRef<HTMLDivElement>(null);
  const initialCols = columnCount(
    typeof window !== "undefined" ? Math.min(window.innerWidth, 1280) - 40 : 1200,
  );  const [cols, setCols] = useState(initialCols);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const ro = new ResizeObserver(() => {
      const next = columnCount(el.clientWidth);
      setCols((prev) => (prev === next ? prev : next));
    });
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  const columns = useMemo(() => roundRobin(items.length, cols), [items.length, cols]);

  return (
    <div ref={ref} className="masonry">
      {columns.map((bucket, i) => (
        <div key={i} className="masonry-col">
          {bucket.map((idx) => render(items[idx], idx))}
        </div>
      ))}
    </div>
  );
}

export default function SearchView() {
  const [query, setQuery] = useState("");
  const [result, setResult] = useState<SearchResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const toast = useToast();

  const runSearch = async (q: string) => {
    if (!q.trim()) return;
    setLoading(true);
    setResult(null);
    try {
      setResult(await searchProducts(q.trim()));
    } catch (e) {
      toast((e as Error).message, "error");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="container">
      <div className="page-head">
        <h1>Find the best price</h1>
        <p>Search across retailers — grouped and matched for you.</p>
      </div>

      <form
        className="search-form"
        onSubmit={(e) => {
          e.preventDefault();
          runSearch(query);
        }}
      >
        <input
          className="search-input"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder='Try "macbook m3" or "iphone 15"'
        />
        <button type="submit" className="search-btn">
          Search
        </button>
      </form>

      {loading && (
        <div className="loading-line">
          <span className="spinner" />
          Matching products…
        </div>
      )}

      {result && !loading && (
        result.groups.length === 0 ? (
          <div className="empty">No results for “{result.query}”. Try another search.</div>
        ) : (
          <Masonry
            items={result.groups}
            render={(g, i) => <PinCard key={i} group={g} onSaved={toast} />}
          />
        )
      )}
    </div>
  );
}
