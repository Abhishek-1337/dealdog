import { navigate } from "../useRoute";

export default function Header() {
  return (
    <header
      style={{
        background: "var(--surface)",
        borderBottom: "1px solid var(--border)",
        padding: "14px 20px",
        display: "flex",
        alignItems: "center",
        gap: 24,
        position: "sticky",
        top: 0,
        zIndex: 10,
      }}
    >
      <a
        href="#/"
        style={{ fontWeight: 800, fontSize: 18, letterSpacing: "-0.02em" }}
      >
        DealDog
      </a>
      <nav style={{ display: "flex", gap: 16, fontSize: 14 }}>
        <a href="#/" onClick={() => navigate("/")} style={{ color: "var(--muted)" }}>
          Search
        </a>
        <a href="#/tracked" onClick={() => navigate("/tracked")} style={{ color: "var(--muted)" }}>
          Tracked
        </a>
      </nav>
    </header>
  );
}
