import { useState } from "react";
import { useStore } from "../store";

const REASONS: { value: string; label: string }[] = [
  { value: "procedural_error", label: "I believe the process made a procedural error" },
  { value: "data_wrong", label: "The data my lender holds about me is wrong" },
  { value: "not_explained", label: "I was not given a clear explanation of the decision" },
  { value: "other", label: "Something else — I'll describe it below" },
];

export function ReviewView() {
  const [reason, setReason] = useState("procedural_error");
  const [statement, setStatement] = useState("");
  const submit = useStore((s) => s.requestReview);
  const busy = useStore((s) => s.busy);
  const error = useStore((s) => s.error);
  const goto = useStore((s) => s.goto);

  return (
    <section className="mx-auto max-w-2xl px-6 py-12">
      <div className="label mb-3">Alternate path · Human reviewer</div>
      <h1 className="display text-4xl mb-3">Hand this to a person.</h1>
      <p className="text-ink-muted text-base max-w-xl mb-8">
        This path does not re-run the model. Your case is queued for a human
        reviewer at your lender. Expect a response within 72 hours. Your statement
        is preserved in the audit chain.
      </p>

      <div className="card p-5 space-y-4">
        <div>
          <label className="label mb-2 block">Reason</label>
          <select className="input" value={reason} onChange={(e) => setReason(e.target.value)}>
            {REASONS.map((r) => <option key={r.value} value={r.value}>{r.label}</option>)}
          </select>
        </div>
        <div>
          <label className="label mb-2 block">Statement (optional, max 2000 chars)</label>
          <textarea
            className="input min-h-[160px]"
            rows={6}
            maxLength={2000}
            value={statement}
            onChange={(e) => setStatement(e.target.value)}
            placeholder="Tell the reviewer what went wrong in your own words."
          />
          <div className="text-[11px] text-ink-muted mt-1 text-right">{statement.length} / 2000</div>
        </div>
        {error && <div className="rounded-md border border-accent/40 bg-accent/5 px-3 py-2 text-sm text-accent">{error}</div>}
        <div className="flex items-center justify-between pt-2">
          <button className="btn-ghost" onClick={() => goto("understand")}>← Back</button>
          <button className="btn-primary" disabled={busy} onClick={() => submit(reason, statement)}>
            {busy ? <><span className="spinner" /> Queuing…</> : "Queue for human review →"}
          </button>
        </div>
      </div>
    </section>
  );
}
