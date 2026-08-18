import { useState } from "react";
import { searchProducts, trackProduct } from "../api";
import { useToast } from "../components/Toast";
import { navigate } from "../useRoute";
import type { Group, MatchStatus, SearchResponse } from "../types";

const STATUS_LABEL: Record<MatchStatus, { text: string; className: string }> = {
  matched: { text: "Already tracked", className: "badge-matched" },
  needs_confirmation: { text: "Possible match", className: "badge-pending" },
  new: { text: "New", className: "badge-new" },
};

function formatPrice(price: number, currency: string) {
  return `${currency === "USD" ? "$" : ""}${price.toFixed(2)}`;
}

function GroupCard({ group, onTracked }: { group: Group; onTracked: (msg: string) => void }) {
  const [busy, setBusy] = useState(false);
  const [resolve, setResolve] = useState<"yes" | "no" | null>(null);

  const attrs = Object.entries(group.attributes);
  const status = STATUS_LABEL[group.match_status];

  const doTrack = async (productId: number | null, message: string) => {
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
      onTracked(`${message} ${result.reused_existing ? "(linked to existing)" : ""}`);
      navigate(`/products/${result.product_id}`);
    } catch (e) {
      onTracked(`Track failed: ${(e as Error).message}`);
    } finally {
      setBusy(false);
    }
  };

  const resolveProductId = () =>
    resolve === "yes" ? group.candidate_product_id : null;

  return (
    <div className="card" style={{ display: "grid", gap: 12 }}>
      <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
        <span className={`badge ${status.className}`}>{status.text}</span>
        {group.existing_product_id != null && (
          <span style={{ fontSize: 12, color: "var(--muted)" }}>
            product #{group.existing_product_id}
          </span>
        )}
        {attrs.length === 0 && (
          <span style={{ fontSize: 13, color: "var(--muted)" }}>no attributes extracted</span>
        )}
      </div>

      <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
        {attrs.map(([k, v]) => (
          <span key={k} className="chip">
            <span style={{ color: "var(--muted)", marginRight: 4 }}>{k}</span>
            {v}
          </span>
        ))}
      </div>

      {group.match_status === "needs_confirmation" && (
        <div
          style={{
            background: "var(--amber-soft)",
            border: "1px solid #fde68a",
            borderRadius: 8,
            padding: "10px 12px",
            fontSize: 13,
            display: "flex",
            alignItems: "center",
            gap: 10,
            flexWrap: "wrap",
          }}
        >
          <span>
            Similar to an already-tracked product ({(group.similarity ?? 0).toFixed(2)}). Is this the
            same product?
          </span>
          <button className="btn btn-primary" onClick={() => setResolve("yes")} disabled={busy}>
            Yes
          </button>
          <button className="btn" onClick={() => setResolve("no")} disabled={busy}>
            No
          </button>
        </div>
      )}

      <div style={{ display: "grid", gap: 6 }}>
        {group.listings.map((l) => (
          <div
            key={`${l.site}-${l.link}`}
            style={{
              display: "flex",
              alignItems: "center",
              gap: 10,
              padding: "8px 10px",
              borderRadius: 8,
              border: l.best ? "1px solid #bbf7d0" : "1px solid var(--border)",
              background: l.best ? "var(--green-soft)" : "#fafbfc",
            }}
          >
            <span style={{ width: 76, fontWeight: 600, textTransform: "capitalize" }}>
              {l.site}
            </span>
            <span style={{ flex: 1, fontSize: 13, color: "var(--muted)", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
              {l.title}
            </span>
            <span style={{ fontWeight: 700 }}>{formatPrice(l.price, l.currency)}</span>
            {l.best && <span className="badge badge-best">Best price</span>}
            <a href={l.link} target="_blank" rel="noreferrer" className="btn btn-ghost">
              ↗
            </a>
          </div>
        ))}
      </div>

      <div style={{ display: "flex", gap: 8 }}>
        <button
          className="btn btn-primary"
          disabled={busy}
          onClick={() =>
            doTrack(
              group.match_status === "matched" ? group.existing_product_id : resolveProductId(),
              group.match_status === "matched" ? "Tracked" : "Tracked",
            )
          }
        >
          {busy ? <span className="spinner" /> : null}
          Track
        </button>
      </div>
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
      <div style={{ margin: "32px 0 24px" }}>
        <h1 style={{ fontSize: 28, letterSpacing: "-0.03em", margin: "0 0 4px" }}>
          Find the best price
        </h1>
        <p style={{ color: "var(--muted)", margin: 0 }}>
          Search across retailers. Results are grouped and matched automatically.
        </p>
      </div>

      <form
        onSubmit={(e) => {
          e.preventDefault();
          runSearch(query);
        }}
        style={{ display: "flex", gap: 8, marginBottom: 24 }}
      >
        <input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder='Try "macbook m3" or "iphone 15"'
          style={{
            flex: 1,
            padding: "12px 16px",
            borderRadius: 10,
            border: "1px solid var(--border)",
            fontSize: 15,
          }}
        />
        <button type="submit" className="btn btn-primary" style={{ padding: "12px 20px" }}>
          Search
        </button>
      </form>

      {loading && (
        <div style={{ display: "flex", alignItems: "center", gap: 10, color: "var(--muted)" }}>
          <span className="spinner" />
          Extracting attributes & matching…
        </div>
      )}

      {result && !loading && (
        <div style={{ display: "grid", gap: 16 }}>
          {result.groups.length === 0 ? (
            <div className="card" style={{ color: "var(--muted)" }}>
              No results for “{result.query}”.
            </div>
          ) : (
            result.groups.map((g, i) => (
              <GroupCard key={`${g.canonical_title}-${i}`} group={g} onTracked={toast} />
            ))
          )}
        </div>
      )}
    </div>
  );
}
