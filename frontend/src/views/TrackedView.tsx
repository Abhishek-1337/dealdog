import { useEffect, useState } from "react";
import { getTracked } from "../api";
import Sparkline from "../components/Sparkline";
import { useToast } from "../components/Toast";
import { navigate } from "../useRoute";
import type { TrackedProduct } from "../types";

function formatPrice(price: number | null, currency: string) {
  if (price == null) return "—";
  return `${currency === "USD" ? "$" : ""}${price.toFixed(2)}`;
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
      <div style={{ margin: "32px 0 24px" }}>
        <h1 style={{ fontSize: 28, letterSpacing: "-0.03em", margin: "0 0 4px" }}>
          Tracked products
        </h1>
        <p style={{ color: "var(--muted)", margin: 0 }}>
          Products you're watching, with price history.
        </p>
      </div>

      {loading && <div style={{ color: "var(--muted)" }}>Loading…</div>}

      {!loading && items.length === 0 && (
        <div className="card" style={{ color: "var(--muted)" }}>
          Nothing tracked yet. Search for a product and hit Track.
        </div>
      )}

      <div style={{ display: "grid", gap: 14 }}>
        {items.map((item) => (
          <div
            key={item.product_id}
            className="card"
            style={{ display: "flex", alignItems: "center", gap: 16, cursor: "pointer" }}
            onClick={() => navigate(`/products/${item.product_id}`)}
          >
            <div style={{ flex: 1, minWidth: 0 }}>
              <div style={{ fontWeight: 600, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                {item.title}
              </div>
              <div style={{ display: "flex", gap: 6, marginTop: 6, flexWrap: "wrap" }}>
                {Object.entries(item.attributes).map(([k, v]) => (
                  <span key={k} className="chip">
                    <span style={{ color: "var(--muted)", marginRight: 4 }}>{k}</span>
                    {v}
                  </span>
                ))}
              </div>
            </div>
            <Sparkline data={item.history.map((h) => h.price)} />
            <div style={{ textAlign: "right" }}>
              <div style={{ fontSize: 12, color: "var(--muted)" }}>best</div>
              <div style={{ fontWeight: 700 }}>{formatPrice(item.best_price, item.currency)}</div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
