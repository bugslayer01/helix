import { useEffect } from "react";
import { useHiring } from "../../store_hiring";

export function HiringDecisionView() {
  const s = useHiring();
  const decision = s.decision;

  useEffect(() => {
    if (decision?.verdict === "denied" && !s.contestUrl) s.requestContest();
  }, [decision?.verdict]);

  if (!decision) return null;
  const approved = decision.verdict === "approved";

  return (
    <section className="mx-auto max-w-3xl px-6 py-12">
      <button className="text-[13px] text-ink-muted hover:text-brand mb-6" onClick={() => s.reset()}>← All postings</button>
      <div className="label mb-3">{s.selectedPostingTitle}</div>
      <h1 className="display text-3xl mb-1">{s.candidate.full_name}</h1>
      <div className="mono text-[12px] text-ink-muted mb-6">{s.applicationId}</div>

      <div className={`card overflow-hidden mb-8 ${approved ? "border-good/40" : "border-bad/40"}`}>
        <div className={`px-6 py-6 ${approved ? "bg-good/5" : "bg-bad/5"}`}>
          <div className="flex items-center gap-3 mb-2">
            <span className={`pill ${approved ? "pill-approved" : "pill-denied"}`}>{decision.verdict}</span>
            <span className="label">Fit score: {(decision.confidence * 100).toFixed(0)}%</span>
          </div>
          <h2 className="display text-3xl">{approved ? "Move forward — strong fit." : "Not selected — see reasons."}</h2>
        </div>
        <div className="px-6 py-5 border-t hairline">
          <div className="label mb-3">Top factors</div>
          <ol className="space-y-2">
            {(decision.top_reasons || []).map((r: string, i: number) => (
              <li key={i} className="flex items-start gap-3 text-sm">
                <span className="mono text-[11px] text-ink-muted pt-[3px]">{(i + 1).toString().padStart(2, "0")}</span>
                <span>{r}</span>
              </li>
            ))}
          </ol>
        </div>
        <div className="px-6 py-5 border-t hairline bg-cream-soft/60">
          <details>
            <summary className="cursor-pointer text-[13px] text-ink hover:text-brand">All LLM reasons</summary>
            <table className="mt-3 w-full text-[12.5px]">
              <thead className="text-ink-muted">
                <tr><th className="text-left pb-1">Reason</th><th className="text-left pb-1">JD requires</th><th className="text-left pb-1">Resume says</th><th className="text-right pb-1">Weight</th></tr>
              </thead>
              <tbody>
                {(decision.shap || []).map((r: any) => (
                  <tr key={r.feature} className="border-t hairline">
                    <td className="py-1 pr-3">{r.display_name}</td>
                    <td className="py-1 pr-3 text-ink-muted">{r.jd_requirement}</td>
                    <td className="py-1 pr-3 mono">{r.value_display}</td>
                    <td className={`py-1 text-right ${r.contribution >= 0 ? "text-good" : "text-bad"}`}>{r.contribution >= 0 ? "+" : ""}{Number(r.contribution).toFixed(2)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </details>
        </div>
      </div>

      {!approved && (
        <div className="card p-6 mb-6 bg-accent-soft/30 border-brand/30">
          <div className="flex items-start justify-between gap-4">
            <div>
              <div className="label mb-2">Right to contest</div>
              <h2 className="display text-xl mb-2">Hand off to Recourse</h2>
              <p className="text-ink-muted text-sm max-w-md">
                EU AI Act Annex III flags hiring as high-risk. The applicant
                has a right to challenge each reason individually with a
                document or a written rebuttal. Issuing the link mints a
                signed JWT they verify with their DOB.
              </p>
            </div>
            <div>
              {s.contestUrl ? <a href={s.contestUrl} target="_blank" rel="noopener" className="btn-primary">Open contest portal →</a>
                : <button className="btn-primary" disabled={s.busy} onClick={() => s.requestContest()}>{s.busy ? <><span className="spinner" /> Issuing…</> : "Issue contest link"}</button>}
            </div>
          </div>
          {s.contestUrl && <div className="mt-4 rounded-md border hairline bg-surface px-3 py-2 text-[12px] mono text-ink-muted break-all">{s.contestUrl}</div>}
        </div>
      )}
    </section>
  );
}
