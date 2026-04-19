import { create } from "zustand";

export type Domain = "loans" | "hiring";
export type View = "applicant" | "operator";

function readDomain(): Domain {
  return new URLSearchParams(window.location.search).get("domain") === "hiring" ? "hiring" : "loans";
}

function readView(): View {
  return new URLSearchParams(window.location.search).get("view") === "operator" ? "operator" : "applicant";
}

function syncUrl(domain: Domain, view: View) {
  const url = new URL(window.location.href);
  url.searchParams.set("domain", domain);
  if (view === "operator") url.searchParams.set("view", "operator");
  else url.searchParams.delete("view");
  window.history.replaceState({}, "", url.toString());
}

interface AppState {
  domain: Domain;
  view: View;
  setDomain: (d: Domain) => void;
  setView: (v: View) => void;
}

export const useApp = create<AppState>((set, get) => {
  // Sync state ← URL on browser back/forward
  if (typeof window !== "undefined") {
    window.addEventListener("popstate", () => {
      set({ domain: readDomain(), view: readView() });
    });
  }
  return {
    domain: typeof window !== "undefined" ? readDomain() : "loans",
    view: typeof window !== "undefined" ? readView() : "applicant",
    setDomain(d) {
      const v = get().view;
      syncUrl(d, v);
      set({ domain: d });
    },
    setView(v) {
      const d = get().domain;
      syncUrl(d, v);
      set({ view: v });
    },
  };
});
