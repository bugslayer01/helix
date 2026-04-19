import { useEffect } from "react";
import { useStore } from "../store";
import { ShapBars } from "./ShapBars";

export function OutcomeView() {
  const outcome = useStore((s) => s.outcome);
  const decisionVerdict = useStore((s) => s.decisionVerdict);
  const decisionProbBad = useStore((s) => s.decisionProbBad);
  const reset = useStore((s) => s.reset);
  const verifyAudit = useStore((s) => s.verifyAudit);
  const auditVerified = useStore((s) => s.auditVerified);
  const webhookId = useStore((s) => s.webhookId);

  useEffect(() => { verifyAudit(); }, []);

  if (!outcome) {
    return (
      <section className="mx-auto max-w-xl px-6 py-16">
        <div className="label mb-3">Handed off</div>
        <h1 className="display text-4xl">Your case is queued with a human reviewer.</h1>
        <p className="text-ink-muted mt-4">
          A reviewer will read your case within 72 hours. The model is not re-run on
          this path; the decision will be made by a person.
        </p>
      </section>
    );
  }

  const flipped = outcome.outcome === "flipped";

  return (
    <section className="mx-auto max-w-4xl px-6 py-12">
      <div className="label mb-3">Step 4 of 4 · Outcome</div>

      <div className={`card overflow-hidden mb-8 ${flipped ? "border-good/40" : "border-warn/40"}`}>
        <div className={`px-6 py-6 ${flipped ? "bg-good/5" : "bg-warn/5"}`}>
          <div className="flex items-center gap-3 mb-2">
            <span className={`pill ${flipped ? "pill-approved" : "border-warn/40 bg-warn/10 text-warn"}`}>
              {flipped ? "Flipped" : "Held"}
            </span>
            <span className="label">
              Probability of default: {(decisionProbBad * 100).toFixed(1)}% → {(outcome.new_prob_bad * 100).toFixed(1)}%
            </span>
          </div>
          <h1 className="display text-4xl">
            {flipped
              ? "Your decision has changed."
              : "Your decision did not change."}
          </h1>
          <p className="mt-3 text-ink-muted max-w-xl">
            {flipped
              ? "The model re-ran on your corrected features and moved the outcome. Your lender has been notified."
              : "The model re-ran on your corrected features but the risk signal is still above the underwriting threshold."}
          </p>
        </div>

        <div className="px-6 py-5 border-t hairline">
          <div className="label mb-3">What changed</div>
          <table className="mono w-full text-[12.5px]">
            <thead className="text-ink-muted">
              <tr>
                <th className="text-left pb-2">Feature</th>
                <th className="text-right pb-2">Before</th>
                <th className="text-right pb-2">After</th>
                <th className="text-right pb-2">SHAP Δ</th>
              </tr>
            </thead>
            <tbody>
              {outcome.delta.map((d) => {
                const shapDelta = d.contribution_new - d.contribution_old;
                return (
                  <tr key={d.feature} className="border-t hairline">
                    <td className="py-2 pr-3">{d.display_name}</td>
                    <td className="py-2 text-right">{d.old}</td>
                    <td className="py-2 text-right">{d.new}</td>
                    <td className={`py-2 text-right ${shapDelta >= 0 ? "text-good" : "text-bad"}`}>
                      {shapDelta >= 0 ? "+" : ""}{shapDelta.toFixed(3)}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>

        <div className="px-6 py-5 border-t hairline bg-cream-soft/60 text-[13px] text-ink-muted">
          <div>Previous verdict: <span className="text-ink">{decisionVerdict}</span> · New verdict: <span className="text-ink">{outcome.new_verdict}</span></div>
          {webhookId && <div>Verdict dispatched to lender. Webhook id <span className="mono text-ink">{webhookId}</span>.</div>}
        </div>
      </div>

      <div className="card p-5 mb-8">
        <div className="label mb-3">Feature contributions — after re-evaluation</div>
        <ShapBars shap={outcome.new_shap} />
      </div>

      <div className="card p-5 mb-8">
        <div className="flex items-start justify-between gap-4">
          <div>
            <div className="label mb-1">Tamper-evident audit chain</div>
            <p className="text-[13px] text-ink-muted max-w-lg">
              Every event in your contest — from case_opened to
              webhook_delivered — is SHA-256 chained. Any edit to the log
              breaks the chain. Verify it now.
            </p>
          </div>
          <button className="btn-ghost" onClick={() => verifyAudit()}>Verify chain</button>
        </div>
        {auditVerified && (
          <div className={`mt-4 rounded-md border px-3 py-2 text-sm ${auditVerified.ok ? "border-good/40 bg-good/5 text-good" : "border-bad/40 bg-bad/5 text-bad"}`}>
            {auditVerified.ok
              ? <>Chain valid · {auditVerified.rows} rows · head <span className="mono">{auditVerified.head?.slice(0, 16)}…</span></>
              : <>Chain broken at row {(auditVerified as any).broken_at_row}.</>}
          </div>
        )}
      </div>

      <div className="flex items-center gap-3 border-t hairline pt-6">
        <button className="btn-ghost" onClick={() => { reset(); window.location.search = ""; }}>Start over</button>
      </div>
    </section>
  );
}
