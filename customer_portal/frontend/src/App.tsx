import { useStore } from "./store";
import { useHiring } from "./store_hiring";
import { Header } from "./components/Header";
import { PickerView } from "./components/PickerView";
import { DecisionView } from "./components/DecisionView";
import { OperatorView } from "./components/OperatorView";
import { PostingsView } from "./components/hiring/PostingsView";
import { NewPostingView } from "./components/hiring/NewPostingView";
import { CandidateUploadView } from "./components/hiring/CandidateUploadView";
import { HiringDecisionView } from "./components/hiring/HiringDecisionView";

function currentDomain(): "loans" | "hiring" { return new URLSearchParams(window.location.search).get("domain") === "hiring" ? "hiring" : "loans"; }
function currentView(): "applicant" | "operator" { return new URLSearchParams(window.location.search).get("view") === "operator" ? "operator" : "applicant"; }

export function App() {
  const view = currentView();
  const domain = currentDomain();
  const stage = useStore((s) => s.stage);
  const hiringStage = useHiring((s) => s.stage);

  return (
    <div className="min-h-screen">
      <Header operatorMode={view === "operator"} domain={domain} />
      {view === "operator" ? <OperatorView /> :
       domain === "hiring" ? (
         hiringStage === "postings" ? <PostingsView /> :
         hiringStage === "newPosting" ? <NewPostingView /> :
         hiringStage === "candidateUpload" ? <CandidateUploadView /> :
         <HiringDecisionView />
       ) : (
         stage === "picker" ? <PickerView /> : <DecisionView />
       )}
      <footer className="border-t hairline mt-16 py-6 text-center text-[11px] text-ink-muted">
        LenderCo · {domain === "hiring" ? "Hiring decisions powered by gpt-4o-mini" : "Loan decisions powered by XGBoost + SHAP"}.
      </footer>
    </div>
  );
}
