import { navigate, useRoute } from "../useRoute";

export default function Header() {
  const route = useRoute();
  const active = route.path === "/" ? "search" : "tracked";

  return (
    <header className="topbar">
      <a href="#/" className="brand" onClick={() => navigate("/")}>
        <span className="brand-dot" />
        DealDog
      </a>
      <nav className="topbar-nav">
        <a
          href="#/"
          className={active === "search" ? "active" : ""}
          onClick={() => navigate("/")}
        >
          Search
        </a>
        <a
          href="#/tracked"
          className={active === "tracked" ? "active" : ""}
          onClick={() => navigate("/tracked")}
        >
          Saved
        </a>
      </nav>
    </header>
  );
}
