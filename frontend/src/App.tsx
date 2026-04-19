import { useEffect } from "react";
import "./App.css";
import { useStore } from "./store";
import { Header } from "./components/Header";
import { AuditTrail } from "./components/AuditTrail";
import { HandoffView } from "./components/HandoffView";
import { UnderstandView } from "./components/UnderstandView";
import { ContestView } from "./components/ContestView";
import { OutcomeView } from "./components/OutcomeView";
import { ReviewView } from "./components/ReviewView";

export default function App() {
  const stage = useStore((s) => s.stage);
  const error = useStore((s) => s.error);

  useEffect(() => {
    window.scrollTo({ top: 0, behavior: "instant" });
  }, [stage]);

  if (stage === "handoff") {
    return (
      <div className="min-h-screen">
        <Header />
        <HandoffView />
      </div>
    );
  }

  return (
    <div className="min-h-screen">
      <Header />
      <div className="mx-auto grid max-w-shell grid-cols-1 gap-10 px-6 py-10 lg:grid-cols-[1fr_340px] lg:px-8">
        <main id="main" tabIndex={-1} aria-label="Contestation flow">
          {stage === "understand" && <UnderstandView />}
          {stage === "contest" && <ContestView />}
          {stage === "review" && <ReviewView />}
          {stage === "outcome" && <OutcomeView />}
        </main>
        <AuditTrail />
      </div>
      {error && (
        <div role="alert" className="fixed right-4 bottom-6 z-50 rounded-lg border border-accent/40 bg-surface px-4 py-3 text-sm text-accent shadow-lg">
          {error}
        </div>
      )}
    </div>
  );
}
