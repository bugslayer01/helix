import { useEffect, useState } from "react";
import * as api from "../lib/api";

export function OperatorView() {
  const [cases, setCases] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState<string | null>(null);
  const [detail, setDetail] = useState<any | null>(null);

  useEffect(() => {
    let cancelled = false;
    const poll = async () => {
      try {
        const res = await api.listOperatorCases();
        if (!cancelled) {
          setCases(res.cases);
          setLoading(false);
        }
      } catch {
        if (!cancelled) setLoading(false);
      }
    };
    poll();
    const id = setInterval(poll, 3000);
    return () => { cancelled = true; clearInterval(id); };
  }, []);

  useEffect(() => {
    if (!selected) { setDetail(null); return; }
    let cancelled = false;
    const poll = async () => {
      try {
        const res = await api.getOperatorCase(selected);
        if (!cancelled) setDetail(res);
      } catch { /* noop */ }
    };
    poll();
    const id = setInterval(poll, 3000);
    return () => { cancelled = true; clearInterval(id); };
  }, [selected]);

  return (
    <section className="mx-auto max-w-shell px-8 py-8">
      <div className="flex items-center justify-between mb-6">
        <div>
          <div className="label mb-1">Internal tools</div>
          <h1 className="display text-3xl">Operator console</h1>
        </div>
        <div className="text-[12px] text-ink-muted">{cases.length} cases · live</div>
      </div>

      <div className="grid grid-cols-[1.1fr_1.4fr] gap-6">
        <div className="card overflow-hidden">
          <div className="border-b hairline bg-cream-soft/60 px-4 py-2 label">Applications</div>
          {loading ? (
            <div className="px-4 py-6 text-sm text-ink-muted">Loading…</div>
          ) : cases.length === 0 ? (
            <div className="px-4 py-6 text-sm text-ink-muted">No applications yet. Submit one from the applicant portal.</div>
          ) : (
            <table className="w-full text-[13px]">
              <thead className="text-ink-muted">
                <tr className="border-b hairline">
                  <th className="text-left px-3 py-2">Applicant</th>
                  <th className="text-left px-3 py-2">Ref</th>
                  <th className="text-left px-3 py-2">Amount</th>
                  <th className="text-left px-3 py-2">Status</th>
                  <th className="text-left px-3 py-2">Verdict</th>
                </tr>
              </thead>
              <tbody>
                {cases.map((c) => (
                  <tr key={c.id}
                    className={`cursor-pointer border-b hairline hover:bg-brand-soft/30 ${selected === c.id ? "bg-brand-soft/40" : ""}`}
                    onClick={() => setSelected(c.id)}>
                    <td className="px-3 py-2 font-medium">{c.full_name}</td>
                    <td className="px-3 py-2 mono text-[11.5px] text-ink-muted">{c.id}</td>
                    <td className="px-3 py-2 mono">₹{Number(c.amount).toLocaleString("en-IN")}</td>
                    <td className="px-3 py-2">
                      <span className="pill">{c.status}</span>
                    </td>
                    <td className="px-3 py-2">
                      {c.verdict ? (
                        <span className={`pill ${c.verdict === "approved" ? "pill-approved" : "pill-denied"}`}>
                          {c.verdict}
                        </span>
                      ) : <span className="text-ink-muted">—</span>}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>

        <div className="card p-5">
          {!selected ? (
            <div className="text-ink-muted text-sm">Select a row to inspect.</div>
          ) : !detail ? (
            <div className="text-ink-muted text-sm">Loading detail…</div>
          ) : (
            <div className="space-y-5">
              <div>
                <div className="label mb-1">Case</div>
                <div className="display text-2xl">{detail.applicant.full_name}</div>
                <div className="mono text-[12px] text-ink-muted mt-1">{detail.application.id}</div>
              </div>

              <div className="grid grid-cols-3 gap-3 text-[13px]">
                <div className="card p-3">
                  <div className="label">Amount</div>
                  <div className="mono mt-1">₹{Number(detail.application.amount).toLocaleString("en-IN")}</div>
                </div>
                <div className="card p-3">
                  <div className="label">Status</div>
                  <div className="mt-1">{detail.application.status}</div>
                </div>
                <div className="card p-3">
                  <div className="label">Purpose</div>
                  <div className="mt-1">{detail.application.purpose}</div>
                </div>
              </div>

              <div>
                <div className="label mb-2">Decisions</div>
                <div className="space-y-2">
                  {detail.decisions.map((d: any) => (
                    <div key={d.id} className="card p-3">
                      <div className="flex items-center justify-between">
                        <span className={`pill ${d.verdict === "approved" ? "pill-approved" : "pill-denied"}`}>{d.verdict}</span>
                        <span className="text-[11px] text-ink-muted">{d.source}</span>
                      </div>
                      <div className="mt-2 text-[13px]">
                        prob_bad <span className="mono">{Number(d.prob_bad).toFixed(3)}</span>
                        <span className="mx-2 text-ink-muted">·</span>
                        {new Date(d.decided_at * 1000).toLocaleString()}
                      </div>
                      {d.top_reasons?.length > 0 && (
                        <ul className="mt-2 list-disc pl-5 text-[13px] space-y-1">
                          {d.top_reasons.map((r: string, i: number) => <li key={i}>{r}</li>)}
                        </ul>
                      )}
                    </div>
                  ))}
                  {detail.decisions.length === 0 && <div className="text-[13px] text-ink-muted">No decisions yet.</div>}
                </div>
              </div>

              {detail.contest_handoffs?.length > 0 && (
                <div>
                  <div className="label mb-2">Contest handoffs</div>
                  {detail.contest_handoffs.map((h: any) => (
                    <div key={h.jti} className="mono text-[11.5px] text-ink-muted">
                      jti {h.jti.slice(0, 16)}… expires {new Date(h.expires_at * 1000).toLocaleString()}
                    </div>
                  ))}
                </div>
              )}

              {detail.intake_documents?.length > 0 && (
                <div>
                  <div className="label mb-2">Intake documents</div>
                  <ul className="space-y-1 text-[13px]">
                    {detail.intake_documents.map((d: any) => (
                      <li key={d.id} className="flex items-center gap-2">
                        <span className="pill">{d.doc_type}</span>
                        <span className="mono">{d.original_name}</span>
                        <span className="mono text-[11px] text-ink-muted">sha256:{d.sha256.slice(0, 10)}…</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </section>
  );
}
