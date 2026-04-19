import { useStore } from "../store";
import { ShapBars } from "./ShapBars";

export function UnderstandView() {
  const verdict = useStore((s) => s.decisionVerdict);
  const prob = useStore((s) => s.decisionProbBad);
  const shap = useStore((s) => s.shap);
  const topReasons = useStore((s) => s.topReasons);
  const goto = useStore((s) => s.goto);
  const externalRef = useStore((s) => s.externalRef);
  const modelVersion = useStore((s) => s.modelVersion);
  const intakeDocs = useStore((s) => s.intakeDocs);

  return (
    <section className="mx-auto max-w-4xl px-6 py-12">
      <div className="label mb-3">Step 1 of 4 · Understand</div>
      <h1 className="display text-4xl mb-2">Why were you denied?</h1>
      <p className="text-ink-muted text-base mb-10 max-w-2xl">
        Your lender ran an XGBoost credit-risk model that produced a
        probability of default of <span className="mono text-ink">{(prob * 100).toFixed(1)}%</span>.
        Here's how each factor shaped that number. The features with the
        biggest negative bars are your strongest grounds to contest.
      </p>

      <div className="card p-5 mb-8">
        <div className="flex items-center justify-between mb-4">
          <div>
            <div className="label mb-1">Top reasons</div>
            <h2 className="display text-xl">What the model weighted most.</h2>
          </div>
          <span className={`pill ${verdict === "approved" ? "pill-approved" : "pill-denied"}`}>{verdict}</span>
        </div>
        <ol className="space-y-2">
          {topReasons.map((r, i) => (
            <li key={i} className="flex items-start gap-3 text-[15px]">
              <span className="mono text-[11px] text-ink-muted pt-[3px]">{(i + 1).toString().padStart(2, "0")}</span>
              <span>{r}</span>
            </li>
          ))}
        </ol>
      </div>

      <div className="card p-5 mb-8">
        <div className="label mb-3">Feature contributions (SHAP)</div>
        <ShapBars shap={shap} />
      </div>

      <div className="grid grid-cols-2 gap-4 text-[12.5px] text-ink-muted mb-10">
        <div className="card p-4">
          <div className="label mb-1">Lender reference</div>
          <div className="mono text-ink">{externalRef}</div>
        </div>
        <div className="card p-4">
          <div className="label mb-1">Model version</div>
          <div className="mono text-ink break-all">{modelVersion.slice(0, 28)}…</div>
          <div className="text-[11px] mt-1">
            Same version will be re-run by Recourse when you contest. Drift raises HTTP 409.
          </div>
        </div>
      </div>

      {intakeDocs.length > 0 && (
        <div className="card p-4 mb-8">
          <div className="label mb-2">Documents your lender already has on file</div>
          <ul className="flex flex-wrap gap-2">
            {intakeDocs.map((d, i) => (
              <li key={i} className="pill">{d.doc_type.replace(/_/g, " ")}</li>
            ))}
          </ul>
        </div>
      )}

      <div className="flex items-center justify-between border-t hairline pt-6">
        <div className="text-[12px] text-ink-muted">All subsequent evidence passes through a 10-check forensics pipeline.</div>
        <button className="btn-primary" onClick={() => goto("contest")}>Contest with evidence →</button>
      </div>

      <div className="mt-3 text-[12px] text-ink-muted">
        Prefer a human reviewer?{" "}
        <button className="underline decoration-accent/40 hover:text-accent" onClick={() => goto("review")}>Request human review</button>.
      </div>
    </section>
  );
}
