import { useEffect } from "react";
import { useStore } from "../store";

export function PickerView() {
  const cases = useStore((s) => s.cases);
  const loadCases = useStore((s) => s.loadCases);
  const pick = useStore((s) => s.pickCase);
  const busy = useStore((s) => s.busy);
  const startNewApplication = useStore((s) => s.startNewApplication);

  useEffect(() => { loadCases(); }, []);

  return (
    <section className="mx-auto max-w-3xl px-6 py-14">
      <div className="flex items-start justify-between gap-4 mb-3">
        <div className="label">Demo applicants</div>
        <button className="btn-primary text-[13px] py-1.5" onClick={() => startNewApplication()}>
          + New loan application
        </button>
      </div>
      <h1 className="display text-4xl leading-[1.05] mb-3">
        Pick a case to see what the model said.
      </h1>
      <p className="text-ink-muted text-base max-w-xl mb-8">
        Each row below is a real loan application that has already been scored by
        LenderCo's underwriting model. Pick a denied case to start your
        contestation flow on Recourse.
      </p>

      {busy && cases.length === 0 ? (
        <div className="text-sm text-ink-muted">Loading cases…</div>
      ) : cases.length === 0 ? (
        <div className="card p-6 text-sm text-ink-muted">
          No cases found. Run <span className="mono">make seed-all</span> first to load demo applicants.
        </div>
      ) : (
        <div className="card overflow-x-auto">
          <table className="w-full min-w-[640px] text-[14px]">
            <thead className="text-ink-muted">
              <tr className="border-b hairline">
                <th className="text-left px-4 py-3">Applicant</th>
                <th className="text-left px-4 py-3">Reference</th>
                <th className="text-left px-4 py-3">Amount</th>
                <th className="text-left px-4 py-3">Verdict</th>
                <th className="text-left px-4 py-3">Risk</th>
                <th className="text-right px-4 py-3"></th>
              </tr>
            </thead>
            <tbody>
              {cases.map((c) => {
                const denied = c.verdict === "denied";
                return (
                  <tr key={c.id} className="border-b hairline hover:bg-brand-soft/30 transition-colors">
                    <td className="px-4 py-3 font-medium">{c.full_name}</td>
                    <td className="px-4 py-3 mono text-[12px] text-ink-muted">{c.id}</td>
                    <td className="px-4 py-3 mono">₹{Number(c.amount).toLocaleString("en-IN")}</td>
                    <td className="px-4 py-3">
                      {c.verdict ? (
                        <span className={`pill ${denied ? "pill-denied" : "pill-approved"}`}>{c.verdict}</span>
                      ) : <span className="text-ink-muted">—</span>}
                    </td>
                    <td className="px-4 py-3 mono text-[13px]">
                      {c.prob_bad !== null ? `${(c.prob_bad * 100).toFixed(1)}%` : "—"}
                    </td>
                    <td className="px-4 py-3 text-right">
                      <button className="btn-primary text-[13px] py-1.5" onClick={() => pick(c.id)}>
                        {denied ? "Open & contest →" : "Open →"}
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      <div className="mt-6 text-[12px] text-ink-muted">
        Want a fresh dataset? Run <span className="mono">make reset && make seed-all</span> in the repo.
      </div>
    </section>
  );
}
