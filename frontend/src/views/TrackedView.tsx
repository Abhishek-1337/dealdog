import { useEffect, useState } from "react";
import { getTracked } from "../api";
import PriceChart from "../components/PriceChart";
import PriceLegend from "../components/PriceLegend";
import { useToast } from "../components/Toast";
import { brandColor, formatPrice, shade } from "../lib";
import { navigate } from "../useRoute";
import type { TrackedProduct } from "../types";

function coverLabel(item: TrackedProduct): string {
  return item.attributes.model || item.attributes.chip || item.title || "Product";
}

export default function TrackedView() {
  const [items, setItems] = useState<TrackedProduct[]>([]);
  const [loading, setLoading] = useState(true);
  const toast = useToast();

  useEffect(() => {
    getTracked()
      .then(setItems)
      .catch((e) => toast((e as Error).message, "error"))
      .finally(() => setLoading(false));
  }, [toast]);

  return (
    <div className="container">
      <div className="page-head">
        <h1>Saved products</h1>
        <p>Your tracked items, with price history.</p>
      </div>

      {loading && <div className="loading-line"><span className="spinner" />Loading…</div>}

      {!loading && items.length === 0 && (
        <div className="empty">Nothing saved yet. Search for a product and hit Save.</div>
      )}

      <div className="tracked-grid">
        {items.map((item) => {
          const history = item.price_history;
          const biggestDrop = history.drops[0] ?? null;
          return (
            <article
              key={item.product_id}
              className="tracked-card"
              onClick={() => navigate(`/track/${item.product_id}`)}
            >
              <div
                className="pin-cover"
                style={{
                  background: `linear-gradient(160deg, ${brandColor(item.attributes.brand ?? "")} 0%, ${shade(brandColor(item.attributes.brand ?? ""), -0.35)} 100%)`,
                }}
              >
                {item.attributes.brand && (
                  <span className="pin-watermark">{item.attributes.brand}</span>
                )}
                <div className="pin-cover-text">
                  <span className="pin-cover-label">{coverLabel(item)}</span>
                  <span className="pin-cover-price">
                    {formatPrice(history.best_price, history.currency)}
                  </span>
                </div>
              </div>
              <div className="pin-body">
                {Object.keys(item.attributes).length > 0 && (
                  <div className="pin-chips">
                    {Object.entries(item.attributes).map(([k, v]) => (
                      <span key={k} className="chip">
                        <span>{k}</span>
                        {v}
                      </span>
                    ))}
                  </div>
                )}

                {biggestDrop && (
                  <div className="drop-banner">
                    <strong>
                      ↓ {formatPrice(biggestDrop.absolute, history.currency)} on {biggestDrop.site}
                    </strong>
                    <span>
                      {biggestDrop.percent}% under its {formatPrice(biggestDrop.baseline_average, history.currency)} average
                    </span>
                  </div>
                )}

                <div className="card-chart">
                  <PriceChart history={history} height={72} compact />
                </div>
                <PriceLegend history={history} compact />

                <div className="card-stats">
                  <div>
                    <small>Best now</small>
                    {formatPrice(history.best_price, history.currency)}
                    {history.best_site && <em>{history.best_site}</em>}
                  </div>
                  <div>
                    <small>All-time low</small>
                    {formatPrice(history.lowest_price, history.currency)}
                    {history.lowest_site && <em>{history.lowest_site}</em>}
                  </div>
                </div>
              </div>
            </article>
          );
        })}
      </div>
    </div>
  );
}
