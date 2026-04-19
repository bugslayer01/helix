import { useStore } from "./store";
import { Header } from "./components/Header";
import { IntroView } from "./components/IntroView";
import { FormView } from "./components/FormView";
import { DocsView } from "./components/DocsView";
import { SubmittingView } from "./components/SubmittingView";
import { DecisionView } from "./components/DecisionView";
import { OperatorView } from "./components/OperatorView";

function currentView(): "applicant" | "operator" {
  const params = new URLSearchParams(window.location.search);
  return params.get("view") === "operator" ? "operator" : "applicant";
}

export function App() {
  const view = currentView();
  const stage = useStore((s) => s.stage);

  return (
    <div className="min-h-screen">
      <Header operatorMode={view === "operator"} />
      {view === "operator" ? (
        <OperatorView />
      ) : stage === "intro" ? (
        <IntroView />
      ) : stage === "form" ? (
        <FormView />
      ) : stage === "docs" ? (
        <DocsView />
      ) : stage === "submitting" ? (
        <SubmittingView />
      ) : (
        <DecisionView />
      )}
      <footer className="border-t hairline mt-16 py-6 text-center text-[11px] text-ink-muted">
        LenderCo is a demo customer surface. All decisions are produced by a
        real XGBoost model; contestation routes to an independent recourse
        partner.
      </footer>
    </div>
  );
}
