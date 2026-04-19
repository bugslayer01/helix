import { useStore } from "./store";
import { Header } from "./components/Header";
import { PickerView } from "./components/PickerView";
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
      ) : stage === "picker" ? (
        <PickerView />
      ) : (
        <DecisionView />
      )}
      <footer className="border-t hairline mt-16 py-6 text-center text-[11px] text-ink-muted">
        LenderCo is a demo customer surface. Decisions come from the real
        XGBoost model. Contestation routes to the independent Recourse partner.
      </footer>
    </div>
  );
}
