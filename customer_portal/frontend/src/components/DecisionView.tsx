import { useEffect } from "react";
import { useStore } from "../store";

export function DecisionView() {
  const decision = useStore((s) => s.decision);
  const contestUrl = useStore((s) => s.contestUrl);
  const requestContest = useStore((s) => s.requestContest);
  const busy = useStore((s) => s.busy);
  const reset = useStore((s) => s.reset);

  useEffect(() => {
    if (decision?.verdict === "denied" && !contestUrl) {
      requestContest();
    }
  }, [decision?.verdict]);

  if (!decision) return null;

  const approved = decision.verdict === "approved";
  return (
    <section className="mx-auto max-w-2xl px-6 py-16">
      <div className="label mb-3">Step 3 of 3 · Decision</div>

      <div className={`card overflow-hidden mb-8 ${approved ? "border-good/40" : "border-bad/40"}`}>
        <div className={`px-6 py-6 ${approved ? "bg-good/5" : "bg-bad/5"}`}>
          <div className="flex items-center gap-3 mb-2">
            <span className={`pill ${approved ? "pill-approved" : "pill-denied"}`}>
              {approved ? "Approved" : "Declined"}
            </span>
            <span className="label">Probability of default: {(decision.prob_bad * 100).toFixed(1)}%</span>
          </div>
          <h1 className="display text-4xl">
            {approved
              ? "You're approved."
              : "We're unable to approve this application today."}
          </h1>
          <p className="mt-3 text-ink-muted text-base max-w-lg">
            {approved
              ? "Funds will be disbursed to your registered account within two business days."
              : "The model weighed several factors and landed below our underwriting threshold. You can challenge this outcome."}
          </p>
        </div>

        <div className="px-6 py-5 border-t hairline">
          <div className="label mb-3">Top factors in this decision</div>
          <ol className="space-y-2">
            {(decision.top_reasons || []).map((reason: string, i: number) => (
              <li key={i} className="flex items-start gap-3 text-sm">
                <span className="mono text-[11px] text-ink-muted pt-[3px]">{(i + 1).toString().padStart(2, "0")}</span>
                <span>{reason}</span>
              </li>
            ))}
          </ol>
        </div>

        <div className="px-6 py-5 border-t hairline bg-cream-soft/60">
          <details>
            <summary className="cursor-pointer text-[13px] text-ink hover:text-brand">See all feature contributions</summary>
            <table className="mono mt-3 w-full text-[12.5px]">
              <thead className="text-ink-muted">
                <tr>
                  <th className="text-left pb-1">Feature</th>
                  <th className="text-right pb-1">Value</th>
                  <th className="text-right pb-1">SHAP</th>
                </tr>
              </thead>
              <tbody>
                {(decision.shap || []).map((row: any) => (
                  <tr key={row.feature} className="border-t hairline">
                    <td className="py-1 pr-3">{row.display_name || row.feature}</td>
                    <td className="py-1 text-right">{row.value_display ?? String(row.value)}</td>
                    <td className={`py-1 text-right ${row.contribution >= 0 ? "text-good" : "text-bad"}`}>
                      {row.contribution >= 0 ? "+" : ""}{Number(row.contribution).toFixed(3)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </details>
          <div className="mt-3 text-[11px] text-ink-muted mono">Model version: {decision.model_version?.slice(0, 24)}…</div>
        </div>
      </div>

      {!approved && (
        <div className="card p-6 mb-6 bg-accent-soft/30 border-brand/30">
          <div className="flex items-start justify-between gap-4">
            <div>
              <div className="label mb-2">Your right to contest</div>
              <h2 className="display text-xl mb-2">Challenge this decision</h2>
              <p className="text-ink-muted text-sm max-w-md">
                Under DPDP §11 and GDPR Art. 22(3), any fully-automated decline
                may be contested. You'll be handed to our independent recourse
                partner with a signed token — they verify your identity, validate
                any new evidence, and re-run the exact same model.
              </p>
            </div>
            <div>
              {contestUrl ? (
                <a href={contestUrl} className="btn-primary">Open contest portal →</a>
              ) : (
                <button className="btn-primary" disabled={busy} onClick={() => requestContest()}>
                  {busy ? <><span className="spinner" /> Issuing link…</> : "Issue contest link"}
                </button>
              )}
            </div>
          </div>
          {contestUrl && (
            <div className="mt-4 rounded-md border hairline bg-surface px-3 py-2 text-[12px] mono text-ink-muted break-all">
              {contestUrl}
            </div>
          )}
        </div>
      )}

      <div className="flex items-center gap-3">
        <button className="btn-ghost" onClick={() => reset()}>Start a new application</button>
        <a href="/?view=operator" className="btn-ghost">View in operator console</a>
      </div>
    </section>
  );
}
