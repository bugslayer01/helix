import { useStore } from "./store";
import { useHiring } from "./store_hiring";
import { useApp } from "./store_app";
import { Header } from "./components/Header";
import { PickerView } from "./components/PickerView";
import { DecisionView } from "./components/DecisionView";
import { OperatorView } from "./components/OperatorView";
import { PostingsView } from "./components/hiring/PostingsView";
import { NewPostingView } from "./components/hiring/NewPostingView";
import { CandidateUploadView } from "./components/hiring/CandidateUploadView";
import { HiringDecisionView } from "./components/hiring/HiringDecisionView";

export function App() {
  const view = useApp((s) => s.view);
  const domain = useApp((s) => s.domain);
  const stage = useStore((s) => s.stage);
  const hiringStage = useHiring((s) => s.stage);

  return (
    <div className="min-h-screen">
      <Header />
      {/* Cross-fade per (domain,view) tuple to soften the transition. */}
      <div key={`${domain}:${view}`} className="animate-[fadein_180ms_ease-out]">
        {view === "operator" ? <OperatorView /> :
         domain === "hiring" ? (
           hiringStage === "postings" ? <PostingsView /> :
           hiringStage === "newPosting" ? <NewPostingView /> :
           hiringStage === "candidateUpload" ? <CandidateUploadView /> :
           <HiringDecisionView />
         ) : (
           stage === "picker" ? <PickerView /> : <DecisionView />
         )}
      </div>
      <footer className="border-t hairline mt-16 py-6 text-center text-[11px] text-ink-muted">
        LenderCo · {domain === "hiring" ? "Hiring decisions powered by gpt-4o-mini" : "Loan decisions powered by XGBoost + SHAP"}.
      </footer>
      <style>{`
        @keyframes fadein {
          from { opacity: 0; transform: translateY(2px); }
          to   { opacity: 1; transform: translateY(0); }
        }
      `}</style>
    </div>
  );
}
