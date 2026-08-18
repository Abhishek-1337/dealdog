import { useCallback, useEffect, useState } from "react";
import { getProduct, refreshPrices } from "../api";
import PriceChart from "../components/PriceChart";
import PriceLegend from "../components/PriceLegend";
import { useToast } from "../components/Toast";
import { formatPrice } from "../lib";
import { navigate } from "../useRoute";
import type { PriceHistory, ProductDetail } from "../types";
import { siteColor } from "../viz";

function DropCallout({ history }: { history: PriceHistory }) {
  if (history.drops.length === 0) return null;
  return (
    <div className="drop-callout">
      <span className="drop-callout-icon" aria-hidden="true">↓</span>
      <div>
        <strong>
          Price drop{history.drops.length > 1 ? "s" : ""} detected
        </strong>
        <ul>
          {history.drops.map((drop) => (
            <li key={drop.site}>
              <span style={{ textTransform: "capitalize", fontWeight: 600 }}>{drop.site}</span> is at{" "}
              {formatPrice(drop.current_price, history.currency)} — {drop.percent}% (
              {formatPrice(drop.absolute, history.currency)}) below its recent{" "}
              {formatPrice(drop.baseline_average, history.currency)} average.
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}

export default function ProductDetailView({ id }: { id: number }) {
  const [product, setProduct] = useState<ProductDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [refreshing, setRefreshing] = useState(false);
  const toast = useToast();

  useEffect(() => {
    getProduct(id)
      .then(setProduct)
      .catch((e) => {
        setError((e as Error).message);
        toast((e as Error).message, "error");
      });
  }, [id, toast]);

  const onRefresh = useCallback(async () => {
    setRefreshing(true);
    try {
      const history = await refreshPrices(id);
      setProduct((prev) => (prev ? { ...prev, price_history: history } : prev));
      const drop = history.drops[0];
      toast(drop ? `Prices updated — ${drop.site} is down ${drop.percent}%` : "Prices updated");
    } catch (e) {
      toast((e as Error).message, "error");
    } finally {
      setRefreshing(false);
    }
  }, [id, toast]);

  if (error) {
    return <div className="container" style={{ color: "var(--red)", paddingTop: 24 }}>Failed to load: {error}</div>;
  }

  if (!product) {
    return <div className="container loading-line"><span className="spinner" />Loading…</div>;
  }

  const history = product.price_history;

  return (
    <div className="container">
      <button className="back-link" onClick={() => navigate("/tracked")}>
        ← Saved
      </button>
      <div className="detail-head">
        <div style={{ minWidth: 0 }}>
          <span className="section-label">Tracked product</span>
          <h1>{product.title}</h1>
          <div className="pin-chips">
            {Object.entries(product.attributes).map(([k, v]) => (
              <span key={k} className="chip">
                <span>{k}</span>
                {v}
              </span>
            ))}
          </div>
        </div>
        <div className="detail-price">
          <small>Best price now</small>
          {formatPrice(history.best_price, history.currency)}
          {history.best_site && <em>at {history.best_site}</em>}
        </div>
      </div>

      <DropCallout history={history} />

      <div className="stat-row">
        <div className="stat-tile">
          <small>Best price now</small>
          <span>{formatPrice(history.best_price, history.currency)}</span>
          <em>cheapest site's latest price</em>
        </div>
        <div className="stat-tile">
          <small>All-time low</small>
          <span>{formatPrice(history.lowest_price, history.currency)}</span>
          <em>
            {history.lowest_site ? `${history.lowest_site}` : "—"}
            {history.lowest_at && `, ${new Date(history.lowest_at).toLocaleDateString()}`}
          </em>
        </div>
        <div className="stat-tile">
          <small>Sites tracked</small>
          <span>{history.sites.length}</span>
          <em>{history.records.length} observations</em>
        </div>
      </div>

      <section className="chart-card">
        <header className="chart-card-head">
          <div>
            <h2>Price trend by store</h2>
            <p>One line per retailer. Every scrape is appended, never overwritten.</p>
          </div>
          <button className="ghost-btn" onClick={onRefresh} disabled={refreshing}>
            {refreshing ? "Checking…" : "Check prices"}
          </button>
        </header>
        <PriceLegend history={history} />
        <PriceChart history={history} height={280} />
      </section>

      <h2 style={{ fontSize: 18, margin: "0 0 12px", fontWeight: 700 }}>Price history</h2>
      <table className="history-table">
        <thead>
          <tr>
            <th>Store</th>
            <th>Price</th>
            <th>Recorded</th>
          </tr>
        </thead>
        <tbody>
          {[...history.records].reverse().map((h, i) => (
            <tr key={i} className={h.scrape_success ? undefined : "row-failed"}>
              <td style={{ fontWeight: 600 }}>
                <span className="site-dot" style={{ background: siteColor(h.site) }} />
                <span style={{ textTransform: "capitalize" }}>{h.site}</span>
              </td>
              <td style={{ fontWeight: 700 }}>
                {h.scrape_success ? (
                  formatPrice(h.price, h.currency)
                ) : (
                  <span className="failed-tag">scrape failed</span>
                )}
              </td>
              <td style={{ color: "var(--muted)" }}>
                {new Date(h.recorded_at).toLocaleString()}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
