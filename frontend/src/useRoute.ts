import { useEffect, useState } from "react";

export interface Route {
  path: string;
  parts: string[];
}

export function parseHash(): Route {
  const hash = window.location.hash.replace(/^#/, "") || "/";
  const clean = hash.startsWith("/") ? hash : `/${hash}`;
  const parts = clean.split("/").filter(Boolean);
  return { path: `/${parts[0] ?? ""}`, parts };
}

export function navigate(to: string): void {
  window.location.hash = to;
}

export function useRoute(): Route {
  const [route, setRoute] = useState<Route>(parseHash());
  useEffect(() => {
    const onChange = () => setRoute(parseHash());
    window.addEventListener("hashchange", onChange);
    return () => window.removeEventListener("hashchange", onChange);
  }, []);
  return route;
}
