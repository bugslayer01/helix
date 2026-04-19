import { useEffect } from "react";
import { useStore } from "../store";

export function DecisionView() {
  const detail = useStore((s) => s.detail);
  const decision = useStore((s) => s.decision);
  const contestUrl = useStore((s) => s.contestUrl);
  const mailStatus = useStore((s) => s.mailStatus);
  const requestContest = useStore((s) => s.requestContest);
  const busy = useStore((s) => s.busy);
  const back = useStore((s) => s.back);

  useEffect(() => {
    if (decision?.verdict === "denied" && !contestUrl) {
      requestContest();
    }
  }, [decision?.verdict]);

  if (!detail || !decision) return null;
  const applicant = detail.applicant || {};
  const application = detail.application || {};
  const features = detail.scored_features?.feature_vector || {};
  const approved = decision.verdict === "approved";

  return (
    <section className="mx-auto max-w-3xl px-6 py-12">
      <button className="text-[13px] text-ink-muted hover:text-brand mb-6" onClick={back}>← All cases</button>

      <div className="label mb-3">Applicant decision</div>

      <div className="mb-6">
        <div className="display text-3xl">{applicant.full_name}</div>
        <div className="mono text-[12px] text-ink-muted mt-1">
          {application.id} · DOB {applicant.dob} · ₹{Number(application.amount).toLocaleString("en-IN")} · {application.purpose}
        </div>
      </div>

      <div className={`card overflow-hidden mb-8 ${approved ? "border-good/40" : "border-bad/40"}`}>
        <div className={`px-6 py-6 ${approved ? "bg-good/5" : "bg-bad/5"}`}>
          <div className="flex items-center gap-3 mb-2">
            <span className={`pill ${approved ? "pill-approved" : "pill-denied"}`}>{decision.verdict}</span>
            <span className="label">Probability of default: {(decision.prob_bad * 100).toFixed(1)}%</span>
          </div>
          <h1 className="display text-4xl">
            {approved
              ? "Approved by the underwriting model."
              : "Application declined by the underwriting model."}
          </h1>
          <p className="mt-3 text-ink-muted text-base max-w-lg">
            {approved
              ? "Funds will disburse within two business days. No further action needed."
              : "The model weighed several factors and landed below the underwriting threshold. The applicant has a statutory right to contest this outcome."}
          </p>
        </div>

        <div className="px-6 py-5 border-t hairline">
          <div className="label mb-3">Top factors</div>
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
            <summary className="cursor-pointer text-[13px] text-ink hover:text-brand">All feature contributions</summary>
            <table className="mono mt-3 w-full text-[12px]">
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
          <div className="mt-3 mono text-[11px] text-ink-muted">
            Model version: {String(detail.scored_features?.model_version || "").slice(0, 28)}…
          </div>
        </div>
      </div>

      {Object.keys(features).length > 0 && (
        <details className="card p-5 mb-6">
          <summary className="cursor-pointer label">Feature vector the model scored on</summary>
          <pre className="mono text-[11.5px] mt-3 whitespace-pre-wrap break-all">
            {JSON.stringify(features, null, 2)}
          </pre>
        </details>
      )}

      {!approved && (
        <div className="card p-6 mb-6 bg-accent-soft/30 border-brand/30">
          <div className="flex items-start justify-between gap-4">
            <div>
              <div className="label mb-2">Statutory right to contest</div>
              <h2 className="display text-xl mb-2">Hand off to Recourse</h2>
              <p className="text-ink-muted text-sm max-w-md">
                Under DPDP Section 11 and GDPR Art. 22(3), this denial may be contested.
                Issuing a link mints a signed JWT and opens the independent
                contestation portal where the applicant validates new evidence
                against the same underwriting model.
              </p>
            </div>
            <div>
              {contestUrl ? (
                <a href={contestUrl} className="btn-primary" target="_blank" rel="noopener">Open contest portal →</a>
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
          {mailStatus && (
            <div className={`mt-3 rounded-md border px-3 py-2 text-[12.5px] ${mailStatus.ok ? "border-good/40 bg-good/5 text-good" : "border-warn/40 bg-warn/5 text-warn"}`}>
              {mailStatus.ok ? (
                <>
                  ✉ Email delivered to applicant.{" "}
                  {mailStatus.mailinator_inbox && (
                    <a href={mailStatus.mailinator_inbox} target="_blank" rel="noopener" className="underline font-medium">View mailinator inbox →</a>
                  )}
                </>
              ) : mailStatus.skipped ? (
                <>✉ Email skipped (recipient is not a mailinator address).</>
              ) : (
                <>✉ Email send failed: {mailStatus.error || "unknown"}. Link still valid above.</>
              )}
            </div>
          )}
        </div>
      )}

      <div className="flex items-center gap-3">
        <button className="btn-ghost" onClick={back}>← Back to case list</button>
        <a href="/?view=operator" className="btn-ghost">View in operator console</a>
      </div>
    </section>
  );
}
