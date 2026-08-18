import { useEffect, useState, type CSSProperties } from "react";
import { getProduct } from "../api";
import Sparkline from "../components/Sparkline";
import { useToast } from "../components/Toast";
import type { ProductDetail } from "../types";

function formatPrice(price: number | null, currency: string) {
  if (price == null) return "—";
  return `${currency === "USD" ? "$" : ""}${price.toFixed(2)}`;
}

export default function ProductDetailView({ id }: { id: number }) {
  const [product, setProduct] = useState<ProductDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const toast = useToast();

  useEffect(() => {
    getProduct(id)
      .then(setProduct)
      .catch((e) => {
        setError((e as Error).message);
        toast((e as Error).message, "error");
      });
  }, [id, toast]);

  if (error) {
    return <div className="container" style={{ color: "var(--red)" }}>Failed to load: {error}</div>;
  }

  if (!product) {
    return <div className="container" style={{ color: "var(--muted)" }}>Loading…</div>;
  }

  return (
    <div className="container">
      <div style={{ margin: "32px 0 24px" }}>
        <h1 style={{ fontSize: 26, letterSpacing: "-0.03em", margin: "0 0 8px" }}>{product.title}</h1>
        <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
          {Object.entries(product.attributes).map(([k, v]) => (
            <span key={k} className="chip">
              <span style={{ color: "var(--muted)", marginRight: 4 }}>{k}</span>
              {v}
            </span>
          ))}
        </div>
      </div>

      <div className="card" style={{ marginBottom: 16 }}>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
          <div>
            <div style={{ fontSize: 13, color: "var(--muted)" }}>Best price</div>
            <div style={{ fontSize: 28, fontWeight: 800 }}>
              {formatPrice(product.best_price, product.currency)}
            </div>
          </div>
          <Sparkline data={product.history.map((h) => h.price)} width={180} height={48} />
        </div>
      </div>

      <h2 style={{ fontSize: 16, margin: "0 0 10px" }}>Price history</h2>
      <div className="card">
        <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 14 }}>
          <thead>
            <tr>
              <th style={th}>Site</th>
              <th style={th}>Price</th>
              <th style={th}>Recorded</th>
              <th style={th}></th>
            </tr>
          </thead>
          <tbody>
            {product.history.map((h, i) => (
              <tr key={i} style={{ borderTop: "1px solid var(--border)" }}>
                <td style={td}>{h.site}</td>
                <td style={td}>{formatPrice(h.price, h.currency)}</td>
                <td style={{ ...td, color: "var(--muted)" }}>
                  {new Date(h.recorded_at).toLocaleString()}
                </td>
                <td style={td}>
                  {h.link && (
                    <a href={h.link} target="_blank" rel="noreferrer" className="btn btn-ghost">
                      ↗
                    </a>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

const th: CSSProperties = {
  textAlign: "left",
  padding: "8px 12px",
  fontWeight: 600,
  color: "var(--muted)",
  fontSize: 12,
  textTransform: "uppercase",
};

const td: CSSProperties = { padding: "10px 12px" };
