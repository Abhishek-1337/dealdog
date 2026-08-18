export function formatPrice(price: number | null | undefined, currency = "USD"): string {
  if (price == null) return "—";
  const value = price.toLocaleString("en-US", { maximumFractionDigits: 2 });
  return currency === "USD" ? `$${value}` : `${value} ${currency}`;
}

const PALETTE = ["#0B3D91", "#5B21B6", "#065F46", "#9A3412", "#831843", "#1F2937"];

export function brandColor(brand: string): string {
  const b = (brand || "").trim().toLowerCase();
  if (b === "apple") return "#1D1D1F";
  if (b === "samsung") return "#0B3D91";
  let h = 0;
  for (let i = 0; i < b.length; i++) h = (h * 31 + b.charCodeAt(i)) >>> 0;
  return PALETTE[h % PALETTE.length];
}

export function shade(hex: string, amount: number): string {
  const m = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
  if (!m) return hex;
  const f = (c: string) => {
    const n = Math.max(0, Math.min(255, Math.round(parseInt(c, 16) * (1 + amount))));
    return n.toString(16).padStart(2, "0");
  };
  return `#${f(m[1])}${f(m[2])}${f(m[3])}`;
}

export function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString("en-US", { month: "short", day: "numeric" });
}

// Site identity colors live in viz.ts, so a retailer wears the same hue in the
// search list and in the price chart — and the palette is validated in one place.
